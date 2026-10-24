
from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRApprovalCommon


@tagged("post_install", "-at_install", "onehr_workflow_approval")
class TestDelegationSLA(OneHRApprovalCommon):
    def _role_with_delegator(self, code):
        role = self.env["onehr.role"].with_user(self.security_manager).create(
            {"code": code, "name": code, "company_id": self.company.id}
        )
        assignment = self.env["onehr.user.role"].with_user(self.security_manager).create(
            {
                "user_id": self.approver1.id,
                "role_id": role.id,
                "company_id": self.company.id,
                "valid_from": fields.Date.today(),
            }
        )
        assignment.with_user(self.security_manager).action_activate()
        return role

    def test_12_role_delegation_requires_actual_delegator_authority(self):
        role = self.env["onehr.role"].with_user(self.security_manager).create(
            {"code": "NOAUTH", "name": "No Authority", "company_id": self.company.id}
        )
        delegation = self.env["onehr.approval.delegate"].with_user(self.approver1).create(
            {
                "delegator_user_id": self.approver1.id,
                "delegate_user_id": self.approver2.id,
                "company_id": self.company.id,
                "scope_type": "role",
                "role_id": role.id,
                "reason": "Vacation",
                "valid_from": fields.Date.today(),
            }
        )
        with self.assertRaises(UserError):
            delegation.with_user(self.approver1).action_activate()

    def test_13_delegated_decision_records_authority_chain(self):
        role = self._role_with_delegator("ROLE-DELEGATE")
        rule = self.make_rule("DELEGATED")
        self.add_step(
            rule,
            approver_policy="onehr_role",
            role_id=role.id,
            specific_user_ids=[Command.clear()],
        )
        self.activate_rule(rule)
        delegation = self.env["onehr.approval.delegate"].with_user(self.approver1).create(
            {
                "delegator_user_id": self.approver1.id,
                "delegate_user_id": self.approver2.id,
                "company_id": self.company.id,
                "scope_type": "role",
                "role_id": role.id,
                "reason": "Planned leave",
                "valid_from": fields.Date.today(),
            }
        )
        delegation.with_user(self.approver1).action_activate()
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.assertIn(self.approver2, request.current_approver_ids)
        request.with_user(self.approver2).action_approve()
        decision = request.decision_ids
        self.assertEqual(decision.approver_id, self.approver2)
        self.assertEqual(decision.authority_user_id, self.approver1)
        self.assertEqual(decision.delegated_from_user_id, self.approver1)
        self.assertEqual(decision.decision_source, "delegated")

    def test_14_manual_reassign_preserves_original_authority_identity(self):
        rule = self.make_rule("REASSIGN")
        self.add_step(rule, specific_user_ids=[Command.set(self.approver1.ids)])
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        request.with_user(self.manager).write(
            {
                "reassign_from_user_id": self.approver1.id,
                "reassign_to_user_id": self.approver2.id,
                "reassign_reason": "Documented temporary operational reassignment.",
            }
        )
        request.with_user(self.manager).action_reassign_current_authority()
        self.assertIn(self.approver2, request.current_approver_ids)
        self.assertNotIn(self.approver1, request.current_approver_ids)
        request.with_user(self.approver2).action_approve()
        decision = request.decision_ids
        self.assertEqual(decision.authority_user_id, self.approver1)
        self.assertEqual(decision.decision_source, "reassigned")
        self.assertTrue(request.escalation_log_ids.filtered(lambda row: row.event_type == "reassign"))

    def test_15_sla_cron_adds_configured_escalation_authority_once(self):
        rule = self.make_rule("SLA")
        self.add_step(
            rule,
            specific_user_ids=[Command.set(self.approver1.ids)],
            sla_hours=0,
            escalation_user_ids=[Command.set(self.approver2.ids)],
        )
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.env["onehr.approval.request"]._cron_process_sla()
        request.invalidate_recordset()
        self.assertIn(self.approver2, request.current_approver_ids)
        logs = request.escalation_log_ids.filtered(lambda row: row.event_type == "escalation")
        self.assertTrue(logs)
        count = len(logs)
        self.env["onehr.approval.request"]._cron_process_sla()
        self.assertEqual(
            len(request.escalation_log_ids.filtered(lambda row: row.event_type == "escalation")),
            count,
        )
