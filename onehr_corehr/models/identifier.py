import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_record_action, require_identifier_steward
from .sensitive_access import log_sensitive_change, log_sensitive_read


class OneHREmployeeIdentifier(models.Model):
    """Effective-dated identifier portfolio.

    Odoo's native singleton identification/passport/work-permit fields remain
    canonical for those native facts. This model handles enterprise identifiers
    that need multiple records, validity, masking and historical trace.
    """

    _name = "onehr.employee.identifier"
    _description = "OneHR Employee Identifier"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "employee_id, identifier_type, valid_from desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _("New"))
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    identifier_type = fields.Selection(
        [
            ("employment", "Employment / Worker ID"),
            ("tax", "Tax Identifier"),
            ("social_security", "Social Security Identifier"),
            ("national", "National Identifier"),
            ("professional", "Professional Identifier"),
            ("other", "Other Identifier"),
        ],
        required=True,
        index=True,
        tracking=True,
    )
    issuer = fields.Char(tracking=True)
    country_id = fields.Many2one("res.country", ondelete="restrict")
    identifier_value = fields.Char(
        required=True,
        groups="onehr_corehr.group_onehr_identifier_steward",
        help="Restricted raw identifier value. Routine lists use the masked value.",
    )
    masked_value = fields.Char(compute="_compute_masked_value", string="Masked Identifier")
    value_fingerprint = fields.Char(compute="_compute_value_fingerprint", store=True, copy=False, index=True)
    verified = fields.Boolean(tracking=True)
    verified_at = fields.Datetime(readonly=True)
    verified_by_id = fields.Many2one("res.users", readonly=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(groups="onehr_corehr.group_onehr_identifier_steward")

    _identifier_unique = models.Constraint(
        "unique(company_id, identifier_type, value_fingerprint)",
        "This identifier value already exists for the same identifier type and company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("reference") in (False, _("New"), "New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("onehr.employee.identifier") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        for record in records:
            log_sensitive_change(
                record,
                action="create",
                summary=_("Restricted employee identifier created"),
                metadata={"identifier_type": record.identifier_type, "raw_value_logged": False},
            )
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"identifier_value", "identifier_type", "valid_from", "valid_to", "verified", "active"} & set(vals):
            for record in self:
                log_sensitive_change(
                    record,
                    action="update",
                    summary=_("Restricted employee identifier updated"),
                    metadata={"changed_fields": sorted(set(vals)), "raw_value_logged": False},
                )
        return result

    def read(self, fields=None, load="_classic_read"):
        result = super().read(fields=fields, load=load)
        log_sensitive_read(
            self,
            fields,
            {"identifier_value", "notes"},
            _("Employee Identifier"),
        )
        return result

    @api.depends("identifier_value", "company_id")
    def _compute_masked_value(self):
        for record in self:
            raw = record.identifier_value or ""
            visible = record._mask_visible_chars()
            if not raw:
                record.masked_value = False
            elif len(raw) <= visible:
                record.masked_value = "*" * len(raw)
            else:
                record.masked_value = ("*" * (len(raw) - visible)) + raw[-visible:]

    @api.depends("identifier_value")
    def _compute_value_fingerprint(self):
        for record in self:
            normalized = (record.identifier_value or "").strip().upper()
            record.value_fingerprint = (
                hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                if normalized else False
            )

    def _mask_visible_chars(self):
        self.ensure_one()
        key = f"onehr_corehr.{self.company_id.id}.identifier_mask_visible_chars"
        raw = self.env["ir.config_parameter"].sudo().get_param(key, "4")
        try:
            return max(0, min(8, int(raw)))
        except (TypeError, ValueError):
            return 4

    def action_verify(self):
        require_identifier_steward(self.env)
        self.write(
            {
                "verified": True,
                "verified_at": fields.Datetime.now(),
                "verified_by_id": self.env.user.id,
            }
        )
        return True

    def action_expire(self):
        require_identifier_steward(self.env)
        self.write({"valid_to": fields.Date.context_today(self), "active": False})
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_identifier_steward(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Identifier history cannot be deleted. End-date/archive it instead."))
