
from odoo import _, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    onehr_portal_self_service_enabled = fields.Boolean(
        string="Portal Self-Service Enabled",
        default=True,
        tracking=True,
        groups="hr.group_hr_user",
        help="Controls whether this employee may create OneHR self-service requests through their linked user account.",
    )
    onehr_portal_request_count = fields.Integer(
        compute="_compute_onehr_portal_request_count",
        groups="hr.group_hr_user",
    )

    def _compute_onehr_portal_request_count(self):
        Request = self.env["onehr.portal.request"]
        for employee in self:
            employee.onehr_portal_request_count = Request.search_count([("employee_id", "=", employee.id)])

    def action_open_onehr_portal_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Self-Service Requests — %s", self.name),
            "res_model": "onehr.portal.request",
            "view_mode": "list,kanban,form,pivot,graph",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }

