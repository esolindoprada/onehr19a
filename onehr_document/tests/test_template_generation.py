from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRDocumentCommon


@tagged("post_install", "-at_install", "onehr_document")
class TestTemplateGeneration(OneHRDocumentCommon):
    def test_template_contract_renders_known_tokens_and_escapes_values(self):
        self.employee.name = "<Executive>"
        values = {
            "employee.name": self.employee.name,
            "employee.onehr_employee_number": self.employee.onehr_employee_number,
            "employee.work_email": self.employee.work_email,
            "company.name": self.company.name,
            "category.name": self.internal_category.name,
            "source.display_name": "",
            "current_date": fields.Date.today(),
            "effective_from": fields.Date.today(),
            "effective_to": False,
            "expiry_date": False,
            "document.name": "Letter",
            "document.number": "HRDOC/TEST",
        }
        rendered = self.template_version.render_contract(values)
        self.assertIn("&lt;Executive&gt;", rendered["body_html"])
        self.assertNotIn("<Executive>", rendered["body_html"])

    def test_unknown_template_token_rejected_on_activation(self):
        version = self.env["onehr.document.template.version"].with_user(
            self.manager
        ).create(
            {
                "template_id": self.template.id,
                "version": 2,
                "subject_template": "{{ employee.unknown_secret }}",
                "body_html": "<p>Bad</p>",
                "valid_from": fields.Date.today(),
            }
        )
        with self.assertRaises(ValidationError):
            version.with_user(self.manager).action_activate()

    def test_active_template_version_is_immutable_and_successor_is_draft(self):
        with self.assertRaises(AccessError):
            self.template_version.with_user(self.manager).write(
                {"body_html": "<p>Rewritten</p>"}
            )
        action = self.template_version.with_user(
            self.manager
        ).action_create_successor()
        successor = self.env["onehr.document.template.version"].browse(
            action["res_id"]
        )
        self.assertEqual(successor.state, "draft")
        self.assertEqual(successor.template_id, self.template)

    def test_generate_wizard_creates_document_and_version_without_runtime_pdf_dependency(self):
        wizard = self.env["wizard.document.generate"].with_user(
            self.officer
        ).with_context(onehr_document_skip_pdf_render=True).create(
            {
                "template_id": self.template.id,
                "template_version_id": self.template_version.id,
                "company_id": self.company.id,
                "employee_id": self.employee.id,
                "category_id": self.internal_category.id,
                "document_name": "Generated Employment Letter",
                "effective_from": fields.Date.today(),
            }
        )
        preview_action = wizard.action_preview()
        self.assertEqual(preview_action["res_model"], "wizard.document.generate")
        self.assertTrue(wizard.preview_html)

        action = wizard.action_generate()
        version = self.env["onehr.document.version"].browse(action["res_id"])
        self.assertEqual(version.template_version_id, self.template_version)
        self.assertEqual(version.document_id.template_id, self.template)
        self.assertIn(self.employee.onehr_employee_number, version.rendered_content_html)
