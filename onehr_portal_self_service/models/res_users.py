
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    onehr_portal_employee_id = fields.Many2one(
        "hr.employee",
        string="OneHR Portal Employee",
        related="employee_id",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_self_service_enabled = fields.Boolean(
        related="employee_id.onehr_portal_self_service_enabled",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_employee_name = fields.Char(
        related="employee_id.name",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_department_name = fields.Char(
        related="employee_id.department_id.name",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_job_name = fields.Char(
        related="employee_id.job_id.name",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_manager_name = fields.Char(
        related="employee_id.parent_id.name",
        readonly=True,
        compute_sudo=True,
    )
    onehr_portal_position_code = fields.Char(
        related="employee_id.onehr_primary_position_id.code",
        readonly=True,
        compute_sudo=True,
    )

    def onehr_portal_profile_payload(self):
        self.ensure_one()
        if self != self.env.user:
            self.check_access("read")
        return {
            "employee_id": self.onehr_portal_employee_id.id,
            "employee_name": self.onehr_portal_employee_name or "",
            "employee_number": self.onehr_portal_employee_number or "",
            "department": self.onehr_portal_department_name or "",
            "job": self.onehr_portal_job_name or "",
            "manager": self.onehr_portal_manager_name or "",
            "position_code": self.onehr_portal_position_code or "",
            "self_service_enabled": bool(self.onehr_portal_self_service_enabled),
        }

    def action_open_my_portal_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "My HR Requests",
            "res_model": "onehr.portal.request",
            "view_mode": "list,kanban,form",
            "domain": [("employee_user_id", "=", self.id)],
        }

