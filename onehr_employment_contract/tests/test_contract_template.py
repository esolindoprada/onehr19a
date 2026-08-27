from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRContractCommon


@tagged("post_install", "-at_install", "onehr_employment_contract")
class TestContractTemplate(OneHRContractCommon):
    def test_01_registry_exact_core_models(self):
        self.assertIn("onehr.contract", self.env)
        self.assertIn("onehr.contract.template", self.env)
        self.assertNotIn("onehr_employment_contract.onehr_employment_contract", self.env)

    def test_02_manifest_native_hr_version_contract(self):
        self.assertEqual(self.version.employee_id, self.employee)
        self.assertTrue(self.version.contract_date_start)

    def test_03_template_code_uppercase(self):
        row = self.env["onehr.contract.template"].with_user(self.manager).create(
            {
                "code": "lower",
                "name": "Lower",
                "valid_from": fields.Date.today(),
            }
        )
        self.assertEqual(row.code, "LOWER")

    def test_04_template_unique_version(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.contract.template"].with_user(self.manager).create(
                {
                    "code": "PERM",
                    "name": "Duplicate",
                    "company_id": self.company.id,
                    "version": 1,
                    "valid_from": fields.Date.today(),
                }
            )

    def test_05_template_overlap(self):
        self.template.with_user(self.manager).write(
            {"valid_to": fields.Date.today() + timedelta(days=30)}
        )
        second = self.env["onehr.contract.template"].with_user(self.manager).create(
            {
                "code": "PERM",
                "name": "Version 2",
                "company_id": self.company.id,
                "version": 2,
                "valid_from": fields.Date.today() + timedelta(days=10),
            }
        )
        with self.assertRaises(ValidationError):
            second.with_user(self.manager).action_activate()

    def test_06_template_version_copy(self):
        action = self.template.with_user(self.manager).action_create_new_version()
        new_version = self.env["onehr.contract.template"].browse(action["res_id"])

        self.assertEqual(new_version.version, 2)
        self.assertEqual(new_version.state, "draft")

    def test_07_officer_cannot_admin_template(self):
        with self.assertRaises(AccessError):
            self.env["onehr.contract.template"].with_user(self.officer).create(
                {
                    "code": "NO",
                    "name": "Unauthorized Template",
                    "valid_from": fields.Date.today(),
                }
            )
