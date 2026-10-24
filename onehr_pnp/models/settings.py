
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    onehr_pnp_default_owner_user_id = fields.Many2one(
        "res.users",
        string="Default Policy Owner",
        config_parameter="onehr_pnp.default_owner_user_id",
        domain="[('share', '=', False)]",
    )
    onehr_pnp_default_review_months = fields.Integer(
        string="Default Policy Review Interval (Months)",
        default=12,
        config_parameter="onehr_pnp.default_review_months",
    )
    onehr_pnp_default_ack_reminder_days = fields.Integer(
        string="Default Acknowledgement Reminder (Days)",
        default=7,
        config_parameter="onehr_pnp.default_ack_reminder_days",
    )
    onehr_pnp_default_retention_years = fields.Integer(
        string="Default Policy Retention (Years)",
        default=7,
        config_parameter="onehr_pnp.default_retention_years",
    )
    onehr_pnp_default_document_category_id = fields.Many2one(
        "onehr.document.category",
        string="Default Policy Archive Category",
        config_parameter="onehr_pnp.default_document_category_id",
        domain="[('active', '=', True)]",
    )

