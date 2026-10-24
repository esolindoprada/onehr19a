
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    onehr_identifier_mask_visible_chars = fields.Integer(
        string="Visible Identifier Characters",
        default=4,
        help="Number of trailing characters displayed by routine identifier masking.",
    )
    onehr_occ_health_enabled = fields.Boolean(
        string="Occupational Health Operationally Enabled",
        help="Governance flag only; it does not weaken model ACLs.",
    )
    onehr_medical_retention_days = fields.Integer(
        string="Medical Retention Days",
        default=0,
        help="0 means no company policy has been configured here. Apply applicable law/policy.",
    )
    onehr_profile_review_activity_days = fields.Integer(
        string="Profile Review Lead Days",
        default=0,
        help="Reserved policy pointer for profile-review automation; 0 disables lead-day policy.",
    )

    def _onehr_company_param_key(self, suffix):
        company = self.company_id or self.env.company
        return f"onehr_corehr.{company.id}.{suffix}"

    @api.model
    def get_values(self):
        values = super().get_values()
        company = self.env.company
        params = self.env["ir.config_parameter"].sudo()

        def get_int(suffix, default):
            try:
                return int(params.get_param(f"onehr_corehr.{company.id}.{suffix}", str(default)))
            except (TypeError, ValueError):
                return default

        values.update(
            onehr_identifier_mask_visible_chars=get_int("identifier_mask_visible_chars", 4),
            onehr_occ_health_enabled=params.get_param(
                f"onehr_corehr.{company.id}.occ_health_enabled", "False"
            ) == "True",
            onehr_medical_retention_days=get_int("medical_retention_days", 0),
            onehr_profile_review_activity_days=get_int("profile_review_activity_days", 0),
        )
        return values

    def set_values(self):
        super().set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(
            self._onehr_company_param_key("identifier_mask_visible_chars"),
            self.onehr_identifier_mask_visible_chars,
        )
        params.set_param(
            self._onehr_company_param_key("occ_health_enabled"),
            self.onehr_occ_health_enabled,
        )
        params.set_param(
            self._onehr_company_param_key("medical_retention_days"),
            self.onehr_medical_retention_days,
        )
        params.set_param(
            self._onehr_company_param_key("profile_review_activity_days"),
            self.onehr_profile_review_activity_days,
        )

    @api.constrains(
        "onehr_identifier_mask_visible_chars",
        "onehr_medical_retention_days",
        "onehr_profile_review_activity_days",
    )
    def _check_onehr_settings_ranges(self):
        for record in self:
            if not 0 <= record.onehr_identifier_mask_visible_chars <= 8:
                raise ValidationError(_("Visible Identifier Characters must be between 0 and 8."))
            if record.onehr_medical_retention_days < 0:
                raise ValidationError(_("Medical Retention Days cannot be negative."))
            if record.onehr_profile_review_activity_days < 0:
                raise ValidationError(_("Profile Review Lead Days cannot be negative."))
