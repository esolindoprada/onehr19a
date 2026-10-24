from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .action_helpers import open_record_action
from .security_helpers import require_offboarding_manager, require_offboarding_officer


class OneHRExitInterview(models.Model):
    """Governed exit-interview evidence, kept distinct from legal exit facts."""

    _name = "onehr.exit.interview"
    _description = "OneHR Exit Interview"
    _inherit = ["onehr.mixin.audit"]
    _order = "scheduled_at desc, id desc"

    offboarding_id = fields.Many2one(
        "onehr.offboarding", required=True, ondelete="cascade", index=True, tracking=True
    )
    company_id = fields.Many2one(related="offboarding_id.company_id", store=True, index=True)
    employee_id = fields.Many2one(related="offboarding_id.employee_id", store=True, index=True)
    interviewer_user_id = fields.Many2one("res.users", ondelete="restrict", tracking=True)
    scheduled_at = fields.Datetime(index=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("in_progress", "In Progress"),
            ("submitted", "Submitted"),
            ("waived", "Waived"),
        ],
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    primary_exit_reason = fields.Selection(
        [
            ("career", "Career Opportunity"),
            ("compensation", "Compensation / Benefits"),
            ("manager", "Manager / Leadership"),
            ("culture", "Culture / Environment"),
            ("relocation", "Relocation / Family"),
            ("retirement", "Retirement"),
            ("health", "Personal / Health"),
            ("performance", "Performance / Employer Decision"),
            ("mutual", "Mutual Agreement"),
            ("other", "Other"),
        ],
        tracking=True,
        index=True,
    )
    reason_detail = fields.Text(tracking=True)
    manager_relationship_score = fields.Integer(default=3, tracking=True)
    role_clarity_score = fields.Integer(default=3, tracking=True)
    rewards_score = fields.Integer(default=3, tracking=True)
    culture_score = fields.Integer(default=3, tracking=True)
    growth_score = fields.Integer(default=3, tracking=True)
    work_life_score = fields.Integer(default=3, tracking=True)
    recommendation_score = fields.Integer(default=5, tracking=True)
    overall_score = fields.Float(compute="_compute_overall_score", store=True)
    destination_category = fields.Selection(
        [
            ("competitor", "Competitor"),
            ("other_industry", "Other Industry"),
            ("education", "Education"),
            ("entrepreneurship", "Entrepreneurship"),
            ("retirement", "Retirement"),
            ("career_break", "Career Break"),
            ("undisclosed", "Undisclosed"),
        ],
        default="undisclosed",
        tracking=True,
    )
    employee_feedback = fields.Text(tracking=True)
    improvement_suggestions = fields.Text(tracking=True)
    confidential_hr_notes = fields.Text(
        tracking=True,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_manager",
    )
    submitted_at = fields.Datetime(readonly=True, copy=False)
    submitted_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    waiver_reason = fields.Text(copy=False, tracking=True)
    waived_at = fields.Datetime(readonly=True, copy=False)
    waived_by_id = fields.Many2one("res.users", readonly=True, copy=False)

    _unique_offboarding_interview = models.Constraint(
        "UNIQUE(offboarding_id)",
        "Only one governed exit interview may exist for an offboarding case.",
    )
    _score_manager = models.Constraint("CHECK(manager_relationship_score BETWEEN 1 AND 5)", "Manager score must be between 1 and 5.")
    _score_role = models.Constraint("CHECK(role_clarity_score BETWEEN 1 AND 5)", "Role clarity score must be between 1 and 5.")
    _score_rewards = models.Constraint("CHECK(rewards_score BETWEEN 1 AND 5)", "Rewards score must be between 1 and 5.")
    _score_culture = models.Constraint("CHECK(culture_score BETWEEN 1 AND 5)", "Culture score must be between 1 and 5.")
    _score_growth = models.Constraint("CHECK(growth_score BETWEEN 1 AND 5)", "Growth score must be between 1 and 5.")
    _score_work_life = models.Constraint("CHECK(work_life_score BETWEEN 1 AND 5)", "Work-life score must be between 1 and 5.")
    _score_recommend = models.Constraint("CHECK(recommendation_score BETWEEN 0 AND 10)", "Recommendation score must be between 0 and 10.")

    @api.depends(
        "manager_relationship_score", "role_clarity_score", "rewards_score",
        "culture_score", "growth_score", "work_life_score",
    )
    def _compute_overall_score(self):
        for record in self:
            scores = [
                record.manager_relationship_score, record.role_clarity_score,
                record.rewards_score, record.culture_score,
                record.growth_score, record.work_life_score,
            ]
            record.overall_score = round(sum(scores) / len(scores), 2)

    @api.model_create_multi
    def create(self, vals_list):
        require_offboarding_officer(self)
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(lambda r: r.offboarding_id.state == "closed"):
            raise ValidationError(_("Exit interview evidence is immutable after the offboarding case is Closed."))
        if "state" in vals and not self.env.context.get("onehr_exit_interview_state_action"):
            raise ValidationError(_("Use exit-interview workflow actions to change state."))
        protected_actor_evidence = {"submitted_at", "submitted_by_id", "waived_at", "waived_by_id"}
        if protected_actor_evidence.intersection(vals) and not self.env.context.get("onehr_exit_interview_state_action"):
            raise ValidationError(_("Exit-interview actor/timestamp evidence may change only through workflow actions."))
        evidence_fields = {
            "primary_exit_reason", "reason_detail", "manager_relationship_score", "role_clarity_score",
            "rewards_score", "culture_score", "growth_score", "work_life_score",
            "recommendation_score", "destination_category", "employee_feedback",
            "improvement_suggestions", "confidential_hr_notes",
        }
        if evidence_fields.intersection(vals) and self.filtered(lambda r: r.state in ("submitted", "waived")):
            raise ValidationError(_("Submitted or waived interviews must be reopened before correction."))
        return super().write(vals)

    def unlink(self):
        require_offboarding_manager(self)
        if self.filtered(lambda r: r.state not in ("draft", "scheduled")):
            raise ValidationError(_("Started interview evidence cannot be deleted. Waive or retain it."))
        return super().unlink()

    def action_schedule(self):
        require_offboarding_officer(self)
        for record in self:
            if not record.scheduled_at or not record.interviewer_user_id:
                raise UserError(_("Interviewer and Scheduled At are required."))
            record.with_context(onehr_exit_interview_state_action=True).write({"state": "scheduled"})
        return True

    def action_start(self):
        require_offboarding_officer(self)
        self.with_context(onehr_exit_interview_state_action=True).write({"state": "in_progress"})
        return True

    def action_submit(self):
        require_offboarding_officer(self)
        for record in self:
            if not record.primary_exit_reason:
                raise UserError(_("Primary Exit Reason is required before submitting the interview."))
            record.with_context(onehr_exit_interview_state_action=True).write(
                {"state": "submitted", "submitted_at": fields.Datetime.now(), "submitted_by_id": self.env.user.id}
            )
        return True

    def action_waive(self):
        require_offboarding_manager(self)
        for record in self:
            if not record.waiver_reason:
                raise UserError(_("Waiver Reason is required."))
            record.with_context(onehr_exit_interview_state_action=True).write(
                {"state": "waived", "waived_at": fields.Datetime.now(), "waived_by_id": self.env.user.id}
            )
        return True

    def action_reopen(self):
        require_offboarding_manager(self)
        for record in self:
            if record.offboarding_id.state == "closed":
                raise UserError(_("Closed-case interview evidence cannot be reopened."))
            if record.state not in ("submitted", "waived"):
                raise UserError(_("Only Submitted or Waived interviews may be reopened."))
            record.with_context(onehr_exit_interview_state_action=True).write(
                {
                    "state": "in_progress",
                    "submitted_at": False,
                    "submitted_by_id": False,
                    "waived_at": False,
                    "waived_by_id": False,
                }
            )
        return True

    def action_open_offboarding(self):
        self.ensure_one()
        return open_record_action(
            name=self.offboarding_id.display_name,
            res_model="onehr.offboarding",
            res_id=self.offboarding_id.id,
        )

    def onehr_exit_interview_portal_payload(self):
        """Sanitized service payload. HTTP/authentication remain Portal ownership."""
        self.ensure_one()
        self.check_access("read")
        return {
            "reference": self.offboarding_id.name,
            "state": self.state,
            "scheduled_at": fields.Datetime.to_string(self.scheduled_at) if self.scheduled_at else False,
            "primary_exit_reason": self.primary_exit_reason,
            "overall_score": self.overall_score if self.state == "submitted" else False,
        }
