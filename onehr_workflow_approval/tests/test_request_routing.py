from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRApprovalCommon


@tagged("post_install", "-at_install", "onehr_workflow_approval")
class TestRequestRouting(OneHRApprovalCommon):
    def test_06_single_step_submit_and_approve(self):
        rule = self.make_rule("SINGLE")
        self.add_step(rule)
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.assertEqual(request.state, "pending")
        self.assertIn(self.approver1, request.current_approver_ids)
        request.with_user(self.approver1).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.final_decision, "approve")
        self.assertEqual(len(request.decision_ids), 1)

    def test_07_sequential_levels_advance_in_order(self):
        rule = self.make_rule("SEQUENTIAL", minimum_distinct_approvers=2)
        self.add_step(rule, name="Level 10", level=10, specific_user_ids=[Command.set(self.approver1.ids)])
        self.add_step(rule, name="Level 20", level=20, sequence=10, specific_user_ids=[Command.set(self.approver2.ids)])
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.assertEqual(request.current_level, 10)
        request.with_user(self.approver1).action_approve()
        self.assertEqual(request.current_level, 20)
        request.with_user(self.approver2).action_approve()
        self.assertEqual(request.state, "approved")

    def test_08_parallel_steps_complete_same_level(self):
        rule = self.make_rule("PARALLEL", minimum_distinct_approvers=2)
        self.add_step(rule, name="Finance", level=10, sequence=10, specific_user_ids=[Command.set(self.approver1.ids)])
        self.add_step(rule, name="HR", level=10, sequence=20, specific_user_ids=[Command.set(self.approver2.ids)])
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        self.assertEqual(len(request.current_step_ids), 2)
        request.with_user(self.approver1).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.approver2).action_approve()
        self.assertEqual(request.state, "approved")

    def test_09_self_approval_and_four_eyes_capacity_guard(self):
        rule = self.make_rule("SELF", minimum_distinct_approvers=2)
        self.add_step(rule, specific_user_ids=[Command.set(self.manager.ids)], block_self_approval=True)
        self.activate_rule(rule)
        request = self.create_request(requester=self.manager)
        with self.assertRaises(UserError):
            request.with_user(self.manager).action_submit()

    def test_10_rejection_is_final_and_requires_rationale(self):
        rule = self.make_rule("REJECT")
        self.add_step(rule)
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.approver1).action_reject()
        request.with_user(self.approver1).write({"decision_comment": "Policy threshold not met."})
        request.with_user(self.approver1).action_reject()
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.final_decision, "reject")

    def test_11_cancel_and_resubmit_preserve_history(self):
        rule = self.make_rule("RESUBMIT")
        self.add_step(rule)
        self.activate_rule(rule)
        request = self.create_request()
        request.with_user(self.manager).action_submit()
        request.with_user(self.manager).action_cancel()
        self.assertEqual(request.state, "cancelled")
        action = request.with_user(self.manager).action_resubmit()
        new_request = self.env["onehr.approval.request"].browse(action["res_id"])
        self.assertEqual(new_request.supersedes_request_id, request)
        self.assertEqual(new_request.state, "pending")
        self.assertEqual(request.state, "cancelled")
