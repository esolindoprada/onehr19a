import hashlib
import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import display_notification, require_api_admin


class OneHRApiQueue(models.Model):
    _name = "onehr.api.queue"
    _description = "OneHR API/Webhook Retry Queue"
    _inherit = ["onehr.mixin.audit"]
    _order = "retry_at, id"

    _webhook_dedupe_unique = models.Constraint(
        "UNIQUE(webhook_id, dedupe_key)",
        "This webhook delivery has already been queued.",
    )

    name = fields.Char(required=True, readonly=True, copy=False, default=lambda self: _("New"), index=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True, tracking=True)
    webhook_id = fields.Many2one("onehr.webhook", required=True, ondelete="restrict", index=True, tracking=True)
    event_code = fields.Char(required=True, readonly=True, index=True)
    dedupe_key = fields.Char(required=True, readonly=True, index=True)
    request_id = fields.Char(required=True, readonly=True, index=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("retry", "Retry Scheduled"),
            ("sent", "Sent"),
            ("dead_letter", "Dead Letter"),
            ("cancelled", "Cancelled"),
        ],
        default="pending", required=True, readonly=True, tracking=True, index=True,
    )
    payload_json = fields.Text(required=True, readonly=True, groups="onehr_integrations_api.group_onehr_api_admin")
    payload_hash = fields.Char(required=True, readonly=True, index=True)
    attempts = fields.Integer(default=0, readonly=True, tracking=True)
    max_attempts = fields.Integer(required=True, readonly=True)
    retry_at = fields.Datetime(default=fields.Datetime.now, readonly=True, index=True, tracking=True)
    last_attempt_at = fields.Datetime(readonly=True, index=True)
    sent_at = fields.Datetime(readonly=True, index=True)
    last_http_status = fields.Integer(readonly=True, tracking=True)
    last_error_class = fields.Char(readonly=True, tracking=True)
    last_error_message = fields.Text(readonly=True)
    response_hash = fields.Char(readonly=True)
    log_ids = fields.One2many("onehr.api.log", "queue_id", string="Delivery Logs", readonly=True)
    log_count = fields.Integer(compute="_compute_log_count")

    @api.depends("log_ids")
    def _compute_log_count(self):
        for queue in self:
            queue.log_count = len(queue.log_ids)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_api_queue_controlled"):
            raise AccessError(_("Queue items are created by webhook transport only."))
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("onehr.api.queue") or _("New")
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("onehr_api_queue_controlled"):
            raise AccessError(_("Queue lifecycle/evidence must change through governed actions."))
        return super().write(vals)

    @api.model
    def create_from_webhook(self, webhook, payload, dedupe_key):
        webhook.ensure_one()
        if webhook.direction != "outbound":
            raise ValidationError(_("Only outbound webhooks can create delivery queue items."))
        payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        request_id = hashlib.sha256(f"{webhook.id}:{dedupe_key}".encode("utf-8")).hexdigest()[:32]
        return self.with_context(onehr_api_queue_controlled=True).create({
            "company_id": webhook.company_id.id,
            "webhook_id": webhook.id,
            "event_code": webhook.event_code,
            "dedupe_key": dedupe_key,
            "request_id": request_id,
            "payload_json": payload_text,
            "payload_hash": digest,
            "max_attempts": webhook.max_attempts,
            "retry_at": fields.Datetime.now(),
        })

    def _write_controlled(self, values):
        return self.with_context(onehr_api_queue_controlled=True).write(values)

    def action_process_now(self):
        require_api_admin(self)
        from ..services.webhook_delivery import WebhookDeliveryService

        for queue in self:
            WebhookDeliveryService(queue.env).deliver(queue)
        return display_notification(_("Selected queue item(s) processed."))

    def action_retry(self):
        require_api_admin(self)
        for queue in self:
            if queue.state not in ("dead_letter", "retry"):
                raise UserError(_("Only Retry Scheduled or Dead Letter items can be manually retried."))
            queue._write_controlled({"state": "pending", "retry_at": fields.Datetime.now(), "last_error_class": False, "last_error_message": False})
        return display_notification(_("Queue item returned to Pending."))

    def action_mark_dead_letter(self):
        require_api_admin(self)
        for queue in self.filtered(lambda rec: rec.state not in ("sent", "cancelled")):
            queue._write_controlled({"state": "dead_letter", "retry_at": False})
        return display_notification(_("Queue item marked Dead Letter."), notification_type="warning")

    def action_cancel(self):
        require_api_admin(self)
        for queue in self.filtered(lambda rec: rec.state not in ("sent", "cancelled")):
            queue._write_controlled({"state": "cancelled", "retry_at": False})
        return display_notification(_("Queue item cancelled."), notification_type="warning")

    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": self.display_name,
            "res_model": "onehr.api.queue", "view_mode": "form", "res_id": self.id,
        }

    def action_open_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Delivery Logs"),
            "res_model": "onehr.api.log", "view_mode": "list,form",
            "domain": [("queue_id", "=", self.id)],
        }

    @api.model
    def _cron_process_retry_queue(self):
        from ..services.webhook_delivery import WebhookDeliveryService

        now = fields.Datetime.now()
        queues = self.sudo().search([
            ("state", "in", ("pending", "retry")),
            ("retry_at", "!=", False),
            ("retry_at", "<=", now),
        ], order="retry_at, id", limit=200)
        service = WebhookDeliveryService(self.env)
        for queue in queues:
            service.deliver(queue)
        return True

    def next_retry_time(self):
        self.ensure_one()
        delay_minutes = min(60, 2 ** max(self.attempts, 0))
        return fields.Datetime.now() + timedelta(minutes=delay_minutes)

    @api.ondelete(at_uninstall=False)
    def _unlink_block_evidence(self):
        raise UserError(_("Integration delivery queue evidence is retained; cancel or dead-letter it instead of deleting."))
