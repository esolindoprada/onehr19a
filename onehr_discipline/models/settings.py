
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    onehr_discipline_default_investigation_sla_days = fields.Integer(
        string="Default Investigation SLA (Days)",
        default=7,
        config_parameter="onehr_discipline.default_investigation_sla_days",
    )
    onehr_discipline_default_hearing_sla_days = fields.Integer(
        string="Default Hearing SLA (Days)",
        default=5,
        config_parameter="onehr_discipline.default_hearing_sla_days",
    )
    onehr_discipline_default_decision_sla_days = fields.Integer(
        string="Default Decision SLA (Days)",
        default=5,
        config_parameter="onehr_discipline.default_decision_sla_days",
    )
    onehr_discipline_default_appeal_sla_days = fields.Integer(
        string="Default Appeal SLA (Days)",
        default=7,
        config_parameter="onehr_discipline.default_appeal_sla_days",
    )
    onehr_discipline_default_retention_years = fields.Integer(
        string="Default Case Retention (Years)",
        default=7,
        config_parameter="onehr_discipline.default_retention_years",
    )
    onehr_discipline_weight_minor = fields.Integer(
        string="Minor Violation Weight",
        default=20,
        config_parameter="onehr_discipline.weight_minor",
    )
    onehr_discipline_weight_moderate = fields.Integer(
        string="Moderate Violation Weight",
        default=45,
        config_parameter="onehr_discipline.weight_moderate",
    )
    onehr_discipline_weight_serious = fields.Integer(
        string="Serious Violation Weight",
        default=70,
        config_parameter="onehr_discipline.weight_serious",
    )
    onehr_discipline_weight_critical = fields.Integer(
        string="Critical Violation Weight",
        default=100,
        config_parameter="onehr_discipline.weight_critical",
    )

