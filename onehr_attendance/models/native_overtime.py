from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import display_notification, open_record_action


class HrAttendanceOvertimeLine(models.Model):
    """Registry concept ``hr.attendance.overtime`` mapped to Odoo 19 actual overtime line."""

    _inherit = "hr.attendance.overtime.line"

    onehr_payroll_code_snapshot = fields.Char(compute="_compute_onehr_policy_metadata", store=True, index=True)
    onehr_policy_reference = fields.Char(compute="_compute_onehr_policy_metadata", store=True)
    onehr_export_ready = fields.Boolean(compute="_compute_onehr_policy_metadata", store=True, index=True)

    @api.depends("status", "rule_ids", "rule_ids.onehr_payroll_code", "rule_ids.onehr_policy_code", "rule_ids.paid")
    def _compute_onehr_policy_metadata(self):
        for overtime in self:
            payroll_codes = sorted(set(filter(None, overtime.rule_ids.mapped("onehr_payroll_code"))))
            policy_codes = sorted(set(filter(None, overtime.rule_ids.mapped("onehr_policy_code"))))
            overtime.onehr_payroll_code_snapshot = ",".join(payroll_codes)
            overtime.onehr_policy_reference = ",".join(policy_codes)
            overtime.onehr_export_ready = overtime.status == "approved" and bool(overtime.rule_ids.filtered("paid"))

    def action_onehr_open_employee(self):
        self.ensure_one()
        return open_record_action(self.employee_id.name, "hr.employee", self.employee_id.id)

    def action_onehr_open_attendance(self):
        self.ensure_one()
        attendance = self.env["hr.attendance"].search([
            ("employee_id", "=", self.employee_id.id),
            ("check_in", "=", self.time_start),
        ], limit=1)
        if not attendance:
            return display_notification(_("No canonical attendance starts at this overtime line's Start timestamp."), notification_type="warning")
        return open_record_action(attendance.display_name, "hr.attendance", attendance.id)


class HrAttendanceOvertimeRule(models.Model):
    """Policy metadata only; native Odoo 19 overtime calculation remains authoritative."""

    _inherit = "hr.attendance.overtime.rule"

    onehr_policy_code = fields.Char(string="OneHR Policy Code", index=True)
    onehr_payroll_code = fields.Char(string="Payroll Export Code", index=True)
    onehr_policy_note = fields.Text(string="OneHR Policy Note")

    def action_onehr_open_ruleset(self):
        self.ensure_one()
        return open_record_action(self.ruleset_id.display_name, "hr.attendance.overtime.ruleset", self.ruleset_id.id)


class HrAttendanceOvertimeRuleset(models.Model):
    """Effective-policy metadata on the native Odoo overtime ruleset."""

    _inherit = "hr.attendance.overtime.ruleset"

    onehr_policy_reference = fields.Char(string="Policy Reference", index=True)
    onehr_valid_from = fields.Date(string="Policy Valid From", default=fields.Date.context_today, index=True)
    onehr_valid_to = fields.Date(string="Policy Valid To", index=True)

    @api.constrains("onehr_valid_from", "onehr_valid_to")
    def _check_onehr_policy_interval(self):
        for ruleset in self:
            if ruleset.onehr_valid_from and ruleset.onehr_valid_to and ruleset.onehr_valid_to < ruleset.onehr_valid_from:
                raise ValidationError(_("Overtime Ruleset Policy Valid To cannot be earlier than Valid From."))
