from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRPnPCommon


@tagged("post_install", "-at_install", "onehr_pnp")
class TestPolicyWorkflow(OneHRPnPCommon):
    def test_15_submission_creates_onehr_approval_request(self):
        policy = self.make_policy()
        policy.with_user(self.owner).action_submit_policy_approval()
        request = self.latest_request(policy)
        self.assertTrue(request)
        self.assertEqual(policy.state, "approval")
        self.assertIn(request.state, ("submitted", "pending"))

    def test_16_approval_callback_moves_policy_to_approved(self):
        policy = self.make_policy()
        request = self.approve_policy(policy)
        self.assertEqual(policy.state, "approved")
        self.assertTrue(policy.approved_at)
        self.assertEqual(len(policy.content_fingerprint), 64)
        self.assertEqual(request.final_decision, "approve")

    def test_17_definition_locked_after_submission(self):
        policy = self.make_policy()
        policy.with_user(self.owner).action_submit_policy_approval()
        with self.assertRaises(AccessError):
            policy.with_user(self.owner).write(
                {"policy_statement": "<p>Unauthorized rewrite.</p>"}
            )

    def test_18_publish_requires_workflow_approval(self):
        policy = self.make_policy()
        with self.assertRaises(UserError):
            policy.with_user(self.compliance).action_publish()

    def test_19_publish_creates_assignments_and_document_snapshot(self):
        policy = self.publish_policy()
        self.assertTrue(policy.is_current)
        self.assertEqual(policy.audience_count, 2)
        self.assertEqual(policy.pending_ack_count, 2)
        self.assertTrue(policy.archive_document_id)
        self.assertTrue(policy.archive_document_version_id)
        self.assertEqual(
            policy.archive_document_version_id.state,
            "issued",
        )

    def test_20_publish_marks_approval_executed(self):
        policy = self.make_policy()
        request = self.approve_policy(policy)
        policy.with_user(self.compliance).action_publish()
        request.invalidate_recordset()
        self.assertEqual(request.state, "executed")

    def test_21_reader_acknowledges_own_assignment(self):
        policy = self.publish_policy()
        ack = self.own_ack(policy)
        ack.with_user(self.reader).action_acknowledge()
        self.assertEqual(ack.state, "acknowledged")
        self.assertTrue(ack.acknowledged_at)

    def test_22_reader_cannot_acknowledge_another_employee(self):
        policy = self.publish_policy()
        other_ack = self.own_ack(policy, self.employee_two)
        with self.assertRaises(AccessError):
            other_ack.with_user(self.reader).action_acknowledge()

    def test_23_acknowledgement_metrics_recompute(self):
        policy = self.publish_policy()
        self.own_ack(policy).with_user(
            self.reader
        ).action_acknowledge()
        policy.invalidate_recordset()
        self.assertEqual(policy.acknowledged_count, 1)
        self.assertEqual(policy.pending_ack_count, 1)
        self.assertEqual(policy.acknowledgement_rate, 50.0)

    def test_24_not_required_ack_is_not_pending(self):
        policy = self.publish_policy(
            self.make_policy(
                acknowledgement_required=False,
                evidence_required=False,
            )
        )
        self.assertEqual(policy.pending_ack_count, 0)
        self.assertEqual(policy.acknowledgement_rate, 100.0)
        self.assertTrue(
            all(
                ack.state == "not_required"
                for ack in policy.ack_ids
            )
        )

    def test_25_employee_can_submit_note_evidence(self):
        policy = self.publish_policy()
        evidence = self.create_note_evidence(policy)
        evidence.with_user(self.reader).action_submit()
        self.assertEqual(evidence.state, "submitted")
        self.assertTrue(evidence.submitted_at)

    def test_26_compliance_can_verify_submitted_evidence(self):
        policy = self.publish_policy()
        evidence = self.create_note_evidence(policy)
        evidence.with_user(self.reader).action_submit()
        evidence.with_user(self.compliance).action_verify()
        self.assertEqual(evidence.state, "verified")
        self.assertTrue(evidence.verified_at)

    def test_27_evidence_coverage_recomputes(self):
        policy = self.publish_policy()
        evidence = self.create_note_evidence(policy)
        evidence.with_user(self.reader).action_submit()
        evidence.with_user(self.compliance).action_verify()
        policy.invalidate_recordset()
        self.assertEqual(policy.verified_evidence_count, 1)
        self.assertEqual(policy.evidence_covered_employee_count, 1)
        self.assertEqual(policy.evidence_coverage_rate, 50.0)

    def test_28_submitted_evidence_content_locked(self):
        policy = self.publish_policy()
        evidence = self.create_note_evidence(policy)
        evidence.with_user(self.reader).action_submit()
        with self.assertRaises(AccessError):
            evidence.with_user(self.reader).write(
                {"evidence_note": "Changed after submission"}
            )

    def test_29_review_can_be_completed_without_content_change(self):
        policy = self.publish_policy()
        original_due = policy.review_due_date
        policy.with_user(self.compliance).action_start_review()
        self.assertEqual(policy.state, "review")
        policy.with_user(
            self.compliance
        ).action_complete_review_no_change()
        self.assertEqual(policy.state, "published")
        self.assertGreater(policy.review_due_date, original_due)

    def test_30_controlled_revision_increments_version(self):
        policy = self.publish_policy()
        action = policy.with_user(self.compliance).action_create_revision()
        revision = self.env["onehr.policy"].browse(
            action["res_id"]
        )
        self.assertEqual(revision.policy_code, policy.policy_code)
        self.assertEqual(revision.version_no, policy.version_no + 1)
        self.assertEqual(revision.previous_policy_id, policy)
        self.assertEqual(revision.state, "draft")

    def test_31_successor_publish_archives_previous_current(self):
        policy = self.publish_policy()
        action = policy.with_user(self.compliance).action_create_revision()
        revision = self.env["onehr.policy"].browse(action["res_id"])
        revision.with_user(self.owner).write(
            {"change_summary": "Controlled policy revision."}
        )
        self.approve_policy(revision)
        revision.with_user(self.compliance).action_publish()

        policy.invalidate_recordset()
        revision.invalidate_recordset()
        self.assertEqual(policy.state, "archived")
        self.assertFalse(policy.is_current)
        self.assertEqual(revision.state, "published")
        self.assertTrue(revision.is_current)

    def test_32_successor_reuses_document_archive_header(self):
        policy = self.publish_policy()
        archive = policy.archive_document_id
        action = policy.with_user(self.compliance).action_create_revision()
        revision = self.env["onehr.policy"].browse(action["res_id"])
        revision.with_user(self.owner).write(
            {"change_summary": "Second controlled version."}
        )
        self.approve_policy(revision)
        revision.with_user(self.compliance).action_publish()
        self.assertEqual(revision.archive_document_id, archive)
        self.assertEqual(
            revision.archive_document_version_id.document_id,
            archive,
        )
