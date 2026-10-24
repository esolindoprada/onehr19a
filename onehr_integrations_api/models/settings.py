from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    onehr_api_enabled = fields.Boolean(
        string="Enable OneHR External API",
        default=True,
        config_parameter="onehr_integrations_api.api_enabled",
    )
    onehr_api_default_rate_limit = fields.Integer(
        string="Default Requests / Minute",
        default=60,
        config_parameter="onehr_integrations_api.default_rate_limit",
    )
    onehr_api_max_payload_kb = fields.Integer(
        string="Maximum JSON Payload (KB)",
        default=1024,
        config_parameter="onehr_integrations_api.max_payload_kb",
    )
    onehr_api_hmac_tolerance_seconds = fields.Integer(
        string="HMAC Timestamp Tolerance (seconds)",
        default=300,
        config_parameter="onehr_integrations_api.hmac_tolerance_seconds",
    )
    onehr_api_cors_origins = fields.Char(
        string="Allowed CORS Origins",
        config_parameter="onehr_integrations_api.cors_origins",
        help="Comma-separated exact origins. Use * only when explicitly accepted by your security policy.",
    )
    onehr_api_log_payloads = fields.Boolean(
        string="Store Sanitized Payload Bodies",
        default=False,
        config_parameter="onehr_integrations_api.log_payloads",
    )
    onehr_api_log_retention_days = fields.Integer(
        string="Archive Logs After (days)",
        default=180,
        config_parameter="onehr_integrations_api.log_retention_days",
    )
    onehr_webhook_default_max_attempts = fields.Integer(
        string="Default Webhook Attempts",
        default=5,
        config_parameter="onehr_integrations_api.webhook_default_max_attempts",
    )
    onehr_webhook_timeout_seconds = fields.Integer(
        string="Default Webhook Timeout (seconds)",
        default=10,
        config_parameter="onehr_integrations_api.webhook_timeout_seconds",
    )
    onehr_webhook_allow_http = fields.Boolean(
        string="Allow Plain HTTP Webhook Targets",
        default=False,
        config_parameter="onehr_integrations_api.webhook_allow_http",
    )
    onehr_webhook_allow_private_targets = fields.Boolean(
        string="Allow Private/Loopback Webhook Targets",
        default=False,
        config_parameter="onehr_integrations_api.webhook_allow_private_targets",
        help="Keep disabled for internet-facing deployments unless an approved private integration architecture requires it.",
    )
