
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRSOPCommon


@tagged("post_install", "-at_install", "onehr_sop")
class TestSOPWorkflow(OneHRSOPCommon):
    def test_13_review_requires_complete_content(self):
        sop = self.make_sop()
        version = self.env["onehr.sop.version"].with_user(
            self.editor
        ).create(
            {
                "sop_id": sop.id,
                "purpose": "<p>Incomplete.</p>",
                "target_employee_ids": [
                    Command.set([self.employee.id])
                ],
            }
        )
        with self.assertRaises(UserError):
            version.with_user(self.editor).action_submit_review()

    def test_14_review_requires_nonempty_resolved_audience(self):
        sop = self.make_sop()
        version = self.make_version(
            sop,
            target_employee_ids=[Command.set([])],
            target_department_ids=[Command.set([])],
            target_job_ids=[Command.set([])],
        )
        with self.assertRaises(UserError):
            version.with_user(self.editor).action_submit_review()

    def test_15_draft_moves_to_review(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        self.assertEqual(version.state, "review")
        self.assertTrue(version.submitted_at)

    def test_16_editor_cannot_approve(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.editor).action_approve()

    def test_17_assigned_approver_matrix_is_enforced(self):
        sop = self.make_sop(
            approver_user_ids=[Command.set([self.approver.id])]
        )
        version = self.make_version(sop)
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.second_approver).action_approve()

    def test_18_approval_captures_content_fingerprint(self):
        version = self.make_version()
        self.approve_version(version)
        self.assertEqual(version.state, "approved")
        self.assertEqual(len(version.content_fingerprint), 64)
        self.assertTrue(version.approved_at)

    def test_19_submitted_content_is_locked(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.editor).write(
                {"procedure_steps": "<p>Unauthorized rewrite.</p>"}
            )

    def test_20_approved_version_can_return_to_draft_before_publish(self):
        version = self.make_version()
        self.approve_version(version)
        version.with_user(self.approver).action_return_draft()
        self.assertEqual(version.state, "draft")
        self.assertFalse(version.content_fingerprint)

    def test_21_publish_creates_acknowledgements(self):
        version = self.publish_version(self.make_version())
        self.assertEqual(version.state, "published")
        self.assertTrue(version.is_current)
        self.assertEqual(version.ack_count, 2)
        self.assertEqual(version.pending_count, 2)

    def test_22_publish_creates_issued_document_archive(self):
        version = self.publish_version(self.make_version())
        self.assertTrue(version.sop_id.archive_document_id)
        self.assertTrue(version.archive_document_version_id)
        self.assertEqual(version.archive_document_version_id.state, "issued")
        self.assertEqual(
            version.archive_document_version_id.document_id,
            version.sop_id.archive_document_id,
        )

    def test_23_missing_archive_category_blocks_publish(self):
        sop = self.make_sop(document_category_id=False)
        version = self.make_version(sop)
        self.approve_version(version)
        with self.assertRaises(UserError):
            version.with_user(self.approver).action_publish()

    def test_24_reader_can_acknowledge_own_assignment(self):
        version = self.publish_version(self.make_version())
        ack = version.ack_ids.filtered(
            lambda item: item.employee_id == self.employee
        )
        ack.with_user(self.reader).action_acknowledge()
        self.assertEqual(ack.state, "acknowledged")
        self.assertTrue(ack.acknowledged_at)
        self.assertEqual(ack.acknowledged_by_id, self.reader)

    def test_25_reader_cannot_acknowledge_other_employee(self):
        version = self.publish_version(self.make_version())
        ack = version.ack_ids.filtered(
            lambda item: item.employee_id == self.employee_two
        )
        with self.assertRaises(AccessError):
            ack.with_user(self.reader).action_acknowledge()

    def test_26_successor_publish_obsoletes_previous_current(self):
        sop = self.make_sop()
        first = self.publish_version(self.make_version(sop))
        successor = self.env["onehr.sop.version"].with_user(
            self.editor
        ).create(
            {
                "sop_id": sop.id,
                **first._copy_content_values(),
                "change_summary": "Controlled revision of the published SOP.",
            }
        )
        self.publish_version(successor)

        self.assertEqual(first.state, "obsolete")
        self.assertFalse(first.is_current)
        self.assertEqual(successor.state, "published")
        self.assertTrue(successor.is_current)
        self.assertEqual(sop.current_version_id, successor)

    def test_27_document_archive_header_is_reused_for_successor(self):
        sop = self.make_sop()
        first = self.publish_version(self.make_version(sop))
        archive_header = sop.archive_document_id

        successor = self.env["onehr.sop.version"].with_user(
            self.editor
        ).create(
            {
                "sop_id": sop.id,
                **first._copy_content_values(),
                "change_summary": "Second controlled version.",
            }
        )
        self.publish_version(successor)

        self.assertEqual(sop.archive_document_id, archive_header)
        self.assertEqual(
            successor.archive_document_version_id.document_id,
            archive_header,
        )

    def test_28_published_version_cannot_be_deleted(self):
        version = self.publish_version(self.make_version())
        with self.assertRaises(UserError):
            version.with_user(self.admin).unlink()

