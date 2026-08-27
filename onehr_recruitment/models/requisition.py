from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_recruiter, require_recruitment_manager


class OneHRRecruitmentRequisition(models.Model):
    """Approved demand to recruit against an Odoo-native job/OneHR position.

    ED3: once submitted, the demand facts are frozen. Approval evidence belongs
    to onehr_workflow_approval; this model remains owner of recruitment state.
    """

    _name = "onehr.recruitment.requisition"
    _description = "OneHR Recruitment Requisition"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "request_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Requisition Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    title = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True, ondelete="restrict"
    )
    job_id = fields.Many2one(
        "hr.job", required=True, index=True, tracking=True, ondelete="restrict", check_company=True
    )
    position_id = fields.Many2one(
        "onehr.position", string="Position", index=True, tracking=True,
        ondelete="restrict", check_company=True,
        help="Optional authorized OneHR position/seat this requisition intends to fill.",
    )
    department_id = fields.Many2one(
        "hr.department", related="job_id.department_id", store=True, index=True, readonly=True
    )
    requester_user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        index=True, tracking=True, ondelete="restrict"
    )
    recruiter_user_id = fields.Many2one(
        "res.users", string="Recruiter", index=True, tracking=True, ondelete="set null"
    )
    hiring_manager_user_id = fields.Many2one(
        "res.users", string="Hiring Manager", index=True, tracking=True, ondelete="set null"
    )
    request_date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    target_start_date = fields.Date(index=True, tracking=True)
    target_fill_date = fields.Date(index=True, tracking=True)
    requested_headcount = fields.Integer(required=True, default=1, tracking=True)
    approved_headcount = fields.Integer(readonly=True, tracking=True, copy=False)
    urgency = fields.Selection(
        [("normal", "Normal"), ("high", "High"), ("critical", "Critical")],
        required=True, default="normal", index=True, tracking=True
    )
    employment_basis = fields.Selection(
        [
            ("replacement", "Replacement"),
            ("growth", "Growth / New Position"),
            ("temporary", "Temporary / Project"),
            ("internship", "Internship / Trainee"),
        ],
        required=True, default="replacement", tracking=True,
    )
    reason = fields.Text(required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("recruiting", "Recruiting"),
            ("filled", "Filled"),
            ("cancelled", "Cancelled"),
        ],
        required=True, default="draft", index=True, tracking=True, copy=False,
    )
    submitted_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    approved_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    recruiting_started_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    filled_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    cancelled_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    cancellation_reason = fields.Text(copy=False, tracking=True)

    applicant_ids = fields.One2many("hr.applicant", "onehr_requisition_id", string="Applicants")
    applicant_count = fields.Integer(compute="_compute_pipeline_counts")
    hired_count = fields.Integer(compute="_compute_pipeline_counts")
    interview_count = fields.Integer(compute="_compute_pipeline_counts")
    offer_count = fields.Integer(compute="_compute_pipeline_counts")

    _FROZEN_AFTER_SUBMISSION = {
        "company_id", "job_id", "position_id", "request_date", "requested_headcount",
        "employment_basis", "reason",
    }

    @api.model_create_multi
    def create(self, vals_list):
        require_recruiter(self)
        for values in vals_list:
            if values.get("name", _("New")) in (False, _("New")):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.recruitment.requisition") or _("New")
            job = self.env["hr.job"].browse(values.get("job_id"))
            values.setdefault("title", job.name if job else _("Recruitment Requisition"))
        return super().create(vals_list)

    def write(self, values):
        if self._FROZEN_AFTER_SUBMISSION.intersection(values):
            blocked = self.filtered(lambda rec: rec.state != "draft")
            if blocked:
                raise AccessError(_("Submitted requisition demand facts are historical evidence and cannot be rewritten."))
        return super().write(values)

    @api.depends("applicant_ids.application_status", "applicant_ids.onehr_interview_session_ids", "applicant_ids.onehr_offer_ids")
    def _compute_pipeline_counts(self):
        for requisition in self:
            requisition.applicant_count = len(requisition.applicant_ids)
            requisition.hired_count = len(requisition.applicant_ids.filtered(lambda app: app.application_status == "hired"))
            requisition.interview_count = self.env["onehr.interview.session"].search_count([("requisition_id", "=", requisition.id)])
            requisition.offer_count = self.env["onehr.offer"].search_count([("requisition_id", "=", requisition.id)])

    @api.constrains("requested_headcount", "approved_headcount")
    def _check_headcount(self):
        for rec in self:
            if rec.requested_headcount <= 0:
                raise ValidationError(_("Requested headcount must be greater than zero."))
            if rec.approved_headcount < 0:
                raise ValidationError(_("Approved headcount cannot be negative."))
            if rec.approved_headcount > rec.requested_headcount:
                raise ValidationError(_("Approved headcount cannot exceed requested headcount."))

    @api.constrains("target_start_date", "target_fill_date", "request_date")
    def _check_dates(self):
        for rec in self:
            if rec.target_fill_date and rec.target_fill_date < rec.request_date:
                raise ValidationError(_("Target fill date cannot be before request date."))
            if rec.target_start_date and rec.target_fill_date and rec.target_start_date < rec.target_fill_date:
                # A start date before the target fill date is contradictory for a normal hire plan.
                raise ValidationError(_("Target start date cannot be before target fill date."))

    @api.constrains("job_id", "position_id", "company_id")
    def _check_scope_alignment(self):
        for rec in self:
            if rec.job_id.company_id and rec.job_id.company_id != rec.company_id:
                raise ValidationError(_("Job and requisition must belong to the same company."))
            if rec.position_id:
                if rec.position_id.company_id != rec.company_id:
                    raise ValidationError(_("Position and requisition must belong to the same company."))
                if rec.position_id.job_id != rec.job_id:
                    raise ValidationError(_("Position job must match the requisition job."))

    def _approval_payload(self):
        self.ensure_one()
        return {
            "requisition": self.name,
            "title": self.title,
            "job": self.job_id.display_name,
            "position": self.position_id.display_name if self.position_id else False,
            "requested_headcount": self.requested_headcount,
            "urgency": self.urgency,
            "employment_basis": self.employment_basis,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = [self.hiring_manager_user_id.id] if self.hiring_manager_user_id else []
        values.update({
            "document_type": "recruitment_requisition",
            "risk_level": "high" if self.urgency == "critical" else "normal",
            "manager_user_ids": manager_ids,
            "extra": {
                "job_id": self.job_id.id,
                "position_id": self.position_id.id,
                "requested_headcount": self.requested_headcount,
                "employment_basis": self.employment_basis,
            },
        })
        return values

    def action_submit_for_approval(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "draft":
            raise UserError(_("Only a draft requisition can be submitted."))
        self.write({"state": "pending_approval", "submitted_at": fields.Datetime.now()})
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "pending_approval":
            return True
        if decision == "approve":
            self.write({
                "state": "approved",
                "approved_headcount": self.requested_headcount,
                "approved_at": fields.Datetime.now(),
            })
        elif decision == "reject":
            self.write({"state": "rejected"})
        return True

    def action_start_recruiting(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "approved":
            raise UserError(_("Only an approved requisition can start recruiting."))
        self.write({"state": "recruiting", "recruiting_started_at": fields.Datetime.now()})
        request = self.env["onehr.approval.request"].search(
            [("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")],
            order="requested_at desc, id desc", limit=1,
        )
        if request:
            self.onehr_mark_approval_executed(request)
        return True

    def action_mark_filled(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state != "recruiting":
            raise UserError(_("Only a recruiting requisition can be marked filled."))
        if self.hired_count < self.approved_headcount:
            raise UserError(_("Hired applicant count has not reached the approved headcount."))
        self.write({"state": "filled", "filled_at": fields.Datetime.now()})
        return True

    def action_cancel(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state in {"filled", "cancelled"}:
            raise UserError(_("Filled or cancelled requisitions cannot be cancelled again."))
        if not self.cancellation_reason:
            raise UserError(_("Enter a cancellation reason before cancelling the requisition."))
        self.write({"state": "cancelled", "cancelled_at": fields.Datetime.now()})
        return True

    def action_create_applicant(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "recruiting":
            raise UserError(_("Applicants may only be created against an active recruiting requisition."))
        return {
            "type": "ir.actions.act_window",
            "name": _("New Applicant"),
            "res_model": "hr.applicant",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_onehr_requisition_id": self.id,
                "default_job_id": self.job_id.id,
                "default_company_id": self.company_id.id,
                "default_user_id": self.recruiter_user_id.id,
            },
        }

    def action_open_applicants(self):
        self.ensure_one()
        return open_records_action(
            name=_("Applicants — %s", self.name), res_model="hr.applicant",
            domain=[("onehr_requisition_id", "=", self.id)],
            context={"default_onehr_requisition_id": self.id, "default_job_id": self.job_id.id},
            view_mode="kanban,list,form,pivot,graph",
        )

    def action_open_interviews(self):
        self.ensure_one()
        return open_records_action(
            name=_("Interviews — %s", self.name), res_model="onehr.interview.session",
            domain=[("requisition_id", "=", self.id)],
            context={"default_requisition_id": self.id}, view_mode="calendar,list,form",
        )

    def action_open_offers(self):
        self.ensure_one()
        return open_records_action(
            name=_("Offers — %s", self.name), res_model="onehr.offer",
            domain=[("requisition_id", "=", self.id)], context={"default_requisition_id": self.id},
        )

    def action_open_position(self):
        self.ensure_one()
        if not self.position_id:
            raise UserError(_("This requisition is not linked to a OneHR position."))
        return open_record_action(name=_("Position"), res_model="onehr.position", res_id=self.position_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "draft" for rec in self):
            raise UserError(_("Only draft requisitions may be deleted. Historical requisitions must be retained."))
