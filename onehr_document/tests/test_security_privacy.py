from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRDocumentCommon


@tagged("post_install", "-at_install", "onehr_document")
class TestDocumentSecurityPrivacy(OneHRDocumentCommon):
    def test_employee_user_reads_only_own_employee_visible_internal_document(self):
        own = self.create_document()
        confidential = self.create_document(category=self.confidential_category)
        visible = self.env["onehr.document"].with_user(self.self_user).search([])
        self.assertIn(own, visible)
        self.assertNotIn(confidential, visible)

    def test_officer_sees_nonrestricted_but_not_restricted(self):
        normal = self.create_document(category=self.confidential_category)
        restricted = self.create_document(
            category=self.restricted_category,
            user=self.restricted_manager,
        )
        visible = self.env["onehr.document"].with_user(self.officer).search([])
        self.assertIn(normal, visible)
        self.assertNotIn(restricted, visible)

    def test_compliance_reads_restricted_but_cannot_write(self):
        restricted = self.create_document(
            category=self.restricted_category,
            user=self.restricted_manager,
        )
        visible = self.env["onehr.document"].with_user(self.compliance).search([])
        self.assertIn(restricted, visible)
        with self.assertRaises(AccessError):
            restricted.with_user(self.compliance).write({"name": "Changed"})

    def test_manager_requires_explicit_restricted_access_to_create_restricted_document(self):
        with self.assertRaises(AccessError):
            self.env["onehr.document"].with_user(self.manager).create(
                {
                    "name": "Restricted Without Dual Gate",
                    "category_id": self.restricted_category.id,
                    "company_id": self.company.id,
                    "employee_id": self.employee.id,
                    "valid_from": fields.Date.today(),
                }
            )
        allowed = self.create_document(
            category=self.restricted_category,
            user=self.restricted_manager,
        )
        self.assertTrue(allowed)

    def test_global_company_rule_hides_other_company(self):
        other_category = self.env["onehr.document.category"].with_user(
            self.other_manager
        ).create(
            {
                "code": "OTHER",
                "name": "Other Company Document",
                "company_id": self.other_company.id,
                "valid_from": fields.Date.today(),
            }
        )
        other_document = self.env["onehr.document"].with_user(
            self.other_officer
        ).create(
            {
                "name": "Other Company",
                "category_id": other_category.id,
                "company_id": self.other_company.id,
                "employee_id": self.other_employee.id,
                "valid_from": fields.Date.today(),
            }
        )
        visible_ids = self.env["onehr.document"].with_user(self.officer).search([]).ids
        self.assertNotIn(other_document.id, visible_ids)
