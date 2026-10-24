
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRJobDescriptionCommon


@tagged("post_install", "-at_install", "onehr_job_description")
class TestJDVersionWorkflow(OneHRJobDescriptionCommon):
    def test_09_review_requires_minimum_completeness(self):
        jd = self.make_jd()
        version = self.env["onehr.jd.version"].with_user(self.editor).create(
            {
                "jd_id": jd.id,
                "purpose": "<p>Only one section.</p>",
            }
        )
        with self.assertRaises(UserError):
            version.with_user(self.editor).action_submit_review()

    def test_10_draft_moves_to_review(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        self.assertEqual(version.state, "review")
        self.assertTrue(version.submitted_at)

    def test_11_editor_cannot_approve(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.editor).action_approve()

    def test_12_assigned_approver_matrix_is_enforced(self):
        jd = self.make_jd(
            approver_user_ids=[Command.set([self.approver.id])]
        )
        version = self.make_version(jd)
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.second_approver).action_approve()

    def test_13_approval_captures_fingerprint(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        version.with_user(self.approver).action_approve()
        self.assertEqual(version.state, "approved")
        self.assertEqual(len(version.content_fingerprint), 64)
        self.assertTrue(version.approved_at)

    def test_14_publish_sets_current_evidence(self):
        version = self.publish_version(self.make_version())
        self.assertEqual(version.state, "published")
        self.assertTrue(version.is_current)
        self.assertTrue(version.published_at)
        self.assertEqual(version.jd_id.current_version_id, version)

    def test_15_second_publish_preserves_history_and_moves_current(self):
        jd = self.make_jd()
        first = self.publish_version(self.make_version(jd))
        second = self.make_version(
            jd,
            change_summary="Material controlled revision.",
        )
        self.publish_version(second)

        self.assertEqual(first.state, "published")
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)
        self.assertEqual(jd.current_version_id, second)
        self.assertEqual(second.version_no, 2)

    def test_16_submitted_content_is_immutable(self):
        version = self.make_version()
        version.with_user(self.editor).action_submit_review()
        with self.assertRaises(AccessError):
            version.with_user(self.editor).write(
                {"purpose": "<p>Unauthorized post-submit rewrite.</p>"}
            )

    def test_17_published_version_cannot_be_deleted(self):
        version = self.publish_version(self.make_version())
        with self.assertRaises(UserError):
            version.with_user(self.admin).unlink()

    def test_18_master_reflects_coverage_and_current_version(self):
        jd = self.make_jd()
        version = self.publish_version(self.make_version(jd))
        self.assertEqual(jd.coverage_state, "covered")
        self.assertEqual(jd.coverage_score, 100.0)
        self.assertEqual(jd.current_version_id, version)

