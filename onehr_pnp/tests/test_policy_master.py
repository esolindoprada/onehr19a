
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRPnPCommon


@tagged("post_install", "-at_install", "onehr_pnp")
class TestPolicyMaster(OneHRPnPCommon):
    def test_01_exact_three_persistent_models(self):
        self.assertIn("onehr.policy", self.env)
        self.assertIn("onehr.policy.ack", self.env)
        self.assertIn("onehr.policy.evidence", self.env)
        self.assertNotIn("onehr_pnp.onehr_pnp", self.env)

    def test_02_settings_extension_is_transient(self):
        self.assertTrue(self.env["res.config.settings"].is_transient())

    def test_03_policy_reference_uses_sequence(self):
        policy = self.make_policy()
        self.assertNotEqual(policy.policy_code, "New")
        self.assertTrue(policy.policy_code.startswith("PNP/"))

    def test_04_first_policy_version_defaults_to_one(self):
        policy = self.make_policy()
        self.assertEqual(policy.version_no, 1)
        self.assertEqual(policy.state, "draft")

    def test_05_policy_code_version_unique_per_company(self):
        policy = self.make_policy()
        with self.assertRaises(ValidationError):
            self.env["onehr.policy"].with_user(self.owner).create(
                self.policy_values(
                    policy_code=policy.policy_code,
                    version_no=policy.version_no,
                )
            )

    def test_06_review_interval_positive(self):
        with self.assertRaises(ValidationError):
            self.make_policy(review_interval_months=0)

    def test_07_ack_reminder_positive(self):
        with self.assertRaises(ValidationError):
            self.make_policy(ack_reminder_days=0)

    def test_08_retention_positive(self):
        with self.assertRaises(ValidationError):
            self.make_policy(retention_years=0)

    def test_09_evidence_due_days_nonnegative(self):
        with self.assertRaises(ValidationError):
            self.make_policy(evidence_due_days=-1)

    def test_10_all_employees_cannot_mix_scoped_targets(self):
        with self.assertRaises(ValidationError):
            self.make_policy(
                target_all_employees=True,
                target_employee_ids=[
                    Command.set([self.employee.id])
                ],
            )

    def test_11_cross_company_employee_target_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.policy"].create(
                self.policy_values(
                    target_department_ids=[Command.set([])],
                    target_employee_ids=[
                        Command.set([self.other_employee.id])
                    ],
                )
            )

    def test_12_plain_internal_user_has_no_policy_access(self):
        self.make_policy()
        with self.assertRaises(AccessError):
            self.env["onehr.policy"].with_user(
                self.plain_user
            ).search([])

    def test_13_owner_sees_owned_draft(self):
        policy = self.make_policy()
        visible = self.env["onehr.policy"].with_user(
            self.owner
        ).search([("id", "=", policy.id)])
        self.assertEqual(visible.id, policy.id)

    def test_14_preview_audience_resolves_employees(self):
        policy = self.make_policy()
        action = policy.with_user(
            self.compliance
        ).action_preview_audience()
        self.assertEqual(action["tag"], "display_notification")

