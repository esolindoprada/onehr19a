from odoo import _, fields, models
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = "res.users"

    onehr_offboarding_access_revoked = fields.Boolean(
        string="OneHR Offboarding Access Revoked",
        readonly=True,
        copy=False,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_admin,base.group_system",
    )
    onehr_offboarding_access_revoked_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_admin,base.group_system",
    )
    onehr_offboarding_access_reference = fields.Char(
        readonly=True,
        copy=False,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_admin,base.group_system",
    )
    onehr_offboarding_access_revoked_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_admin,base.group_system",
    )

    def write(self, vals):
        evidence_fields = {
            "onehr_offboarding_access_revoked",
            "onehr_offboarding_access_revoked_at",
            "onehr_offboarding_access_reference",
            "onehr_offboarding_access_revoked_by_id",
        }
        if evidence_fields.intersection(vals) and not self.env.context.get("onehr_offboarding_access_evidence"):
            raise AccessError(_("OneHR offboarding access evidence may be changed only by the governed revocation action."))
        return super().write(vals)
