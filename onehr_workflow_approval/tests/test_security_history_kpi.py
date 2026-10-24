
from odoo import fields
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRApprovalCommon


@tagged("post_install", "-at_install", "onehr_workflow_approval")
class TestSecurityHistoryKPI(OneHRApprovalCommon):
    def _approved_request(self, code="APPROVED"):
        rule = self.make_rule(code)
        self.add_step(rule)
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        request.with_user(self.approver1).action_approve()
        return request

    def test_16_decision_is_immutable_and_correction_supersedes_evidence(self):
        request = self._approved_request("CORRECTION")
        decision = request.decision_ids
        with self.assertRaises(AccessError):
            decision.with_user(self.workflow_admin).write({"rationale": "Rewrite"})
        correction = decision.with_user(self.workflow_admin).record_correction(
            "reject",
            "Original decision evidence was entered incorrectly.",
        )
        self.assertEqual(correction.supersedes_id, decision)
        self.assertEqual(correction.decision_source, "correction")
        self.assertEqual(request.state, "approved")

    def test_17_company_record_rules_hide_other_company_requests(self):
        other_rule = self.env["onehr.approval.rule"].sudo().create(
            {
                "code": "OTHER",
                "name": "Other",
                "company_id": self.other_company.id,
                "model_id": self.partner_model.id,
                "valid_from": fields.Date.today(),
            }
        )
        self.env["onehr.approval.step"].sudo().create(
            {
                "rule_id": other_rule.id,
                "name": "Other Step",
                "approver_policy": "specific_users",
                "specific_user_ids": [Command.set(self.manager.ids)],
                "valid_from": fields.Date.today(),
            }
        )
        other_rule.sudo().action_activate()
        request = self.env["onehr.approval.request"].sudo().create(
            {
                "company_id": self.other_company.id,
                "source_model": self.other_source._name,
                "source_res_id": self.other_source.id,
                "requested_by_id": self.other_company_user.id,
                "source_payload_json": {"name": self.other_source.display_name},
                "context_json": {
                    "company_id": self.other_company.id,
                    "document_type": "res.partner",
                    "amount": 0.0,
                    "currency_id": self.other_company.currency_id.id,
                    "risk_level": "normal",
                    "extra": {},
                },
            }
        )
        request.sudo().action_submit()
        visible = self.env["onehr.approval.request"].with_user(self.requester).search([])
        self.assertNotIn(request, visible)

    def test_18_participant_visibility_requester_approver_outsider(self):
        rule = self.make_rule("VISIBILITY")
        self.add_step(rule)
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.assertIn(request, self.env["onehr.approval.request"].with_user(self.requester).search([]))
        self.assertIn(request, self.env["onehr.approval.request"].with_user(self.approver1).search([]))
        self.assertNotIn(request, self.env["onehr.approval.request"].with_user(self.outsider).search([]))

    def test_19_daily_kpi_snapshot_is_idempotent_and_read_only(self):
        request = self._approved_request("KPI")
        self.env["onehr.approval.kpi.daily"]._cron_build_daily_kpi()
        snapshots = self.env["onehr.approval.kpi.daily"].search([("rule_id", "=", request.rule_id.id)])
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots.approved_count, 1)
        self.env["onehr.approval.kpi.daily"]._cron_build_daily_kpi()
        self.assertEqual(
            self.env["onehr.approval.kpi.daily"].search_count([("rule_id", "=", request.rule_id.id)]),
            1,
        )
        with self.assertRaises(AccessError):
            snapshots.with_user(self.workflow_admin).write({"approved_count": 999})

    def test_20_source_execution_marker_never_executes_source_business_logic(self):
        request = self._approved_request("EXECUTE")
        self.assertEqual(request.state, "approved")
        request._mark_executed_from_source(self.source)
        self.assertEqual(request.state, "executed")
        self.assertTrue(request.executed_at)
        self.assertEqual(self.source.name, "Approval Source Record")
