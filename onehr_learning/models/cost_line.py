from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import require_learning_manager, require_learning_officer


class OneHRLearningCostLine(models.Model):
    """Training cost evidence with controlled planned → committed → actual lifecycle."""

    _name = "onehr.learning.cost.line"
    _description = "OneHR Learning Cost Line"
    _inherit = ["onehr.mixin.audit"]
    _order = "cost_date desc, id desc"
    _rec_name = "description"

    _STATE_CONTEXT = "onehr_learning_cost_state_controlled"

    description = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    cost_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    budget_id = fields.Many2one(
        "onehr.learning.budget",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    session_id = fields.Many2one(
        "onehr.learning.session",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    enrollment_id = fields.Many2one(
        "onehr.learning.enrollment",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="enrollment_id.employee_id",
        store=True,
        readonly=True,
        index=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    employee_name = fields.Char(
        related="enrollment_id.employee_name",
        store=True,
        readonly=True,
        index=True,
    )
    vendor_id = fields.Many2one(
        "onehr.learning.vendor",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    cost_type = fields.Selection(
        [
            ("trainer", "Trainer / Facilitation"),
            ("venue", "Venue"),
            ("material", "Learning Materials"),
            ("platform", "Platform / LMS"),
            ("travel", "Travel"),
            ("certification", "Certification Fee"),
            ("reimbursement", "Employee Reimbursement"),
            ("other", "Other"),
        ],
        required=True,
        default="other",
        index=True,
        tracking=True,
    )
    amount = fields.Monetary(
        required=True,
        default=0.0,
        currency_field="currency_id",
        tracking=True,
        aggregator="sum",
    )
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("committed", "Committed"),
            ("actual", "Actual"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="planned",
        index=True,
        tracking=True,
    )
    reimbursable = fields.Boolean(default=False, tracking=True)
    payroll_bridge_eligible = fields.Boolean(
        default=False,
        tracking=True,
        help="Eligibility flag only. Payroll Bridge transport/processing remains downstream-owned.",
    )
    source_reference = fields.Char(index=True, tracking=True)
    note = fields.Text(tracking=True)

    @api.onchange("session_id")
    def _onchange_session_id(self):
        if self.session_id:
            self.company_id = self.session_id.company_id
            self.budget_id = self.budget_id or self.session_id.budget_id

    @api.onchange("enrollment_id")
    def _onchange_enrollment_id(self):
        if self.enrollment_id:
            self.session_id = self.enrollment_id.session_id
            self.company_id = self.enrollment_id.company_id
            self.budget_id = self.budget_id or self.enrollment_id.session_id.budget_id

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "planned") != "planned":
                raise AccessError(_("Learning Costs must be created as Planned."))
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_cost_line()
        return records

    def _write_governed(self, values):
        return super(OneHRLearningCostLine, self).write(values)

    def write(self, values):
        require_learning_officer(self)
        values = dict(values)
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Learning Cost state changes only through governed actions."))
        for record in self:
            if record.state == "actual" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Actual Learning Cost evidence is frozen."))
            if record.state == "committed" and not self.env.context.get(self._STATE_CONTEXT):
                protected = {"amount", "company_id", "budget_id", "session_id", "enrollment_id"}
                if protected & set(values):
                    raise AccessError(_("Committed Learning Cost amount/scope is frozen."))
        result = super().write(values)
        self._validate_cost_line()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_cost_evidence(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "planned":
                raise AccessError(_("Committed/Actual/Cancelled Learning Cost evidence cannot be deleted."))

    @api.constrains(
        "company_id",
        "budget_id",
        "session_id",
        "enrollment_id",
        "vendor_id",
        "amount",
        "reimbursable",
        "payroll_bridge_eligible",
    )
    def _check_cost_line(self):
        self._validate_cost_line()

    def _validate_cost_line(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("Learning Cost amount cannot be negative."))
            if record.budget_id and record.budget_id.company_id != record.company_id:
                raise ValidationError(_("Learning Budget and Cost company must match."))
            if record.session_id and record.session_id.company_id != record.company_id:
                raise ValidationError(_("Learning Session and Cost company must match."))
            if record.enrollment_id:
                if record.enrollment_id.company_id != record.company_id:
                    raise ValidationError(_("Enrollment and Cost company must match."))
                if record.session_id and record.enrollment_id.session_id != record.session_id:
                    raise ValidationError(_("Enrollment must belong to the selected Session."))
            if record.vendor_id and record.vendor_id.company_id != record.company_id:
                raise ValidationError(_("Vendor and Cost company must match."))
            if record.payroll_bridge_eligible and not record.reimbursable:
                raise ValidationError(
                    _("Payroll Bridge eligible Learning Cost must be marked Reimbursable.")
                )
        return True

    def action_commit(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "planned":
                raise UserError(_("Only Planned Learning Costs can be committed."))
            if record.budget_id:
                if record.budget_id.state != "active":
                    raise UserError(_("Selected Learning Budget must be Active before commitment."))
                record.budget_id._assert_cost_capacity(record.amount, excluding_line=record)
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "committed"}
            )
            record.log_business_action(_("Learning Cost committed."))
        return True

    def action_mark_actual(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "committed":
                raise UserError(_("Only Committed Learning Costs can become Actual."))
            if record.budget_id:
                record.budget_id._assert_cost_capacity(record.amount, excluding_line=record)
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "actual"}
            )
            record.log_business_action(_("Learning Cost posted as Actual evidence."))
        return True

    def action_cancel(self):
        require_learning_manager(self)
        for record in self:
            if record.state not in {"planned", "committed"}:
                raise UserError(_("Only Planned/Committed Learning Costs can be cancelled."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "cancelled"}
            )
        return True

    def onehr_payroll_cost_payload(self):
        self.ensure_one()
        require_learning_manager(self)
        if self.state != "actual" or not self.reimbursable or not self.payroll_bridge_eligible:
            raise UserError(_("Only Actual reimbursable/eligible cost may enter the Payroll hand-off payload."))
        return {
            "cost_line_id": self.id,
            "date": fields.Date.to_string(self.cost_date),
            "employee_id": self.employee_id.id if self.employee_id else False,
            "employee_name": self.employee_name or "",
            "session": self.session_id.name if self.session_id else "",
            "course_code": self.session_id.course_id.code if self.session_id else "",
            "cost_type": self.cost_type,
            "amount": self.amount,
            "currency": self.currency_id.name,
            "source_reference": self.source_reference or "",
        }
