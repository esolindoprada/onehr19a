import secrets
from urllib.parse import urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import display_notification, require_api_admin

INBOUND_EVENT_CODES = {
    "attendance.interval",
    "document.esign.status",
    "learning.result",
    "appraisal.rating",
    "career.assessment",
    "payroll.result",
}


class OneHRWebhook(models.Model):
    _name = "onehr.webhook"
    _description = "OneHR Integration Webhook"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, direction, event_code, name, id"

    _endpoint_key_unique = models.Constraint(
        "UNIQUE(endpoint_key)",
        "Inbound Webhook Endpoint Key must be unique.",
    )

    name = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="restrict", index=True, tracking=True)
    direction = fields.Selection([("inbound", "Inbound"), ("outbound", "Outbound")], required=True, default="outbound", tracking=True, index=True)
    event_code = fields.Char(required=True, tracking=True, index=True, help="Stable event contract, for example attendance.interval or employee.changed.")
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("disabled", "Disabled")],
        default="draft", required=True, tracking=True, index=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    target_url = fields.Char(tracking=True)
    endpoint_key = fields.Char(readonly=True, copy=False, index=True)
    service_user_id = fields.Many2one(
        "res.users", ondelete="restrict", tracking=True, index=True,
        domain="[('share', '=', False), ('active', '=', True)]",
        help="Required for inbound business execution. Normal ACLs/rules of this user remain authoritative.",
    )
    secret = fields.Char(
        copy=False,
        groups="onehr_integrations_api.group_onehr_api_admin",
        help="Restricted signing secret. Unlike API-key secrets, outbound webhook signing requires reversible server-side storage.",
    )
    secret_hint = fields.Char(readonly=True, copy=False)
    hmac_required = fields.Boolean(default=True, tracking=True)
    branch_code = fields.Char(index=True, tracking=True)
    rate_limit_per_minute = fields.Integer(default=120, required=True, tracking=True)
    max_attempts = fields.Integer(default=5, required=True, tracking=True)
    timeout_seconds = fields.Integer(default=10, required=True, tracking=True)
    last_success_at = fields.Datetime(readonly=True, copy=False, index=True)
    last_failure_at = fields.Datetime(readonly=True, copy=False, index=True)
    last_http_status = fields.Integer(readonly=True, copy=False)
    last_message = fields.Char(readonly=True, copy=False)

    queue_ids = fields.One2many("onehr.api.queue", "webhook_id", string="Delivery Queue", readonly=True)
    log_ids = fields.One2many("onehr.api.log", "webhook_id", string="Logs", readonly=True)
    queue_count = fields.Integer(compute="_compute_metrics")
    pending_count = fields.Integer(compute="_compute_metrics")
    failed_count = fields.Integer(
        compute="_compute_metrics",
        store=True,
        help="Stored Dead Letter delivery count so Odoo search views can filter webhooks safely.",
    )
    log_count = fields.Integer(compute="_compute_metrics")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("direction", "outbound") == "inbound":
                vals.setdefault("endpoint_key", secrets.token_urlsafe(18).replace("-", "").replace("_", "")[:24])
        return super().create(vals_list)

    def write(self, vals):
        if "endpoint_key" in vals:
            raise AccessError(_("Inbound Endpoint Key is immutable."))
        protected = {"state", "secret", "secret_hint", "last_success_at", "last_failure_at", "last_http_status", "last_message"}
        if protected.intersection(vals) and not self.env.context.get("onehr_webhook_controlled"):
            raise AccessError(_("Webhook lifecycle/credential/technical status must change through governed actions."))
        active_routing_fields = {"company_id", "direction", "event_code", "target_url", "service_user_id", "hmac_required", "branch_code"}
        for webhook in self:
            if webhook.state == "active" and active_routing_fields.intersection(vals):
                raise AccessError(_("Pause the webhook before changing its routing or service identity."))
            if webhook.state == "disabled" and set(vals) - {"active"}:
                raise AccessError(_("A disabled webhook is immutable. Create a replacement configuration."))
        return super().write(vals)

    @api.depends("queue_ids.state", "log_ids.outcome")
    def _compute_metrics(self):
        Queue = self.env["onehr.api.queue"]
        Log = self.env["onehr.api.log"]
        for hook in self:
            hook.queue_count = Queue.search_count([("webhook_id", "=", hook.id)])
            hook.pending_count = Queue.search_count([("webhook_id", "=", hook.id), ("state", "in", ("pending", "retry"))])
            hook.failed_count = Queue.search_count([("webhook_id", "=", hook.id), ("state", "=", "dead_letter")])
            hook.log_count = Log.search_count([("webhook_id", "=", hook.id)])

    @api.constrains("direction", "target_url", "service_user_id", "event_code")
    def _check_direction_contract(self):
        for hook in self:
            if hook.direction == "outbound" and not (hook.target_url or "").strip():
                raise ValidationError(_("Outbound webhooks require a Target URL."))
            if hook.direction == "inbound":
                if not hook.service_user_id:
                    raise ValidationError(_("Inbound webhooks require a least-privilege internal Service User."))
                if hook.service_user_id.share or hook.company_id not in hook.service_user_id.company_ids:
                    raise ValidationError(_("Inbound webhook Service User must be internal and allowed in the webhook company."))
                if hook.event_code not in INBOUND_EVENT_CODES:
                    raise ValidationError(_("Unsupported inbound event code. Inbound dispatch is intentionally allow-listed."))

    @api.constrains("target_url")
    def _check_target_url_shape(self):
        for hook in self.filtered(lambda rec: rec.direction == "outbound" and rec.target_url):
            parsed = urlsplit(hook.target_url.strip())
            if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
                raise ValidationError(_("Webhook Target URL must be a normal HTTP(S) URL without embedded credentials."))

    @api.constrains("rate_limit_per_minute", "max_attempts", "timeout_seconds")
    def _check_limits(self):
        for hook in self:
            if hook.rate_limit_per_minute < 1 or hook.rate_limit_per_minute > 100_000:
                raise ValidationError(_("Webhook Rate Limit must be between 1 and 100000 per minute."))
            if hook.max_attempts < 1 or hook.max_attempts > 20:
                raise ValidationError(_("Max Attempts must be between 1 and 20."))
            if hook.timeout_seconds < 1 or hook.timeout_seconds > 120:
                raise ValidationError(_("Webhook Timeout must be between 1 and 120 seconds."))

    def action_rotate_secret(self):
        require_api_admin(self)
        self.ensure_one()
        if self.state == "disabled":
            raise UserError(_("A disabled webhook cannot be rotated."))
        secret = secrets.token_urlsafe(36)
        self.with_context(onehr_webhook_controlled=True).write({"secret": secret, "secret_hint": secret[-6:]})
        return display_notification(
            _("Webhook signing secret rotated. Copy it to the remote system now:\n%s") % secret,
            notification_type="warning", sticky=True,
        )

    def action_activate(self):
        require_api_admin(self)
        for hook in self:
            if hook.hmac_required and not hook.secret:
                raise UserError(_("Rotate/generate a webhook secret before activation."))
            hook._check_direction_contract()
            hook.with_context(onehr_webhook_controlled=True).write({"state": "active", "active": True})
        return display_notification(_("Webhook activated."))

    def action_pause(self):
        require_api_admin(self)
        self.filtered(lambda hook: hook.state == "active").with_context(onehr_webhook_controlled=True).write({"state": "paused"})
        return display_notification(_("Webhook paused."), notification_type="warning")

    def action_disable(self):
        require_api_admin(self)
        self.with_context(onehr_webhook_controlled=True).write({"state": "disabled", "active": False})
        return display_notification(_("Webhook disabled."), notification_type="warning")

    def action_test_webhook(self):
        require_api_admin(self)
        self.ensure_one()
        if self.direction != "outbound" or self.state != "active":
            raise UserError(_("Only an Active outbound webhook can queue a test delivery."))
        queue = self._queue_outbound_payload(
            {"event": "onehr.webhook.test", "webhook": self.name, "company_id": self.company_id.id},
            dedupe_key=f"manual-test-{self.id}-{fields.Datetime.now()}",
        )
        return queue.action_open_record()

    def action_open_queue(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Webhook Delivery Queue"),
            "res_model": "onehr.api.queue", "view_mode": "list,kanban,form,pivot,graph",
            "domain": [("webhook_id", "=", self.id)],
        }

    def action_open_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Webhook Logs"),
            "res_model": "onehr.api.log", "view_mode": "list,form,pivot,graph",
            "domain": [("webhook_id", "=", self.id)],
        }

    def _queue_outbound_payload(self, payload, dedupe_key):
        self.ensure_one()
        if self.direction != "outbound" or self.state != "active":
            return self.env["onehr.api.queue"]
        # Integration transport owns queue evidence. This is deliberately technical
        # elevation and never executes sibling business-domain mutations.
        Queue = self.env["onehr.api.queue"].sudo()
        existing = Queue.search([("webhook_id", "=", self.id), ("dedupe_key", "=", dedupe_key)], limit=1)
        if existing:
            return existing
        return Queue.create_from_webhook(self, payload, dedupe_key)

    @api.model
    def emit_event(self, event_code, payload, company, dedupe_key):
        """Transport-only outbound fan-out called after a successful domain operation."""
        hooks = self.sudo().search([
            ("direction", "=", "outbound"), ("state", "=", "active"),
            ("event_code", "=", event_code), ("company_id", "=", company.id),
        ])
        queues = self.env["onehr.api.queue"]
        for hook in hooks:
            queues |= hook._queue_outbound_payload(payload, f"{dedupe_key}:{hook.id}")
        return queues

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unused_draft(self):
        for hook in self:
            if hook.state != "draft" or hook.queue_ids or hook.log_ids:
                raise UserError(_("Only unused Draft webhook configurations can be deleted."))
