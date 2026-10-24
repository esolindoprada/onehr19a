
from odoo import _, fields, models

from .action_helpers import open_records_action


class OneHRApprovableMixin(models.AbstractModel):
    """Registry-approved source-side integration contract.

    The source addon remains owner of business state and actual execution. This
    mixin creates/references approval requests and exposes narrow overridable hooks.
    """

    _name = "onehr.mixin.approvable"
    _description = "OneHR Approvable Source Contract"

    onehr_approval_request_count = fields.Integer(
        string="Approval Requests", compute="_compute_onehr_approval_summary"
    )
    onehr_latest_approval_state = fields.Selection(
        [
            ("none", "No Approval"),
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("executed", "Executed"),
        ],
        compute="_compute_onehr_approval_summary",
        string="Latest Approval",
    )

    def _compute_onehr_approval_summary(self):
        Request = self.env["onehr.approval.request"]
        for record in self:
            domain = [("source_model", "=", record._name), ("source_res_id", "=", record.id)]
            record.onehr_approval_request_count = Request.search_count(domain)
            latest = Request.search(domain, order="requested_at desc, id desc", limit=1)
            record.onehr_latest_approval_state = latest.state if latest else "none"

    def _approval_payload(self):
        """Return the minimum-necessary non-executable source snapshot."""
        self.ensure_one()
        return {"display_name": self.display_name}

    def _approval_branch_scope_key(self):
        """Future branch addon may override without creating reverse dependency."""
        self.ensure_one()
        return False

    def _approval_rule_context(self):
        """Return structured routing inputs; each source addon extends as needed."""
        self.ensure_one()
        company = getattr(self, "company_id", False) or self.env.company
        return {
            "company_id": company.id,
            "branch_scope_key": self._approval_branch_scope_key(),
            "document_type": self._name,
            "amount": 0.0,
            "currency_id": company.currency_id.id,
            "risk_level": "normal",
            "manager_user_ids": [],
            "approver_user_ids_by_key": {},
            "extra": {},
        }

    def _on_approval_finalized(self, decision, request):
        """Source-domain hook. Override in owner addon; no default state mutation."""
        self.ensure_one()
        return True

    def _approval_cancel_guard(self, request):
        """Source-domain hook may veto request cancellation."""
        self.ensure_one()
        return True

    def action_submit_for_approval(self):
        self.ensure_one()
        self.check_access("write")
        company = getattr(self, "company_id", False) or self.env.company
        request = self.env["onehr.approval.request"].create(
            {
                "company_id": company.id,
                "source_model": self._name,
                "source_res_id": self.id,
                "source_display_name": self.display_name,
                "source_payload_json": self._approval_payload(),
                "context_json": self._approval_rule_context(),
            }
        )
        request.action_submit()
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "onehr.approval.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_approval_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Approval Requests — %s", self.display_name),
            res_model="onehr.approval.request",
            domain=[("source_model", "=", self._name), ("source_res_id", "=", self.id)],
        )

    def onehr_mark_approval_executed(self, request):
        """Call only after the source owner successfully performs approved work."""
        self.ensure_one()
        request.ensure_one()
        return request._mark_executed_from_source(self)
