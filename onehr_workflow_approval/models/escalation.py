
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .action_helpers import open_record_action


class OneHRApprovalEscalationLog(models.Model):
    _name = "onehr.approval.escalation.log"
    _description = "OneHR Approval SLA / Escalation Evidence"
    _order = "event_at desc, id desc"

    request_id = fields.Many2one(
        "onehr.approval.request", required=True, ondelete="cascade", index=True
    )
    step_id = fields.Many2one("onehr.approval.step", ondelete="restrict", index=True)
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)

    event_type = fields.Selection(
        [
            ("reminder", "Reminder"),
            ("overdue", "Overdue"),
            ("escalation", "Escalation"),
            ("reassign", "Manual Reassign"),
        ],
        required=True,
        index=True,
    )
    event_at = fields.Datetime(
        required=True, default=fields.Datetime.now, index=True, readonly=True
    )
    due_at = fields.Datetime(readonly=True)
    from_user_id = fields.Many2one("res.users", ondelete="restrict", readonly=True)
    to_user_id = fields.Many2one("res.users", ondelete="restrict", readonly=True)
    reason = fields.Text(readonly=True)
    automated = fields.Boolean(default=False, readonly=True)
    payload_json = fields.Json(readonly=True)
    correlation_id = fields.Char(index=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_approval_evidence_create"):
            raise AccessError(
                _("Escalation evidence is append-only and created only by the approval engine.")
            )
        return super().create(vals_list)

    @api.model
    def _record_event(self, **values):
        """Append evidence after business authorization has already succeeded.

        The narrow sudo is evidence-only. It never authorizes or mutates the source
        business record and avoids granting ordinary users create rights on the
        immutable evidence ledger.
        """
        values = dict(values)
        values.setdefault("event_at", fields.Datetime.now())
        values.setdefault("correlation_id", str(uuid.uuid4()))
        return self.sudo().with_context(onehr_approval_evidence_create=True).create(values)

    def write(self, vals):
        raise AccessError(_("Approval escalation evidence is immutable."))

    @api.ondelete(at_uninstall=False)
    def _unlink_immutable_escalation_evidence(self):
        raise AccessError(_("Approval escalation evidence cannot be deleted."))

    def action_open_request(self):
        self.ensure_one()
        return open_record_action(
            name=self.request_id.display_name,
            res_model="onehr.approval.request",
            res_id=self.request_id.id,
        )

    def action_open_source(self):
        self.ensure_one()
        return self.request_id.action_open_source()
