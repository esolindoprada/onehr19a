import base64
import hashlib
import hmac
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import display_notification, require_api_admin

PBKDF2_ITERATIONS = 260_000


class OneHRApiKey(models.Model):
    _name = "onehr.api.key"
    _description = "OneHR API Key"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, name, id"

    _public_id_unique = models.Constraint(
        "UNIQUE(public_id)",
        "API Key Public ID must be unique.",
    )

    name = fields.Char(required=True, tracking=True, index=True)
    client_reference = fields.Char(index=True, tracking=True)
    public_id = fields.Char(required=True, readonly=True, copy=False, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    service_user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        domain="[('share', '=', False), ('active', '=', True)]",
        help="Least-privilege internal user under whose normal ACLs and record rules business adapters execute.",
    )
    scope_ids = fields.Many2many(
        "onehr.api.scope",
        "onehr_api_key_scope_rel",
        "api_key_id",
        "scope_id",
        string="Scopes",
        tracking=True,
        domain="[('active', '=', True)]",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    expires_at = fields.Datetime(index=True, tracking=True)
    rate_limit_per_minute = fields.Integer(
        default=60,
        required=True,
        tracking=True,
        help="0 uses the global default. A positive value overrides it for this key.",
    )
    hmac_required = fields.Boolean(
        default=True,
        tracking=True,
        help="Require X-Signature, X-Timestamp and X-Request-ID in addition to the API key.",
    )
    branch_code = fields.Char(
        index=True,
        tracking=True,
        help="Optional downstream branch boundary. An endpoint rejects branch-scoped use if its domain owner has no verifiable branch field.",
    )

    secret_hash = fields.Char(readonly=True, copy=False, groups="onehr_integrations_api.group_onehr_api_admin")
    secret_salt = fields.Char(readonly=True, copy=False, groups="onehr_integrations_api.group_onehr_api_admin")
    secret_hint = fields.Char(readonly=True, copy=False)
    generated_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    rotated_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    last_used_at = fields.Datetime(readonly=True, copy=False, index=True)
    last_used_ip = fields.Char(readonly=True, copy=False)

    log_ids = fields.One2many("onehr.api.log", "api_key_id", string="API Logs", readonly=True)
    log_count = fields.Integer(compute="_compute_log_metrics")
    error_count = fields.Integer(compute="_compute_log_metrics")
    success_count = fields.Integer(compute="_compute_log_metrics")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values.setdefault("public_id", secrets.token_hex(8))
        return super().create(vals_list)

    def write(self, vals):
        if "public_id" in vals:
            raise AccessError(_("API Key Public ID is immutable."))
        protected = {"secret_hash", "secret_salt", "secret_hint", "generated_at", "rotated_at", "last_used_at", "last_used_ip", "state"}
        if protected.intersection(vals) and not self.env.context.get("onehr_api_key_controlled"):
            raise AccessError(_("API key credential/lifecycle fields must change through governed actions."))
        active_identity_fields = {"company_id", "service_user_id", "scope_ids", "branch_code", "hmac_required"}
        for key in self:
            if key.state == "active" and active_identity_fields.intersection(vals):
                raise AccessError(_("Suspend the API key before changing company, service identity, scopes, branch or HMAC policy."))
            if key.state == "revoked" and set(vals) - {"active"}:
                raise AccessError(_("A revoked API key is immutable."))
        return super().write(vals)

    @api.depends("log_ids.outcome")
    def _compute_log_metrics(self):
        Log = self.env["onehr.api.log"]
        for key in self:
            key.log_count = Log.search_count([("api_key_id", "=", key.id)])
            key.success_count = Log.search_count([("api_key_id", "=", key.id), ("outcome", "=", "success")])
            key.error_count = key.log_count - key.success_count

    @api.constrains("service_user_id", "company_id")
    def _check_service_identity_company(self):
        for key in self:
            if key.service_user_id and key.company_id not in key.service_user_id.company_ids:
                raise ValidationError(_("The service user must be allowed to operate in the API key company."))
            if key.service_user_id and key.service_user_id.share:
                raise ValidationError(_("The API service identity must be an internal user, not a portal/shared user."))

    @api.constrains("rate_limit_per_minute")
    def _check_rate_limit(self):
        for key in self:
            if key.rate_limit_per_minute < 0 or key.rate_limit_per_minute > 100_000:
                raise ValidationError(_("Rate Limit per Minute must be between 0 and 100000."))

    @staticmethod
    def _derive_secret_hash(secret, salt):
        digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return base64.urlsafe_b64encode(digest).decode("ascii")

    @staticmethod
    def _format_raw_key(public_id, secret):
        return f"onehr_{public_id}.{secret}"

    @staticmethod
    def split_presented_key(presented_key):
        token = (presented_key or "").strip()
        if not token.startswith("onehr_") or "." not in token:
            return False, False
        public_part, secret = token[6:].split(".", 1)
        if not public_part or not secret:
            return False, False
        return public_part, secret

    def _set_new_secret(self, *, rotated=False):
        require_api_admin(self)
        self.ensure_one()
        if self.state == "revoked":
            raise UserError(_("A revoked key cannot be rotated. Create a replacement key."))
        secret = secrets.token_urlsafe(32)
        salt = secrets.token_bytes(24)
        now = fields.Datetime.now()
        values = {
            "secret_hash": self._derive_secret_hash(secret, salt),
            "secret_salt": base64.urlsafe_b64encode(salt).decode("ascii"),
            "secret_hint": secret[-6:],
            "generated_at": self.generated_at or now,
            "rotated_at": now if rotated else False,
        }
        self.with_context(onehr_api_key_controlled=True).write(values)
        raw_key = self._format_raw_key(self.public_id, secret)
        return display_notification(
            _("Copy this credential now. It will not be stored or shown again:\n%s") % raw_key,
            notification_type="warning",
            sticky=True,
        )

    def action_generate_secret(self):
        self.ensure_one()
        if self.secret_hash:
            raise UserError(_("This key already has a credential. Use Rotate Secret instead."))
        return self._set_new_secret(rotated=False)

    def action_rotate_secret(self):
        self.ensure_one()
        return self._set_new_secret(rotated=True)

    def action_activate(self):
        require_api_admin(self)
        for key in self:
            if not key.secret_hash:
                raise UserError(_("Generate the API credential before activation."))
            if not key.scope_ids:
                raise UserError(_("Assign at least one active API scope before activation."))
            if not key.service_user_id.active:
                raise UserError(_("The service user must be active."))
            key.with_context(onehr_api_key_controlled=True).write({"state": "active", "active": True})
        return display_notification(_("API key activated."))

    def action_suspend(self):
        require_api_admin(self)
        self.filtered(lambda key: key.state == "active").with_context(onehr_api_key_controlled=True).write({"state": "suspended"})
        return display_notification(_("API key suspended."), notification_type="warning")

    def action_revoke(self):
        require_api_admin(self)
        self.with_context(onehr_api_key_controlled=True).write({"state": "revoked", "active": False})
        return display_notification(_("API key permanently revoked."), notification_type="warning")

    def action_open_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("API Logs"),
            "res_model": "onehr.api.log",
            "view_mode": "list,form,pivot,graph",
            "domain": [("api_key_id", "=", self.id)],
        }

    @api.model
    def authenticate_presented_key(self, presented_key):
        """Technical credential lookup only; business-domain execution never uses sudo."""
        public_id, secret = self.split_presented_key(presented_key)
        if not public_id:
            return self.browse(), False

        # Public HTTP requests have no custom-model ACL before identity is known.
        # Elevation is deliberately limited to credential metadata lookup.
        key = self.sudo().search([("public_id", "=", public_id), ("active", "=", True)], limit=1)
        if not key or key.state != "active" or not key.secret_hash or not key.secret_salt:
            return self.browse(), False
        if key.expires_at and key.expires_at <= fields.Datetime.now():
            return self.browse(), False
        if not key.service_user_id.active or key.service_user_id.share:
            return self.browse(), False
        try:
            salt = base64.urlsafe_b64decode(key.secret_salt.encode("ascii"))
        except Exception:
            return self.browse(), False
        computed = self._derive_secret_hash(secret, salt)
        if not hmac.compare_digest(computed, key.secret_hash):
            return self.browse(), False
        return key, secret

    def technical_mark_used(self, remote_ip=None):
        """Credential metadata only; called after authentication from public transport."""
        self.sudo().with_context(onehr_api_key_controlled=True).write({
            "last_used_at": fields.Datetime.now(),
            "last_used_ip": (remote_ip or "")[:128],
        })

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unused_draft(self):
        for key in self:
            if key.state != "draft" or key.log_ids:
                raise UserError(_("Only unused Draft API keys can be deleted. Revoke used credentials instead."))
