from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import OffboardingCase


@tagged("post_install", "-at_install", "onehr_retirement_offboarding")
class TestOffboardingLifecycle(OffboardingCase):
    def test_01_exact_case_model_exists(self):
        self.assertEqual(self.env["onehr.offboarding"]._name, "onehr.offboarding")

    def test_02_case_sequence_is_generated(self):
        self.assertTrue(self.case.name and self.case.name != "New")

    def test_03_employee_company_snapshot_is_frozen_on_create(self):
        self.assertEqual(self.case.company_id, self.employee.company_id)

    def test_04_proposed_exit_cannot_precede_request(self):
        with self.assertRaises(ValidationError):
            self.Case.create(
                {
                    "employee_id": self.employee.id,
                    "offboarding_type": "other",
                    "request_date": fields.Date.today(),
                    "proposed_exit_date": fields.Date.today() - timedelta(days=1),
                }
            )

    def test_05_direct_state_write_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.case.write({"state": "closed"})

    def test_06_open_case_uniqueness_is_enforced(self):
        with self.assertRaises(ValidationError):
            self.Case.create(
                {
                    "employee_id": self.employee.id,
                    "offboarding_type": "retirement",
                    "request_date": fields.Date.today(),
                    "proposed_exit_date": fields.Date.today() + timedelta(days=30),
                }
            )

    def test_07_approval_payload_is_minimum_structured_snapshot(self):
        payload = self.case._approval_payload()
        self.assertEqual(payload["employee_id"], self.employee.id)
        self.assertNotIn("exit_reason_notes", payload)

    def test_08_approval_rule_context_preserves_company_and_document_type(self):
        context = self.case._approval_rule_context()
        self.assertEqual(context["company_id"], self.env.company.id)
        self.assertTrue(context["document_type"].startswith("onehr.offboarding."))

    def test_09_readiness_reports_missing_controls(self):
        blockers = self.case._readiness_blockers()
        self.assertTrue(blockers)
        self.assertTrue(any("clearance" in text.lower() for text in blockers))

    def test_10_complete_requires_in_progress_state(self):
        with self.assertRaises(UserError):
            self.case.action_complete()
