import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRDocumentCommon


@tagged("post_install", "-at_install", "onehr_document")
class TestDocumentGovernance(OneHRDocumentCommon):
    def test_registry_models_exist_and_parallel_employee_document_absent(self):
        for model_name in (
            "onehr.document.category",
            "onehr.document",
            "onehr.document.version",
            "onehr.document.template",
            "onehr.document.template.version",
            "onehr.esign.transaction",
            "wizard.document.generate",
            "wizard.document.publish.sign",
        ):
            self.assertIn(model_name, self.env)
        self.assertNotIn("onehr.employee.document", self.env)
        self.assertIn("default_grace_days", self.env["onehr.document.category"]._fields)

    def test_document_number_source_snapshot_and_source_action(self):
        document = self.create_document(source=True)
        self.assertNotEqual(document.document_number, "New")
        self.assertEqual(document.source_display_name, self.employee.display_name)
        action = document.action_open_source()
        self.assertEqual(action["res_model"], "hr.employee")
        self.assertEqual(action["res_id"], self.employee.id)

    def test_document_source_pair_and_employee_company_integrity(self):
        with self.assertRaises((ValidationError, UserError)):
            self.env["onehr.document"].with_user(self.officer).create(
                {
                    "name": "Broken Source",
                    "category_id": self.internal_category.id,
                    "company_id": self.company.id,
                    "source_model_id": self.env["ir.model"]._get("hr.employee").id,
                    "valid_from": fields.Date.today(),
                }
            )
        with self.assertRaises(ValidationError):
            self.env["onehr.document"].with_user(self.officer).create(
                {
                    "name": "Wrong Company",
                    "category_id": self.internal_category.id,
                    "company_id": self.company.id,
                    "employee_id": self.other_employee.id,
                    "valid_from": fields.Date.today(),
                }
            )

    def test_version_upload_checksum_issue_and_immutability(self):
        version = self.create_draft_version(
            file_data=base64.b64encode(b"controlled file"),
            file_name="evidence.pdf",
        )
        self.assertTrue(version.file_checksum)
        self.assertEqual(version.mimetype, "application/pdf")
        version.action_issue()
        self.assertEqual(version.state, "issued")
        self.assertTrue(version.issued_at)
        with self.assertRaises(AccessError):
            version.write({"file_name": "rewritten.pdf"})
        with self.assertRaises(AccessError):
            version.unlink()

    def test_successor_supersedes_without_rewriting_history(self):
        version = self.create_draft_version()
        version.action_issue()
        old_id = version.id
        action = version.action_create_successor()
        successor = self.env["onehr.document.version"].browse(action["res_id"])
        self.assertEqual(version.id, old_id)
        self.assertEqual(version.state, "superseded")
        self.assertEqual(successor.state, "draft")
        self.assertGreater(successor.version, version.version)
