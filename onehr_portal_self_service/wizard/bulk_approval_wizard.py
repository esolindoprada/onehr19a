
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from ..models.authority_helpers import is_portal_hr


class OneHRPortalBulkApprovalWizard(models.TransientModel):
    _name = "onehr.portal.bulk.approval.wizard"
    _description = "OneHR Portal Bulk Approval Wizard"

    decision = fields.Selection(
        [("approve", "Approve"), ("reject", "Reject")],
        required=True,
        default="approve",
    )
    note = fields.Text()
    request_count = fields.Integer(readonly=True)

    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        values["request_count"] = len(active_ids)
        return values

    def action_confirm(self):
        self.ensure_one()
        if self.decision == "reject" and not (self.note or "").strip():
            raise ValidationError(_("A rejection note is required for bulk rejection."))

        requests = self.env["onehr.portal.request"].browse(
            self.env.context.get("active_ids", [])
        ).exists()
        if not requests:
            raise UserError(_("Select at least one Portal Request."))

        processed = 0
        for request in requests:
            if request.state == "manager_review":
                if self.decision == "approve":
                    request.action_manager_approve(self.note)
                else:
                    request.action_manager_reject(self.note)
                processed += 1
            elif request.state in ("hr_review", "submitted") and is_portal_hr(self.env):
                if self.decision == "approve":
                    request.action_hr_approve(self.note)
                else:
                    request.action_hr_reject(self.note)
                processed += 1

        if not processed:
            raise UserError(_("None of the selected requests is currently actionable by your role."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OneHR Portal Self-Service"),
                "message": _("Processed %s request(s).") % processed,
                "type": "success",
                "sticky": False,
            },
        }

