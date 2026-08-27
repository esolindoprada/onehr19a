from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .action_helpers import open_records_action


class OneHRApprovalKPIDaily(models.Model):
    _name = "onehr.approval.kpi.daily"
    _description = "OneHR Daily Approval KPI Snapshot"
    _order = "snapshot_date desc, company_id, rule_id"

    snapshot_date = fields.Date(required=True, index=True, readonly=True)
    as_of_at = fields.Datetime(required=True, readonly=True)
    company_id = fields.Many2one(
        "res.company", required=True, ondelete="cascade", index=True, readonly=True
    )
    rule_id = fields.Many2one(
        "onehr.approval.rule", required=True, ondelete="cascade", index=True, readonly=True
    )

    submitted_count = fields.Integer(readonly=True)
    pending_count = fields.Integer(readonly=True)
    approved_count = fields.Integer(readonly=True)
    rejected_count = fields.Integer(readonly=True)
    executed_count = fields.Integer(readonly=True)
    overdue_count = fields.Integer(readonly=True)
    average_cycle_hours = fields.Float(readonly=True)
    average_pending_age_hours = fields.Float(readonly=True)

    _unique_daily_rule_snapshot = models.Constraint(
        "UNIQUE(snapshot_date, company_id, rule_id)",
        "Only one daily approval KPI snapshot is allowed per company and rule.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_kpi_engine"):
            raise AccessError(_("Approval KPI snapshots are generated only by the workflow engine."))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Approval KPI snapshots are immutable."))

    @api.ondelete(at_uninstall=False)
    def _unlink_immutable_snapshots(self):
        raise AccessError(_("Approval KPI snapshots cannot be deleted."))

    @api.model
    def _cron_build_daily_kpi(self):
        snapshot_date = fields.Date.context_today(self)
        as_of_at = fields.Datetime.now()
        Request = self.env["onehr.approval.request"]

        grouped = defaultdict(lambda: self.env["onehr.approval.request"])
        for request in Request.search([("rule_id", "!=", False)]):
            grouped[(request.company_id.id, request.rule_id.id)] |= request

        for (company_id, rule_id), requests in grouped.items():
            if self.search_count(
                [
                    ("snapshot_date", "=", snapshot_date),
                    ("company_id", "=", company_id),
                    ("rule_id", "=", rule_id),
                ],
                limit=1,
            ):
                # ED4 means the first generated daily snapshot remains immutable.
                continue

            finalized = requests.filtered("finalized_at")
            pending = requests.filtered(lambda item: item.state == "pending")
            final_hours = finalized.mapped("cycle_hours")
            pending_hours = pending.mapped("cycle_hours")
            values = {
                "snapshot_date": snapshot_date,
                "as_of_at": as_of_at,
                "company_id": company_id,
                "rule_id": rule_id,
                "submitted_count": len(requests.filtered("submitted_at")),
                "pending_count": len(pending),
                "approved_count": len(requests.filtered(lambda item: item.state == "approved")),
                "rejected_count": len(requests.filtered(lambda item: item.state == "rejected")),
                "executed_count": len(requests.filtered(lambda item: item.state == "executed")),
                "overdue_count": len(pending.filtered(lambda item: item.sla_status == "overdue")),
                "average_cycle_hours": sum(final_hours) / len(final_hours) if final_hours else 0.0,
                "average_pending_age_hours": (
                    sum(pending_hours) / len(pending_hours) if pending_hours else 0.0
                ),
            }
            self.with_context(onehr_kpi_engine=True).create(values)
        return True

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Approval Requests — %s", self.rule_id.display_name),
            res_model="onehr.approval.request",
            domain=[
                ("company_id", "=", self.company_id.id),
                ("rule_id", "=", self.rule_id.id),
            ],
        )
