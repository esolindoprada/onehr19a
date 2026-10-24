from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class OneHRApiLog(models.Model):
    _name = "onehr.api.log"
    _description = "OneHR API Audit Log"
    _order = "event_at desc, id desc"

    _api_request_unique = models.Constraint(
        "UNIQUE(api_key_id, request_id)",
        "The Request ID has already been used by this API key.",
    )
    _inbound_replay_unique = models.Constraint(
        "UNIQUE(inbound_replay_key)",
        "The inbound replay identity has already been processed.",
    )

    event_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True, index=True)
    company_id = fields.Many2one("res.company", ondelete="restrict", readonly=True, index=True)
    api_key_id = fields.Many2one("onehr.api.key", ondelete="restrict", readonly=True, index=True)
    webhook_id = fields.Many2one("onehr.webhook", ondelete="restrict", readonly=True, index=True)
    service_user_id = fields.Many2one("res.users", ondelete="restrict", readonly=True, index=True)
    direction = fields.Selection([("inbound", "Inbound"), ("outbound", "Outbound")], required=True, readonly=True, index=True)
    request_id = fields.Char(readonly=True, index=True)
    inbound_replay_key = fields.Char(readonly=True, index=True)
    scope_code = fields.Char(readonly=True, index=True)
    method = fields.Char(readonly=True, index=True)
    path = fields.Char(readonly=True, index=True)
    remote_ip = fields.Char(readonly=True)
    user_agent = fields.Char(readonly=True)
    http_status = fields.Integer(readonly=True, index=True)
    outcome = fields.Selection(
        [
            ("success", "Success"),
            ("auth_error", "Authentication Error"),
            ("forbidden", "Forbidden"),
            ("rate_limited", "Rate Limited"),
            ("client_error", "Client Error"),
            ("server_error", "Server Error"),
        ],
        required=True,
        readonly=True,
        index=True,
    )
    latency_ms = fields.Float(readonly=True, index=True)
    error_class = fields.Char(readonly=True, index=True)
    error_message = fields.Text(readonly=True)
    request_hash = fields.Char(readonly=True, index=True)
    response_hash = fields.Char(readonly=True)
    request_payload = fields.Text(readonly=True, groups="onehr_integrations_api.group_onehr_api_admin")
    response_payload = fields.Text(readonly=True, groups="onehr_integrations_api.group_onehr_api_admin")
    archived = fields.Boolean(default=False, readonly=True, index=True)
    queue_id = fields.Many2one("onehr.api.queue", ondelete="set null", readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_api_technical_log"):
            raise AccessError(_("API audit logs can only be created by the integration transport."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("onehr_api_technical_log"):
            raise AccessError(_("API audit evidence is immutable."))
        allowed = {"archived"}
        if set(vals) - allowed:
            raise AccessError(_("Only archival status may change on API audit evidence."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("API audit evidence cannot be deleted from the application."))

    @api.model
    def technical_create(self, values):
        """Narrow transport-only creation helper; caller must already have sanitized values."""
        return self.sudo().with_context(onehr_api_technical_log=True).create(values)

    @api.model
    def _cron_archive_old_logs(self):
        params = self.env["ir.config_parameter"].sudo()
        days = int(params.get_param("onehr_integrations_api.log_retention_days", "180") or 180)
        if days <= 0:
            return True
        cutoff = fields.Datetime.now() - timedelta(days=days)
        logs = self.sudo().search([("archived", "=", False), ("event_at", "<", cutoff)], limit=10000)
        if logs:
            logs.with_context(onehr_api_technical_log=True).write({"archived": True})
        return True
