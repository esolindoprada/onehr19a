from odoo import _, fields, models

from .action_helpers import open_records_action


class HREmployee(models.Model):
    _inherit = "hr.employee"

    onehr_offboarding_count = fields.Integer(compute="_compute_onehr_offboarding_summary")
    onehr_last_offboarding_id = fields.Many2one("onehr.offboarding", compute="_compute_onehr_offboarding_summary")
    onehr_exit_date = fields.Date(compute="_compute_onehr_offboarding_summary")
    onehr_exit_reason = fields.Selection(
        selection=lambda self: self.env["onehr.offboarding"]._fields["offboarding_type"].selection,
        compute="_compute_onehr_offboarding_summary",
    )

    def _compute_onehr_offboarding_summary(self):
        allowed = self.env.su or self.env.user.has_group(
            "onehr_retirement_offboarding.group_onehr_offboarding_officer"
        )
        Case = self.env["onehr.offboarding"]
        for employee in self:
            employee.onehr_offboarding_count = 0
            employee.onehr_last_offboarding_id = False
            employee.onehr_exit_date = False
            employee.onehr_exit_reason = False
            if not allowed or not employee.id:
                continue
            domain = [("employee_id", "=", employee.id), ("company_id", "in", self.env.companies.ids)]
            employee.onehr_offboarding_count = Case.search_count(domain)
            latest = Case.search(domain, order="effective_exit_date desc, id desc", limit=1)
            employee.onehr_last_offboarding_id = latest
            closed = Case.search(domain + [("state", "=", "closed")], order="effective_exit_date desc, id desc", limit=1)
            if closed:
                employee.onehr_exit_date = closed.effective_exit_date
                employee.onehr_exit_reason = closed.offboarding_type

    def action_open_onehr_offboarding(self):
        self.ensure_one()
        return open_records_action(
            name=_("Offboarding — %s", self.display_name),
            res_model="onehr.offboarding",
            domain=[("employee_id", "=", self.id)],
            context={"default_employee_id": self.id, "default_company_id": self.company_id.id},
            view_mode="kanban,list,form",
        )
