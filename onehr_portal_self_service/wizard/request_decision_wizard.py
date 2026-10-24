
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from ..models.authority_helpers import is_portal_hr


class OneHRPortalRequestDecisionWizard(models.TransientModel):
    _name = "onehr.portal.request.decision.wizard"
    _description = "OneHR Portal Request Decision Wizard"

    request_id = fields.Many2one(
        "onehr.portal.request",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    decision = fields.Selection(
        [("approve", "Approve"), ("reject", "Reject")],
        required=True,
        default="approve",
    )
    note = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        if self.decision == "reject" and not (self.note or "").strip():
            raise ValidationError(_("A rejection note is required."))

        request = self.request_id
        if request.state == "manager_review":
            return (
                request.action_manager_approve(self.note)
                if self.decision == "approve"
                else request.action_manager_reject(self.note)
            )
        if request.state in ("hr_review", "submitted") and is_portal_hr(self.env):
            return (
                request.action_hr_approve(self.note)
                if self.decision == "approve"
                else request.action_hr_reject(self.note)
            )
        raise UserError(_("The selected request is not waiting for a decision available to your role."))

