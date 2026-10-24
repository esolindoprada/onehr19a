
from odoo import _, fields, models

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_assignment_officer


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    onehr_assignment_count = fields.Integer(
        string="Assignments", compute="_compute_onehr_assignment_summary",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_current_primary_assignment_id = fields.Many2one(
        "onehr.assignment", string="Current Primary Assignment",
        compute="_compute_onehr_assignment_summary",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )

    def _compute_onehr_assignment_summary(self):
        Assignment = self.env["onehr.assignment"]
        today = fields.Date.context_today(self)
        for employee in self:
            employee.onehr_assignment_count = Assignment.search_count([("employee_id", "=", employee.id)])
            employee.onehr_current_primary_assignment_id = Assignment.search([
                ("employee_id", "=", employee.id),
                ("assignment_type", "=", "primary"),
                ("state", "=", "active"),
                ("effective_from", "<=", today),
                "|", ("effective_to", "=", False), ("effective_to", ">=", today),
            ], order="effective_from desc, id desc", limit=1)

    def action_open_onehr_assignments(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_records_action(
            name=_("Assignments — %s", self.display_name),
            res_model="onehr.assignment",
            domain=[("employee_id", "=", self.id)],
            context={"default_employee_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_onehr_current_primary_assignment(self):
        self.ensure_one()
        require_assignment_officer(self)
        if not self.onehr_current_primary_assignment_id:
            return self.action_open_onehr_assignments()
        return open_record_action(
            name=self.onehr_current_primary_assignment_id.display_name,
            res_model="onehr.assignment",
            res_id=self.onehr_current_primary_assignment_id.id,
        )


class OneHRPosition(models.Model):
    _inherit = "onehr.position"

    onehr_assignment_count = fields.Integer(
        string="Assignments", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_active_headcount = fields.Integer(
        string="Current Headcount", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_active_fte = fields.Float(
        string="Current FTE", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_available_headcount = fields.Integer(
        string="Available Headcount", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_available_fte = fields.Float(
        string="Available FTE", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_occupancy_state = fields.Selection(
        [("vacant", "Vacant"), ("partial", "Partially Filled"), ("filled", "Filled"), ("over", "Over Capacity")],
        compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    onehr_position_budget_count = fields.Integer(
        string="Position Budgets", compute="_compute_onehr_occupancy",
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )

    def _compute_onehr_occupancy(self):
        Assignment = self.env["onehr.assignment"]
        Budget = self.env["onehr.position.budget"]
        today = fields.Date.context_today(self)
        for position in self:
            current = Assignment.search([
                ("position_id", "=", position.id),
                ("state", "=", "active"),
                ("effective_from", "<=", today),
                "|", ("effective_to", "=", False), ("effective_to", ">=", today),
            ])
            position.onehr_assignment_count = Assignment.search_count([("position_id", "=", position.id)])
            position.onehr_active_headcount = len(current)
            position.onehr_active_fte = sum(current.mapped("fte"))
            active_budget = Budget.search([
                ("position_id", "=", position.id), ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|", ("valid_to", "=", False), ("valid_to", ">=", today),
            ], order="valid_from desc, id desc", limit=1)
            allowed_hc = active_budget.authorized_headcount if active_budget else position.authorized_headcount
            allowed_fte = active_budget.authorized_fte if active_budget else position.authorized_fte
            position.onehr_available_headcount = allowed_hc - position.onehr_active_headcount
            position.onehr_available_fte = allowed_fte - position.onehr_active_fte
            if position.onehr_active_headcount == 0 and position.onehr_active_fte <= 0.000001:
                occupancy = "vacant"
            elif position.onehr_active_headcount > allowed_hc or position.onehr_active_fte > allowed_fte + 0.000001:
                occupancy = "over"
            elif position.onehr_active_headcount >= allowed_hc or position.onehr_active_fte >= allowed_fte - 0.000001:
                occupancy = "filled"
            else:
                occupancy = "partial"
            position.onehr_occupancy_state = occupancy
            position.onehr_position_budget_count = Budget.search_count([("position_id", "=", position.id)])

    def action_open_onehr_position_assignments(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_records_action(
            name=_("Assignments — %s", self.display_name),
            res_model="onehr.assignment",
            domain=[("position_id", "=", self.id)],
            context={"default_position_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_onehr_position_budgets(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_records_action(
            name=_("Position Budgets — %s", self.display_name),
            res_model="onehr.position.budget",
            domain=[("position_id", "=", self.id)],
            context={"default_position_id": self.id},
        )
