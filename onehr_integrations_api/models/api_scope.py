from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .authority_helpers import display_notification, require_api_admin


class OneHRApiScope(models.Model):
    _name = "onehr.api.scope"
    _description = "OneHR API Scope"
    _inherit = ["onehr.mixin.audit"]
    _order = "code, id"

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "API Scope Code must be unique.",
    )

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True, copy=False)
    description = fields.Text()
    active = fields.Boolean(default=True, tracking=True)
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
        tracking=True,
        index=True,
    )
    http_method = fields.Selection(
        [("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("PATCH", "PATCH"), ("DELETE", "DELETE")],
        tracking=True,
    )
    route_pattern = fields.Char(
        tracking=True,
        help="Human-readable route ownership, for example /onehr/api/v1/attendance.",
    )
    company_scoped = fields.Boolean(
        default=True,
        tracking=True,
        help="When enabled, the service identity is always constrained to the API key company.",
    )
    api_key_ids = fields.Many2many(
        "onehr.api.key",
        "onehr_api_key_scope_rel",
        "scope_id",
        "api_key_id",
        string="API Keys",
        readonly=True,
    )
    api_key_count = fields.Integer(compute="_compute_api_key_count")

    def write(self, vals):
        immutable_contract = {"code", "http_method", "route_pattern"}
        if immutable_contract.intersection(vals):
            raise ValidationError(
                _("Scope Code, HTTP Method and Route Pattern are immutable after creation. Create a replacement scope for a contract change.")
            )
        return super().write(vals)

    @api.depends("api_key_ids")
    def _compute_api_key_count(self):
        for scope in self:
            scope.api_key_count = len(scope.api_key_ids)

    @api.constrains("code")
    def _check_code_format(self):
        for scope in self:
            code = (scope.code or "").strip()
            if not code or code != code.lower() or " " in code or "." not in code:
                raise ValidationError(
                    _("Scope Code must be lowercase, contain a domain separator '.', and contain no spaces.")
                )

    def action_open_api_keys(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("API Keys using %s") % self.code,
            "res_model": "onehr.api.key",
            "view_mode": "list,form",
            "domain": [("scope_ids", "in", self.id)],
        }

    def action_deactivate(self):
        require_api_admin(self)
        self.write({"active": False})
        return display_notification(_("API scope deactivated. Existing keys keep the relation but cannot authorize it."), notification_type="warning")

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unused_scope(self):
        for scope in self:
            if scope.api_key_ids:
                raise ValidationError(_("A scope assigned to API keys cannot be deleted; deactivate it instead."))
