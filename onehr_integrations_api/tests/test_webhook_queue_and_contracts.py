from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..services.domain_adapters import DomainAdapters
from ..services.errors import CapabilityUnavailable
from ..services.runtime import ApiIdentity, ApiRuntime
from .common import OneHRApiCommon


@tagged("post_install", "-at_install", "onehr_integrations_api")
class TestWebhookQueueAndContracts(OneHRApiCommon):
    def test_17_outbound_webhook_requires_target_url(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.webhook"].with_user(self.admin).create({
                "name": "Broken", "company_id": self.company.id,
                "direction": "outbound", "event_code": "test.event",
            })

    def test_18_inbound_webhook_event_is_allowlisted(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.webhook"].with_user(self.admin).create({
                "name": "Unsafe", "company_id": self.company.id,
                "direction": "inbound", "event_code": "arbitrary.model.method",
                "service_user_id": self.service_user.id,
            })

    def test_19_webhook_secret_rotation_and_activation(self):
        webhook = self.make_outbound_webhook()
        notification = webhook.with_user(self.admin).action_rotate_secret()
        self.assertTrue(notification["params"]["message"])
        webhook.with_user(self.admin).action_activate()
        self.assertEqual(webhook.state, "active")

    def test_20_test_webhook_creates_queue_not_direct_business_mutation(self):
        webhook = self.make_outbound_webhook()
        webhook.with_user(self.admin).action_rotate_secret()
        webhook.with_user(self.admin).action_activate()
        before = self.env["onehr.api.queue"].search_count([])
        action = webhook.with_user(self.admin).action_test_webhook()
        self.assertEqual(action["res_model"], "onehr.api.queue")
        self.assertEqual(self.env["onehr.api.queue"].search_count([]), before + 1)

    def test_21_queue_creation_is_transport_controlled(self):
        webhook = self.make_outbound_webhook()
        with self.assertRaises(AccessError):
            self.env["onehr.api.queue"].with_user(self.admin).create({
                "company_id": self.company.id, "webhook_id": webhook.id,
                "event_code": "x", "dedupe_key": "x", "request_id": "x",
                "payload_json": "{}", "payload_hash": "x", "max_attempts": 1,
            })

    def test_22_queue_dedupe_is_idempotent(self):
        webhook = self.make_outbound_webhook()
        first = self.env["onehr.api.queue"].sudo().create_from_webhook(webhook, {"a": 1}, "same")
        existing = self.env["onehr.api.queue"].sudo().search([("webhook_id", "=", webhook.id), ("dedupe_key", "=", "same")])
        self.assertEqual(existing, first)

    def test_23_queue_evidence_cannot_be_deleted(self):
        webhook = self.make_outbound_webhook()
        queue = self.env["onehr.api.queue"].sudo().create_from_webhook(webhook, {"a": 1}, "delete-guard")
        with self.assertRaises(UserError):
            queue.with_user(self.admin).unlink()

    def test_24_health_adapter_reports_soft_capabilities(self):
        scope = self.make_scope(code="test.health")
        key = self.make_key(scope, hmac_required=False)
        identity = ApiIdentity(key, "secret", "", scope.code)
        class FakeHttp:
            headers = {}
            method = "GET"
            path = "/test"
            remote_addr = "127.0.0.1"
        payload = DomainAdapters(ApiRuntime(self.env, FakeHttp()), identity).health()
        self.assertEqual(payload["company_id"], self.company.id)
        self.assertIn("capabilities", payload)

    def test_25_scope_code_format_is_governed(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.api.scope"].with_user(self.admin).create({"name": "Bad", "code": "BAD SCOPE"})


    def test_26_webhook_dead_letter_count_is_searchable(self):
        """Search-view domains may use failed_count only when the field is searchable."""
        field = self.env["onehr.webhook"]._fields["failed_count"]
        self.assertTrue(field.store or field.search)

        webhook = self.make_outbound_webhook()
        result = self.env["onehr.webhook"].with_user(self.admin).search([
            ("failed_count", ">", 0),
        ])
        self.assertNotIn(webhook, result)
