
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    require_hrbp,
    require_talent_manager,
)


class OneHRSuccessionPlan(models.Model):
    _name = "onehr.succession.plan"
    _description = "OneHR Succession Plan"
    _inherit = ["onehr.mixin.audit"]
    _order = "criticality desc, risk_index desc, review_date, name"

    _position_company_unique = models.Constraint(
        "UNIQUE(position_id, company_id)",
        "A position can have only one succession-plan record per company.",
    )

    _STATE_CONTEXT = "onehr_succession_plan_state_controlled"

    name = fields.Char(
        string="Plan Reference",
        required=True,
        default="New",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    title = fields.Char(required=True, translate=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    position_id = fields.Many2one(
        "onehr.position",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    position_code = fields.Char(
        related="position_id.code",
        store=True,
        readonly=True,
        index=True,
    )
    position_name = fields.Char(
        related="position_id.name",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="position_id.department_id",
        store=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="position_id.job_id",
        store=True,
        readonly=True,
        index=True,
    )
    incumbent_employee_id = fields.Many2one(
        "hr.employee",
        string="Current Incumbent",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
        groups="onehr_career_succession.group_onehr_career_hrbp",
    )
    incumbent_name = fields.Char(
        related="incumbent_employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("proposed", "Proposed"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    criticality = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="high",
        required=True,
        tracking=True,
        index=True,
    )
    vacancy_risk = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
        tracking=True,
        index=True,
    )
    retirement_risk = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        required=True,
        tracking=True,
    )
    business_impact = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="high",
        required=True,
        tracking=True,
    )

    review_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
        index=True,
    )
    target_coverage = fields.Integer(
        default=2,
        required=True,
        tracking=True,
        help="Minimum number of approved/active successor candidates required.",
    )
    candidate_talent_ids = fields.Many2many(
        "onehr.talent.pool",
        "onehr_succession_plan_candidate_rel",
        "plan_id",
        "talent_id",
        string="Successor Candidates",
        tracking=True,
    )
    primary_successor_id = fields.Many2one(
        "onehr.talent.pool",
        string="Primary Successor",
        ondelete="restrict",
        check_company=True,
        tracking=True,
        domain="[('id', 'in', candidate_talent_ids)]",
    )

    successor_count = fields.Integer(compute="_compute_metrics", store=True)
    ready_now_count = fields.Integer(compute="_compute_metrics", store=True)
    bench_strength = fields.Float(
        compute="_compute_metrics",
        store=True,
        string="Bench Strength %",
    )
    coverage_percent = fields.Float(
        compute="_compute_metrics",
        store=True,
        string="Coverage %",
    )
    average_readiness = fields.Float(
        compute="_compute_metrics",
        store=True,
        string="Average Readiness %",
    )
    risk_index = fields.Float(
        compute="_compute_risk_index",
        store=True,
        string="Risk Index",
        help="0-100 composite succession risk. Higher means more urgent.",
    )

    proposed_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    proposed_at = fields.Datetime(readonly=True, tracking=True)
    approved_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    approved_at = fields.Datetime(readonly=True, tracking=True)
    activated_at = fields.Datetime(readonly=True, tracking=True)
    closed_at = fields.Datetime(readonly=True, tracking=True)

    succession_strategy = fields.Html(tracking=True)
    risk_mitigation = fields.Html(tracking=True)
    development_actions = fields.Html(tracking=True)
    contingency_notes = fields.Html(tracking=True)
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_succession_plan_attachment_rel",
        "plan_id",
        "attachment_id",
        string="Evidence Attachments",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_hrbp(self)
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.succession.plan"
                ) or "New"
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get(self._STATE_CONTEXT):
            return super().write(vals)

        lifecycle_fields = {
            "name", "state", "proposed_by_id", "proposed_at", "approved_by_id",
            "approved_at", "activated_at", "closed_at",
        }
        if lifecycle_fields.intersection(vals):
            raise AccessError(
                _("Succession-plan lifecycle fields must change through governed actions.")
            )

        for plan in self:
            if (
                plan.state == "active"
                and {"company_id", "position_id"}.intersection(vals)
            ):
                raise AccessError(
                    _("Company and critical position are frozen while a plan is Active.")
                )
        return super().write(vals)

    @api.depends(
        "candidate_talent_ids",
        "candidate_talent_ids.state",
        "candidate_talent_ids.readiness_score",
        "candidate_talent_ids.readiness_level",
        "target_coverage",
    )
    def _compute_metrics(self):
        for plan in self:
            candidates = plan.candidate_talent_ids.filtered(
                lambda talent: talent.state in ("approved", "active")
            )
            plan.successor_count = len(candidates)
            plan.ready_now_count = len(
                candidates.filtered(
                    lambda talent: talent.readiness_level == "ready_now"
                )
            )
            plan.bench_strength = (
                len(
                    candidates.filtered(
                        lambda talent: talent.readiness_level
                        in ("ready_now", "ready_1y", "ready_2y")
                    )
                )
                * 100.0
                / len(candidates)
                if candidates
                else 0.0
            )
            plan.coverage_percent = min(
                100.0,
                len(candidates) * 100.0 / plan.target_coverage
                if plan.target_coverage
                else 100.0,
            )
            plan.average_readiness = (
                sum(candidates.mapped("readiness_score")) / len(candidates)
                if candidates
                else 0.0
            )

    @api.depends(
        "criticality",
        "vacancy_risk",
        "business_impact",
        "coverage_percent",
        "average_readiness",
    )
    def _compute_risk_index(self):
        score_map = {
            "low": 25.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 100.0,
        }
        for plan in self:
            structural = (
                score_map.get(plan.criticality, 50.0)
                + score_map.get(plan.vacancy_risk, 50.0)
                + score_map.get(plan.business_impact, 50.0)
            ) / 3.0
            readiness_gap = 100.0 - plan.average_readiness
            coverage_gap = 100.0 - plan.coverage_percent
            plan.risk_index = (
                structural * 0.40
                + readiness_gap * 0.35
                + coverage_gap * 0.25
            )

    @api.constrains("target_coverage")
    def _check_target_coverage(self):
        for plan in self:
            if plan.target_coverage < 1:
                raise ValidationError(
                    _("Target successor coverage must be at least one.")
                )

    @api.constrains(
        "company_id",
        "position_id",
        "incumbent_employee_id",
        "candidate_talent_ids",
        "primary_successor_id",
    )
    def _check_company_and_candidates(self):
        for plan in self:
            if plan.position_id.company_id != plan.company_id:
                raise ValidationError(
                    _("Critical position must belong to the succession-plan company.")
                )
            if (
                plan.incumbent_employee_id
                and plan.incumbent_employee_id.company_id != plan.company_id
            ):
                raise ValidationError(
                    _("Incumbent must belong to the succession-plan company.")
                )
            if any(
                talent.company_id != plan.company_id
                for talent in plan.candidate_talent_ids
            ):
                raise ValidationError(
                    _("All successor candidates must belong to the succession-plan company.")
                )
            if any(
                talent.target_position_id
                and talent.target_position_id != plan.position_id
                for talent in plan.candidate_talent_ids
            ):
                raise ValidationError(
                    _("Successor candidates must target the succession-plan position.")
                )
            if (
                plan.primary_successor_id
                and plan.primary_successor_id not in plan.candidate_talent_ids
            ):
                raise ValidationError(
                    _("Primary Successor must be one of the plan candidates.")
                )

    def _write_state(self, state, **evidence):
        return self.with_context(**{self._STATE_CONTEXT: True}).write(
            {"state": state, **evidence}
        )

    def action_propose(self):
        require_hrbp(self)
        for plan in self:
            if plan.state != "draft":
                raise UserError(_("Only Draft succession plans can be proposed."))
            if not plan.candidate_talent_ids:
                raise UserError(_("Add at least one successor candidate before proposing."))
            plan._write_state(
                "proposed",
                proposed_by_id=self.env.user.id,
                proposed_at=fields.Datetime.now(),
            )
        return display_notification(_("Succession plan proposed."))

    def action_approve(self):
        require_talent_manager(self)
        for plan in self:
            if plan.state != "proposed":
                raise UserError(_("Only Proposed succession plans can be approved."))
            approved = plan.candidate_talent_ids.filtered(
                lambda talent: talent.state in ("approved", "active")
            )
            if not approved:
                raise UserError(
                    _("At least one Approved/Active talent candidate is required.")
                )
            plan._write_state(
                "approved",
                approved_by_id=self.env.user.id,
                approved_at=fields.Datetime.now(),
            )
        return display_notification(_("Succession plan approved."))

    def action_activate(self):
        require_talent_manager(self)
        for plan in self:
            if plan.state != "approved":
                raise UserError(_("Only Approved succession plans can become Active."))
            if plan.coverage_percent <= 0:
                raise UserError(_("Succession coverage must be greater than zero."))
            plan._write_state(
                "active",
                activated_at=fields.Datetime.now(),
                closed_at=False,
            )
        return display_notification(_("Succession plan activated."))

    def action_close(self):
        require_talent_manager(self)
        for plan in self:
            if plan.state != "active":
                raise UserError(_("Only Active succession plans can be closed."))
            plan._write_state("closed", closed_at=fields.Datetime.now())
        return display_notification(_("Succession plan closed."))

    def action_cancel(self):
        require_talent_manager(self)
        for plan in self:
            if plan.state in ("closed", "cancelled"):
                raise UserError(_("Closed/cancelled succession plans cannot be cancelled again."))
            plan._write_state("cancelled")
        return display_notification(
            _("Succession plan cancelled."),
            notification_type="warning",
        )

    def action_reset_draft(self):
        require_talent_manager(self)
        for plan in self:
            if plan.state not in ("cancelled",):
                raise UserError(_("Only Cancelled succession plans can be reset to Draft."))
            plan._write_state("draft")
        return display_notification(_("Succession plan reset to Draft."))

    def action_open_candidates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Successor Candidates"),
            "res_model": "onehr.talent.pool",
            "view_mode": "kanban,list,form,pivot,graph",
            "domain": [("id", "in", self.candidate_talent_ids.ids)],
        }

    def action_open_position_requirements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Position Competency Requirements"),
            "res_model": "onehr.position.competency",
            "view_mode": "list,form,pivot,graph",
            "domain": [("position_id", "=", self.position_id.id)],
        }

    def action_print_succession_plan(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_career_succession.action_report_succession_plan"
        ).report_action(self)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft(self):
        for plan in self:
            if plan.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Approved/active/closed succession evidence must be retained, not deleted.")
                )

    @api.model
    def _cron_succession_review_reminders(self):
        today = fields.Date.context_today(self)
        plans = self.search(
            [
                ("state", "=", "active"),
                ("review_date", "!=", False),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        todo = self.env.ref("mail.mail_activity_data_todo")
        managers = self.env.ref(
            "onehr_career_succession.group_onehr_talent_manager"
        ).users.filtered(
            lambda user: user.company_id in self.env.companies
        )
        for plan in plans:
            days = (plan.review_date - today).days
            if not 0 <= days <= 14:
                continue
            for user in managers:
                duplicate = plan.activity_ids.filtered(
                    lambda activity: (
                        activity.activity_type_id == todo
                        and activity.user_id == user
                        and activity.date_deadline == plan.review_date
                    )
                )
                if not duplicate:
                    plan.activity_schedule(
                        todo.id,
                        user_id=user.id,
                        date_deadline=plan.review_date,
                        summary=_("Succession plan review due"),
                        note=_("Review succession plan %s.") % plan.display_name,
                    )

