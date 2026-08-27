from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRDocumentCommon


@tagged("post_install", "-at_install", "onehr_document")
class TestEsignExpiry(OneHRDocumentCommon):
    def test_publish_sign_wizard_queues_transaction_and_version(self):
        version = self.create_draft_version(user=self.manager)
        version.with_user(self.manager).action_issue()
        wizard = self.env["wizard.document.publish.sign"].with_user(
            self.manager
        ).create(
            {
                "document_id": version.document_id.id,
                "document_version_id": version.id,
                "provider_key": "test_adapter",
                "signer_name": self.employee.name,
                "signer_email": self.employee.work_email,
                "dispatch_now": False,
            }
        )
        action = wizard.action_submit()
        transaction = self.env["onehr.esign.transaction"].browse(
            action["res_id"]
        )
        self.assertEqual(transaction.state, "queued")
        self.assertTrue(transaction.correlation_id)
        self.assertEqual(version.state, "signature_pending")

    def test_provider_status_signed_updates_version_and_terminal_transaction_is_immutable(self):
        version = self.create_draft_version(user=self.manager)
        version.with_user(self.manager).action_issue()
        transaction = self.env["onehr.esign.transaction"].with_user(
            self.manager
        ).create(
            {
                "document_version_id": version.id,
                "provider_key": "test_adapter",
                "signer_name": self.employee.name,
                "signer_email": self.employee.work_email,
            }
        )
        transaction.with_user(self.manager).apply_provider_status(
            state="signed",
            provider_reference="SIGNED-001",
        )
        self.assertEqual(transaction.state, "signed")
        self.assertEqual(version.state, "signed")
        with self.assertRaises(AccessError):
            transaction.with_user(self.manager).apply_provider_status(
                state="viewed"
            )

    def test_esign_model_has_no_plaintext_credential_fields(self):
        forbidden = {
            "password",
            "secret",
            "token",
            "api_key",
            "access_token",
            "client_secret",
        }
        self.assertFalse(forbidden & set(self.env["onehr.esign.transaction"]._fields))

    def test_expiry_reminder_action_and_expiry_state(self):
        today = fields.Date.today()
        self.internal_category.write({"default_grace_days": 7})
        version = self.create_draft_version(
            expiry_date=today + timedelta(days=5),
        )
        self.assertEqual(version.grace_end_date, today + timedelta(days=12))
        version.action_issue()
        version.action_schedule_expiry_reminder()
        self.assertTrue(version.reminder_activity_id)
        self.assertTrue(version.last_reminder_at)
        version.action_expire()
        self.assertEqual(version.state, "expired")

    def test_binary_attachment_is_bound_to_document_version_record(self):
        version = self.create_draft_version(
            file_data=b"YXR0YWNobWVudC1ldmlkZW5jZQ==",
            file_name="evidence.txt",
        )
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "onehr.document.version"),
                ("res_id", "=", version.id),
                ("res_field", "=", "file_data"),
            ],
            limit=1,
        )
        self.assertTrue(attachment)
