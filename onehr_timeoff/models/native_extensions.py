from odoo import _, fields, models

from .action_helpers import open_records_action
from .authority_helpers import require_timeoff_manager


class HrEmployee(models.Model):
    """Narrow navigation extension; employee identity remains Odoo/Core HR owned."""

    _inherit = "hr.employee"

    onehr_leave_request_count = fields.Integer(
        string="Leave Requests", compute="_compute_onehr_timeoff_counts"
    )
    onehr_leave_allocation_count = fields.Integer(
        string="Leave Allocations", compute="_compute_onehr_timeoff_counts"
    )
    onehr_current_leave_count = fields.Integer(
        string="Current Leave", compute="_compute_onehr_timeoff_counts"
    )

    def _compute_onehr_timeoff_counts(self):
        Request = self.env["onehr.leave.request"]
        Allocation = self.env["onehr.leave.allocation"]
        today = fields.Date.context_today(self)
        for employee in self:
            employee.onehr_leave_request_count = Request.search_count([
                ("employee_id", "=", employee.id)
            ])
            employee.onehr_leave_allocation_count = Allocation.search_count([
                ("employee_id", "=", employee.id),
                ("allocation_scope", "=", "single"),
            ])
            employee.onehr_current_leave_count = Request.search_count([
                ("employee_id", "=", employee.id),
                ("state", "=", "approved"),
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ])

    def action_open_onehr_leave_requests(self):
        self.ensure_one()
        require_timeoff_manager(self)
        return open_records_action(
            name=_("Leave Requests — %s", self.display_name),
            res_model="onehr.leave.request",
            domain=[("employee_id", "=", self.id)],
            context={"default_employee_id": self.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_onehr_leave_allocations(self):
        self.ensure_one()
        require_timeoff_manager(self)
        return open_records_action(
            name=_("Leave Allocations — %s", self.display_name),
            res_model="onehr.leave.allocation",
            domain=[("employee_id", "=", self.id), ("allocation_scope", "=", "single")],
            context={"default_employee_id": self.id},
            view_mode="list,pivot,graph,form",
        )
