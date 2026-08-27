from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRContractCommon


@tagged("post_install", "-at_install", "onehr_employment_contract")
class TestContractWorkflow(OneHRContractCommon):
    def test_08_contract_number_and_native_link(self):
        contract = self.make_contract()

        self.assertNotEqual(contract.name, "New")
        self.assertEqual(contract.hr_version_id, self.version)
        self.assertEqual(contract.employee_name, self.employee.name)
        self.assertEqual(contract.template_name, self.template.name)

    def test_09_wrong_employee_version_rejected(self):
        other_employee = self.env["hr.employee"].create(
            {
                "name": "Other Employee",
                "company_id": self.company.id,
                "contract_date_start": fields.Date.today(),
            }
        )
        with self.assertRaises(ValidationError):
            self.make_contract(hr_version_id=other_employee.version_ids[:1].id)

    def test_10_state_direct_write_blocked(self):
        contract = self.make_contract()
        with self.assertRaises(AccessError):
            contract.with_user(self.officer).write({"state": "approved"})

    def test_11_submission_freezes_snapshot(self):
        contract = self.make_contract()

        # Validate the immutable snapshot contract without requiring a workflow
        # matrix fixture in this source-level runtime test.
        snapshot = contract._snapshot_values()

        self.assertEqual(
            snapshot["snapshot_contract_start"],
            self.version.contract_date_start,
        )
        self.assertEqual(
            snapshot["snapshot_contract_wage"],
            self.version.contract_wage,
        )

    def test_12_approval_hook_approved(self):
        contract = self.make_contract()
        contract.with_context(
            onehr_contract_state_action=True,
            onehr_contract_evidence_action=True,
        ).write(
            {
                "state": "in_review",
                "pending_approval_kind": "contract",
            }
        )

        contract.with_user(self.manager)._on_approval_finalized(
            "approve",
            self.env["onehr.approval.request"],
        )

        self.assertEqual(contract.state, "approved")
        self.assertTrue(contract.approved_at)

    def test_13_approval_hook_rejected_and_reset(self):
        contract = self.make_contract()
        contract.with_context(
            onehr_contract_state_action=True,
            onehr_contract_evidence_action=True,
        ).write(
            {
                "state": "in_review",
                "pending_approval_kind": "contract",
            }
        )

        contract.with_user(self.manager)._on_approval_finalized(
            "reject",
            self.env["onehr.approval.request"],
        )
        self.assertEqual(contract.state, "rejected")

        contract.with_user(self.officer).action_reset_to_draft()
        self.assertEqual(contract.state, "draft")

    def test_14_termination_date_validation(self):
        contract = self.make_contract()
        invalid_date = self.version.contract_date_start - timedelta(days=1)

        with self.assertRaises(ValidationError):
            contract.write({"termination_effective_date": invalid_date})
