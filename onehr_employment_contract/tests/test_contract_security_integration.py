from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRContractCommon


@tagged("post_install", "-at_install", "onehr_employment_contract")
class TestContractSecurityIntegration(OneHRContractCommon):
    def test_15_line_manager_reads_direct_report(self):
        contract = self.make_contract()
        visible_contracts = self.env["onehr.contract"].with_user(self.line_user).search([])

        self.assertIn(contract, visible_contracts)
        employee_action = contract.with_user(self.line_user).action_open_employee()
        self.assertEqual(employee_action["res_model"], "hr.employee.public")

    def test_16_line_manager_cannot_write_contract(self):
        contract = self.make_contract()
        with self.assertRaises(AccessError):
            contract.with_user(self.line_user).write(
                {"responsible_user_id": self.line_user.id}
            )

    def test_17_other_company_isolated(self):
        other_employee = self.env["hr.employee"].create(
            {
                "name": "Other Company Worker",
                "company_id": self.other_company.id,
                "contract_date_start": fields.Date.today(),
            }
        )
        allowed_companies = [self.company.id, self.other_company.id]
        other_template = self.env["onehr.contract.template"].with_user(
            self.manager
        ).with_context(allowed_company_ids=allowed_companies).create(
            {
                "code": "OTHER",
                "name": "Other Company Contract",
                "company_id": self.other_company.id,
                "valid_from": fields.Date.today(),
            }
        )
        other_template.with_user(self.manager).with_context(
            allowed_company_ids=allowed_companies
        ).action_activate()

        other_contract = self.env["onehr.contract"].with_user(
            self.manager
        ).with_context(allowed_company_ids=allowed_companies).create(
            {
                "employee_id": other_employee.id,
                "company_id": self.other_company.id,
                "hr_version_id": other_employee.version_ids[:1].id,
                "template_id": other_template.id,
            }
        )

        officer_visible_ids = self.env["onehr.contract"].with_user(
            self.officer
        ).search([]).ids
        self.assertNotIn(other_contract.id, officer_visible_ids)

    def test_18_soft_document_action_absent_or_authority_guarded(self):
        contract = self.make_contract()
        contract.with_context(
            onehr_contract_state_action=True,
            onehr_contract_evidence_action=True,
        ).write({"state": "approved"})

        try:
            self.env["onehr.document.template"]
        except KeyError:
            with self.assertRaises(UserError):
                contract.with_user(self.officer).action_generate_contract_document()
            with self.assertRaises(UserError):
                contract.with_user(self.officer).action_request_contract_signature()
        else:
            # The integration remains soft. When onehr_document is installed,
            # its own Document Manager privilege remains authoritative for
            # e-signature dispatch; Contract Officer does not bypass it.
            with self.assertRaises(AccessError):
                contract.with_user(self.officer).action_request_contract_signature()

    def test_19_renewal_uses_native_create_contract(self):
        contract = self.make_contract()
        contract_end = fields.Date.today() + timedelta(days=30)
        self.version.write({"contract_date_end": contract_end})
        contract.with_context(onehr_contract_state_action=True).write(
            {"state": "active"}
        )

        action = contract.with_user(self.manager).action_create_renewal()
        renewal = self.env["onehr.contract"].browse(action["res_id"])

        self.assertEqual(renewal.contract_kind, "renewal")
        self.assertEqual(renewal.predecessor_contract_id, contract)
        self.assertEqual(
            renewal.hr_version_id.contract_date_start,
            contract_end + timedelta(days=1),
        )

    def test_20_non_draft_history_deletion_protected(self):
        contract = self.make_contract()
        contract.with_context(onehr_contract_state_action=True).write(
            {"state": "approved"}
        )

        with self.assertRaises((AccessError, UserError)):
            contract.with_user(self.manager).unlink()
