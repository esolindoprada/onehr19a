from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRSOPCommon


@tagged("post_install", "-at_install", "onehr_sop")
class TestSOPMaster(OneHRSOPCommon):
    def test_01_exact_three_models_present(self):
        self.assertIn("onehr.sop", self.env)
        self.assertIn("onehr.sop.version", self.env)
        self.assertIn("onehr.sop.ack", self.env)
        self.assertNotIn("onehr_sop.onehr_sop", self.env)

    def test_02_sop_reference_uses_sequence(self):
        sop = self.make_sop()
        self.assertNotEqual(sop.code, "New")
        self.assertTrue(sop.code.startswith("SOP/"))

    def test_03_review_interval_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.make_sop(review_interval_months=0)

    def test_04_retention_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.make_sop(retention_years=0)

    def test_05_ack_reminder_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.make_sop(ack_reminder_days=0)

    def test_06_archive_category_company_must_match(self):
        with self.assertRaises(ValidationError):
            self.make_sop(
                document_category_id=self.other_document_category.id
            )

    def test_07_first_version_is_draft_v1(self):
        version = self.make_version()
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.state, "draft")

    def test_08_only_one_inflight_version_allowed(self):
        sop = self.make_sop()
        self.make_version(sop)
        with self.assertRaises(UserError):
            self.make_version(sop)

    def test_09_all_employees_cannot_mix_with_scoped_targets(self):
        sop = self.make_sop()
        with self.assertRaises(ValidationError):
            self.make_version(
                sop,
                target_all_employees=True,
                target_employee_ids=[Command.set([self.employee.id])],
            )

    def test_10_publication_targets_must_match_company(self):
        sop = self.make_sop()
        with self.assertRaises(ValidationError):
            self.make_version(
                sop,
                target_employee_ids=[Command.set([self.other_employee.id])],
            )

    def test_11_preview_audience_resolves_employee_users(self):
        version = self.make_version()
        action = version.with_user(self.editor).action_preview_audience()
        self.assertEqual(action["tag"], "display_notification")

    def test_12_plain_internal_user_cannot_read_sop(self):
        self.make_sop()
        with self.assertRaises(AccessError):
            self.env["onehr.sop"].with_user(self.plain_user).search([])
