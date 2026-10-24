
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_hrbp,
    is_talent_manager,
    require_hrbp,
    require_talent_manager,
)


class OneHRTalentPool(models.Model):
    _name = "onehr.talent.pool"
    _description = "OneHR Talent Pool"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, readiness_score desc, potential_score desc, employee_name"

    _employee_pool_unique = models.Constraint(
        "UNIQUE(employee_id, pool_code, company_id)",
        "An employee can have only one active identity per talent pool code and company.",
    )

    _STATE_CONTEXT = "onehr_career_talent_state_controlled"

    name = fields.Char(
        string="Talent Reference",
        required=True,
        default="New",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    pool_code = fields.Char(
        string="Talent Pool",
        required=True,
        default="HIPOT",
        index=True,
        tracking=True,
        help="Business pool identifier, for example HIPOT, LEADERSHIP or CRITICAL.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
        groups="onehr_career_succession.group_onehr_career_hrbp",
    )
    employee_name = fields.Char(
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_career_succession.group_onehr_career_hrbp",
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_name = fields.Char(
        related="employee_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    current_position_id = fields.Many2one(
        "onehr.position",
        related="employee_id.onehr_primary_position_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_career_succession.group_onehr_career_hrbp",
    )
    current_position_name = fields.Char(
        related="employee_id.onehr_primary_position_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    target_position_id = fields.Many2one(
        "onehr.position",
        string="Target / Career Position",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    target_position_name = fields.Char(
        related="target_position_id.name",
        store=True,
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("proposed", "Proposed"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    nomination_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        index=True,
        tracking=True,
    )
    proposed_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    proposed_at = fields.Datetime(readonly=True, tracking=True)
    approved_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    approved_at = fields.Datetime(readonly=True, tracking=True)
    activated_at = fields.Datetime(readonly=True, tracking=True)
    deactivated_at = fields.Datetime(readonly=True, tracking=True)
    review_date = fields.Date(index=True, tracking=True)

    high_potential = fields.Boolean(default=False, index=True, tracking=True)
    retention_risk = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="low",
        required=True,
        index=True,
        tracking=True,
    )
    loss_impact = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
        index=True,
        tracking=True,
    )

    performance_score = fields.Float(
        string="Performance %",
        default=0.0,
        tracking=True,
        help="0-100 score. May be refreshed from OneHR Appraisal when installed.",
    )
    potential_score = fields.Float(
        string="Potential %",
        default=0.0,
        tracking=True,
    )
    competency_score = fields.Float(
        string="Competency Readiness %",
        default=0.0,
        tracking=True,
        help="Overall competency evidence against the target position.",
    )
    learning_score = fields.Float(
        string="Learning Readiness %",
        default=0.0,
        tracking=True,
        help="Training/certification readiness; may be refreshed from OneHR Learning.",
    )
    readiness_score = fields.Float(
        compute="_compute_readiness",
        store=True,
        string="Overall Readiness %",
        index=True,
    )
    readiness_level = fields.Selection(
        [
            ("ready_now", "Ready Now"),
            ("ready_1y", "Ready < 1 Year"),
            ("ready_2y", "Ready 1-2 Years"),
            ("ready_3y", "Ready 2-3 Years"),
            ("long_term", "Long Term"),
            ("not_ready", "Not Ready"),
        ],
        compute="_compute_readiness",
        store=True,
        index=True,
    )
    nine_box_position = fields.Selection(
        [
            ("low_low", "Low Performance / Low Potential"),
            ("low_mid", "Low Performance / Medium Potential"),
            ("low_high", "Low Performance / High Potential"),
            ("mid_low", "Medium Performance / Low Potential"),
            ("mid_mid", "Medium Performance / Medium Potential"),
            ("mid_high", "Medium Performance / High Potential"),
            ("high_low", "High Performance / Low Potential"),
            ("high_mid", "High Performance / Medium Potential"),
            ("high_high", "High Performance / High Potential"),
        ],
        compute="_compute_nine_box",
        store=True,
        index=True,
    )
    gap_score = fields.Float(
        compute="_compute_readiness",
        store=True,
        string="Readiness Gap %",
    )

    appraisal_reference = fields.Char(readonly=True, copy=False)
    appraisal_cycle_code = fields.Char(readonly=True, copy=False)
    learning_evidence_reference = fields.Char(readonly=True, copy=False)
    source_refreshed_at = fields.Datetime(readonly=True, copy=False)

    strengths = fields.Html(tracking=True)
    development_needs = fields.Html(tracking=True)
    career_aspiration = fields.Html(tracking=True)
    mobility_preference = fields.Text(tracking=True)
    assessment_notes = fields.Html(tracking=True)
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_talent_pool_attachment_rel",
        "talent_id",
        "attachment_id",
        string="Evidence Attachments",
        copy=False,
    )

    target_requirement_ids = fields.Many2many(
        "onehr.position.competency",
        compute="_compute_target_requirements",
        string="Target Competency Requirements",
        readonly=True,
    )
    succession_plan_ids = fields.Many2many(
        "onehr.succession.plan",
        "onehr_succession_plan_candidate_rel",
        "talent_id",
        "plan_id",
        string="Succession Plans",
        readonly=True,
    )
    succession_plan_count = fields.Integer(compute="_compute_counts")
    required_competency_count = fields.Integer(compute="_compute_counts")
    gap_competency_count = fields.Integer(compute="_compute_counts")

    @api.model_create_multi
    def create(self, vals_list):
        require_hrbp(self)
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.talent.pool"
                ) or "New"
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get(self._STATE_CONTEXT):
            return super().write(vals)

        lifecycle_fields = {
            "name", "state", "proposed_by_id", "proposed_at", "approved_by_id",
            "approved_at", "activated_at", "deactivated_at",
        }
        if lifecycle_fields.intersection(vals):
            raise AccessError(
                _("Talent lifecycle fields must change through governed actions.")
            )

        immutable_when_active = {
            "employee_id", "company_id", "pool_code",
        }
        for record in self:
            if (
                record.state == "active"
                and immutable_when_active.intersection(vals)
            ):
                raise AccessError(
                    _("Employee, company and talent-pool identity are frozen while Active.")
                )
        return super().write(vals)

    @api.depends(
        "performance_score",
        "potential_score",
        "competency_score",
        "learning_score",
    )
    def _compute_readiness(self):
        for record in self:
            # Balanced composite keeps readiness understandable and manually auditable.
            components = [
                record.performance_score,
                record.potential_score,
                record.competency_score,
                record.learning_score,
            ]
            readiness = sum(components) / len(components)
            record.readiness_score = readiness
            record.gap_score = max(0.0, 100.0 - readiness)

            if readiness >= 90:
                level = "ready_now"
            elif readiness >= 80:
                level = "ready_1y"
            elif readiness >= 70:
                level = "ready_2y"
            elif readiness >= 60:
                level = "ready_3y"
            elif readiness >= 45:
                level = "long_term"
            else:
                level = "not_ready"
            record.readiness_level = level

    @api.depends("performance_score", "potential_score")
    def _compute_nine_box(self):
        def band(value):
            if value < 60:
                return "low"
            if value < 80:
                return "mid"
            return "high"

        for record in self:
            record.nine_box_position = (
                f"{band(record.performance_score)}_{band(record.potential_score)}"
            )

    @api.depends("target_position_id")
    def _compute_target_requirements(self):
        Requirement = self.env["onehr.position.competency"]
        for record in self:
            record.target_requirement_ids = (
                Requirement.search(
                    [
                        ("position_id", "=", record.target_position_id.id),
                        ("active", "=", True),
                    ]
                )
                if record.target_position_id
                else Requirement.browse()
            )

    def _compute_counts(self):
        PositionCompetency = self.env["onehr.position.competency"]
        for record in self:
            record.succession_plan_count = len(record.succession_plan_ids)
            requirements = PositionCompetency.search(
                [
                    ("position_id", "=", record.target_position_id.id),
                    ("active", "=", True),
                ]
            ) if record.target_position_id else PositionCompetency.browse()
            record.required_competency_count = len(requirements)
            # Detailed employee competency observations are intentionally not
            # invented as an unapproved fifth model. The aggregate gap is governed
            # on the Talent record; this count flags whether aggregate readiness
            # is below the configured threshold for a target with requirements.
            record.gap_competency_count = (
                len(requirements)
                if requirements and record.competency_score < 100.0
                else 0
            )

    @api.constrains(
        "performance_score",
        "potential_score",
        "competency_score",
        "learning_score",
    )
    def _check_scores(self):
        for record in self:
            for value, label in (
                (record.performance_score, _("Performance")),
                (record.potential_score, _("Potential")),
                (record.competency_score, _("Competency Readiness")),
                (record.learning_score, _("Learning Readiness")),
            ):
                if value < 0 or value > 100:
                    raise ValidationError(_("%s score must be between 0 and 100.") % label)

    @api.constrains("employee_id", "company_id", "target_position_id")
    def _check_company_alignment(self):
        for record in self:
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(
                    _("Employee and talent record must belong to the same company.")
                )
            if (
                record.target_position_id
                and record.target_position_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _("Target position must belong to the talent record company.")
                )

    def _write_state(self, state, **evidence):
        values = {"state": state, **evidence}
        return self.with_context(**{self._STATE_CONTEXT: True}).write(values)

    def action_propose(self):
        require_hrbp(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft talent records can be proposed."))
            record._write_state(
                "proposed",
                proposed_by_id=self.env.user.id,
                proposed_at=fields.Datetime.now(),
            )
        return display_notification(_("Talent nomination proposed."))

    def action_approve(self):
        require_talent_manager(self)
        for record in self:
            if record.state != "proposed":
                raise UserError(_("Only Proposed talent records can be approved."))
            record._write_state(
                "approved",
                approved_by_id=self.env.user.id,
                approved_at=fields.Datetime.now(),
            )
        return display_notification(_("Talent nomination approved."))

    def action_activate(self):
        require_talent_manager(self)
        for record in self:
            if record.state != "approved":
                raise UserError(_("Only Approved talent records can become Active."))
            record._write_state(
                "active",
                activated_at=fields.Datetime.now(),
                deactivated_at=False,
            )
        return display_notification(_("Talent pool record activated."))

    def action_deactivate(self):
        require_talent_manager(self)
        for record in self:
            if record.state != "active":
                raise UserError(_("Only Active talent records can be deactivated."))
            record._write_state(
                "inactive",
                deactivated_at=fields.Datetime.now(),
            )
        return display_notification(
            _("Talent pool record deactivated."),
            notification_type="warning",
        )

    def action_reject(self):
        require_talent_manager(self)
        for record in self:
            if record.state not in ("draft", "proposed"):
                raise UserError(_("Only Draft/Proposed talent records can be rejected."))
            record._write_state("rejected")
        return display_notification(
            _("Talent nomination rejected."),
            notification_type="warning",
        )

    def action_reset_draft(self):
        require_talent_manager(self)
        for record in self:
            if record.state not in ("rejected", "inactive"):
                raise UserError(_("Only Rejected/Inactive records can be reset to Draft."))
            if record.succession_plan_ids.filtered(lambda plan: plan.state == "active"):
                raise UserError(
                    _("Reset is blocked while the talent is used by an Active succession plan.")
                )
            record._write_state("draft")
        return display_notification(_("Talent record reset to Draft."))

    def action_open_succession_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Succession Plans"),
            "res_model": "onehr.succession.plan",
            "view_mode": "kanban,list,form,pivot,graph",
            "domain": [("candidate_talent_ids", "in", self.id)],
        }

    def action_open_target_requirements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Target Position Competency Requirements"),
            "res_model": "onehr.position.competency",
            "view_mode": "list,form,pivot,graph",
            "domain": [("position_id", "=", self.target_position_id.id)],
        }

    def action_print_gap_report(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_career_succession.action_report_talent_gap"
        ).report_action(self)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft(self):
        for record in self:
            if record.state not in ("draft", "rejected"):
                raise UserError(
                    _("Approved/active/inactive talent evidence must be retained, not deleted.")
                )
            if record.succession_plan_ids:
                raise UserError(
                    _("Talent evidence referenced by succession plans cannot be deleted.")
                )

