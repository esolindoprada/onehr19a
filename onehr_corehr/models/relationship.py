from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_record_action, require_corehr_officer


class OneHREmployeeDependent(models.Model):
    _name = "onehr.employee.dependent"
    _description = "OneHR Employee Dependent"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "employee_id, relationship, name"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    name = fields.Char(required=True, tracking=True)
    relationship = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("child", "Child"),
            ("parent", "Parent"),
            ("sibling", "Sibling"),
            ("guardian", "Guardian"),
            ("other", "Other"),
        ],
        required=True,
        tracking=True,
    )
    birth_date = fields.Date(tracking=True)
    contact_phone = fields.Char()
    contact_email = fields.Char()
    benefit_eligible = fields.Boolean(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()

    @api.constrains("birth_date")
    def _check_birth_date(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.birth_date and record.birth_date > today:
                raise ValidationError(_("Dependent birth date cannot be in the future."))

    def action_expire(self):
        require_corehr_officer(self.env)
        today = fields.Date.context_today(self)
        self.write({"valid_to": today, "active": False})
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_corehr_officer(self.env)
        return open_record_action(
            name=self.employee_id.display_name,
            res_model="hr.employee",
            res_id=self.employee_id.id,
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Dependent history cannot be deleted. End-date/archive it instead."))


class OneHREmployeeEmergencyContact(models.Model):
    _name = "onehr.employee.emergency.contact"
    _description = "OneHR Employee Emergency Contact"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "employee_id, is_primary desc, priority, name"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    name = fields.Char(required=True, tracking=True)
    relationship = fields.Char(required=True, tracking=True)
    phone = fields.Char(required=True, tracking=True)
    email = fields.Char()
    priority = fields.Integer(default=10, required=True)
    is_primary = fields.Boolean(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()

    @api.constrains("priority")
    def _check_priority(self):
        for record in self:
            if record.priority < 1:
                raise ValidationError(_("Emergency contact priority must be at least 1."))

    @api.constrains("employee_id", "is_primary", "active", "valid_from", "valid_to")
    def _check_single_effective_primary(self):
        for record in self.filtered(lambda item: item.active and item.is_primary):
            domain = record._overlap_domain(
                ["employee_id"],
                [("active", "=", True), ("is_primary", "=", True)],
            )
            if self.search_count(domain, limit=1):
                raise ValidationError(_("Only one effective primary emergency contact is allowed per employee."))

    def action_set_primary(self):
        require_corehr_officer(self.env)
        today = fields.Date.context_today(self)
        for record in self:
            if not record.active or not record.is_effective_on(today):
                raise ValidationError(_("Only an effective active contact can become primary."))
            others = self.search(
                [
                    ("employee_id", "=", record.employee_id.id),
                    ("id", "!=", record.id),
                    ("is_primary", "=", True),
                ]
            )
            others.write({"is_primary": False})
            record.write({"is_primary": True})
        return True

    def action_expire(self):
        require_corehr_officer(self.env)
        self.write({"valid_to": fields.Date.context_today(self), "active": False, "is_primary": False})
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_corehr_officer(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Emergency-contact history cannot be deleted. End-date/archive it instead."))
