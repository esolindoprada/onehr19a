from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action
from .authority_helpers import require_recruiter, require_recruitment_manager


class OneHRPreboarding(models.Model):
    """Idempotent bridge from accepted candidate to employee/checklist (ED3).

    This addon orchestrates hire conversion. It does not own employment contract,
    assignment, attendance or access-provisioning records; downstream owners can
    extend the narrow post-hire hook later without reverse dependencies.
    """

    _name = "onehr.preboarding"
    _description = "OneHR Preboarding"
    _inherit = ["onehr.mixin.audit"]
    _order = "planned_start_date desc, id desc"

    name = fields.Char(
        required=True, default=lambda self: _("New Preboarding"),
        readonly=True, copy=False, index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True, ondelete="restrict",
    )
    applicant_id = fields.Many2one(
        "hr.applicant", required=True, index=True, tracking=True,
        ondelete="restrict", check_company=True,
    )
    requisition_id = fields.Many2one(
        "onehr.recruitment.requisition", index=True, tracking=True,
        ondelete="set null", check_company=True,
    )
    offer_id = fields.Many2one(
        "onehr.offer", index=True, tracking=True, ondelete="restrict", check_company=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", readonly=True, index=True, copy=False,
        ondelete="restrict", check_company=True,
    )
    planned_start_date = fields.Date(
        required=True, default=fields.Date.context_today, index=True, tracking=True,
    )
    checklist_instance_id = fields.Many2one(
        "onehr.checklist.instance", string="Onboarding Checklist",
        readonly=True, copy=False, ondelete="restrict",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        required=True, default="draft", index=True, tracking=True, copy=False,
    )
    prepared_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    completed_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    cancellation_reason = fields.Text(copy=False, tracking=True)
    checklist_task_count = fields.Integer(
        related="checklist_instance_id.task_count", readonly=True, string="Checklist Tasks"
    )
    checklist_pending_task_count = fields.Integer(
        related="checklist_instance_id.pending_task_count", readonly=True, string="Pending Tasks"
    )
    checklist_completed_task_count = fields.Integer(
        related="checklist_instance_id.completed_task_count", readonly=True, string="Completed Tasks"
    )

    _PROTECTED_SCOPE = {"company_id", "applicant_id", "requisition_id", "offer_id", "planned_start_date"}

    @api.model_create_multi
    def create(self, vals_list):
        require_recruiter(self)
        for values in vals_list:
            applicant = self.env["hr.applicant"].browse(values.get("applicant_id"))
            values.setdefault("company_id", applicant.company_id.id or self.env.company.id)
            values.setdefault("requisition_id", applicant.onehr_requisition_id.id)
            if values.get("offer_id"):
                offer = self.env["onehr.offer"].browse(values["offer_id"])
                values.setdefault("planned_start_date", offer.proposed_start_date or fields.Date.today())
            values.setdefault("name", _("Preboarding — %s", applicant.partner_name or applicant.display_name))
        records = super().create(vals_list)
        records._check_unique_active_preboarding()
        return records

    def write(self, values):
        if self._PROTECTED_SCOPE.intersection(values) and self.filtered(lambda rec: rec.state != "draft"):
            raise AccessError(_("Prepared preboarding scope is historical evidence and cannot be rewritten."))
        result = super().write(values)
        if self._PROTECTED_SCOPE.intersection(values):
            self._check_unique_active_preboarding()
        return result

    def _check_unique_active_preboarding(self):
        for record in self.filtered(lambda rec: rec.state != "cancelled"):
            if self.search_count([
                ("id", "!=", record.id),
                ("applicant_id", "=", record.applicant_id.id),
                ("state", "!=", "cancelled"),
            ]):
                raise ValidationError(_("An applicant may have only one active preboarding orchestration."))

    @api.constrains("applicant_id", "requisition_id", "offer_id", "company_id", "planned_start_date")
    def _check_scope_alignment(self):
        for record in self:
            if record.applicant_id.company_id and record.applicant_id.company_id != record.company_id:
                raise ValidationError(_("Applicant and preboarding must belong to the same company."))
            if record.requisition_id and record.requisition_id.company_id != record.company_id:
                raise ValidationError(_("Requisition and preboarding must belong to the same company."))
            if record.offer_id:
                if record.offer_id.company_id != record.company_id:
                    raise ValidationError(_("Offer and preboarding must belong to the same company."))
                if record.offer_id.applicant_id != record.applicant_id:
                    raise ValidationError(_("Preboarding offer must belong to the selected applicant."))
            if not record.planned_start_date:
                raise ValidationError(_("Planned start date is required."))

    def action_ready(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "draft":
            raise UserError(_("Only draft preboarding can be marked ready."))
        if self.offer_id and self.offer_id.state != "accepted":
            raise UserError(_("Linked offer must be accepted before preboarding is ready."))
        self.write({"state": "ready"})
        return True

    def _ensure_employee(self):
        self.ensure_one()
        applicant = self.applicant_id
        if self.employee_id:
            return self.employee_id
        if applicant.employee_id:
            self.write({"employee_id": applicant.employee_id.id})
            return applicant.employee_id

        # Creating the canonical employee is a high-impact HR master-data action.
        # Recruiters may orchestrate preboarding, but only Recruitment Managers
        # may invoke Odoo's native applicant-to-employee conversion path.
        require_recruitment_manager(self)

        if self.offer_id and self.offer_id.state != "accepted":
            raise UserError(_("Employee conversion requires an accepted offer."))
        if applicant.application_status != "hired" and not applicant.date_closed:
            raise UserError(_("Mark the native Odoo application as hired before employee conversion."))

        # Deliberately use Odoo's native conversion path instead of duplicating
        # employee creation logic. Native Odoo security still applies.
        applicant.create_employee_from_applicant()
        if not applicant.employee_id:
            raise UserError(_("Odoo employee conversion did not link an employee to the applicant."))
        self.write({"employee_id": applicant.employee_id.id})
        return applicant.employee_id

    def _find_hire_checklist_template(self):
        self.ensure_one()
        event_type = self.env["onehr.lifecycle.event.type"].search([("code", "=", "HIRE")], limit=1)
        if not event_type:
            raise UserError(_("OneHR lifecycle event type HIRE is missing."))
        template = self.env["onehr.checklist.template"].search(
            [
                ("lifecycle_event_type_id", "=", event_type.id),
                ("state", "=", "active"),
                ("valid_from", "<=", self.planned_start_date),
                "|", ("valid_to", "=", False), ("valid_to", ">=", self.planned_start_date),
                "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
            ],
            order="company_id desc, version desc, id desc",
            limit=1,
        )
        if not template:
            raise UserError(_("No active HIRE checklist template is effective for the planned start date."))
        return template

    def _onehr_post_hire_orchestration(self, employee):
        """Downstream contract/assignment/access owners may extend this hook."""
        self.ensure_one()
        return True

    def action_prepare(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state not in {"ready", "in_progress"}:
            raise UserError(_("Preboarding must be Ready before preparation."))
        employee = self._ensure_employee()
        checklist = self.checklist_instance_id
        if not checklist:
            template = self._find_hire_checklist_template()
            checklist = self.env["onehr.checklist.instance"].create({
                "employee_id": employee.id,
                "company_id": self.company_id.id,
                "template_id": template.id,
                "event_date": self.planned_start_date,
                "source_model": self._name,
                "source_res_id": self.id,
            })
            self.write({"checklist_instance_id": checklist.id})
        if self.state != "in_progress":
            self.write({"state": "in_progress", "prepared_at": fields.Datetime.now()})
        self._onehr_post_hire_orchestration(employee)
        return self.action_open_checklist()

    def action_schedule_outstanding_activities(self):
        self.ensure_one()
        require_recruiter(self)
        if not self.checklist_instance_id:
            raise UserError(_("Prepare preboarding first to allocate the onboarding checklist."))
        self.checklist_instance_id.action_schedule_outstanding_activities()
        return True

    def action_complete(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "in_progress":
            raise UserError(_("Only in-progress preboarding can be completed."))
        if not self.checklist_instance_id or self.checklist_instance_id.state != "completed":
            raise UserError(_("Complete the governed onboarding checklist before completing preboarding."))
        self.write({"state": "completed", "completed_at": fields.Datetime.now()})
        return True

    def action_cancel(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state in {"completed", "cancelled"}:
            raise UserError(_("Completed or cancelled preboarding cannot be cancelled again."))
        if not self.cancellation_reason:
            raise UserError(_("Enter a cancellation reason before cancelling preboarding."))
        if self.checklist_instance_id and self.checklist_instance_id.state in {"draft", "in_progress"}:
            self.checklist_instance_id.action_cancel()
        self.write({"state": "cancelled"})
        return True

    def action_open_self(self):
        self.ensure_one()
        return open_record_action(name=_("Preboarding"), res_model=self._name, res_id=self.id)

    def action_open_applicant(self):
        self.ensure_one()
        return open_record_action(name=_("Applicant"), res_model="hr.applicant", res_id=self.applicant_id.id)

    def action_open_employee(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_("No employee has been linked yet."))
        return open_record_action(name=_("Employee"), res_model="hr.employee", res_id=self.employee_id.id)

    def action_open_checklist(self):
        self.ensure_one()
        if not self.checklist_instance_id:
            raise UserError(_("No onboarding checklist has been allocated yet."))
        return open_record_action(
            name=_("Onboarding Checklist"), res_model="onehr.checklist.instance", res_id=self.checklist_instance_id.id
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "draft" or rec.employee_id or rec.checklist_instance_id for rec in self):
            raise UserError(_("Only untouched draft preboarding records may be deleted."))
