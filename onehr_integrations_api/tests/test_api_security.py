from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRApiCommon


@tagged("post_install", "-at_install", "onehr_integrations_api")
class TestApiSecurity(OneHRApiCommon):
    def test_01_exact_five_models_present(self):
        for model in ("onehr.api.key", "onehr.api.scope", "onehr.webhook", "onehr.api.log", "onehr.api.queue"):
            self.assertIn(model, self.env)
        self.assertNotIn("onehr_integrations_api.onehr_integrations_api", self.env)

    def test_02_operator_can_read_scope_but_not_create(self):
        scope = self.make_scope()
        self.assertTrue(scope.with_user(self.operator).read(["code"]))
        with self.assertRaises(AccessError):
            self.env["onehr.api.scope"].with_user(self.operator).create({"name": "No", "code": "test.no.create"})

    def test_03_plain_internal_user_has_no_custom_model_access(self):
        with self.assertRaises(AccessError):
            self.env["onehr.api.key"].with_user(self.plain_user).search([])

    def test_04_api_admin_does_not_gain_hr_or_system_authority(self):
        self.assertTrue(self.admin.has_group("onehr_integrations_api.group_onehr_api_admin"))
        self.assertFalse(self.admin.has_group("hr.group_hr_user"))
        self.assertFalse(self.admin.has_group("base.group_system"))

    def test_05_service_user_must_be_allowed_in_key_company(self):
        scope = self.make_scope()
        with self.assertRaises(ValidationError):
            self.make_key(scope, service_user_id=self.other_service.id)

    def test_06_company_rule_hides_other_company_key(self):
        scope = self.make_scope()
        other_key = self.env["onehr.api.key"].with_user(self.env.user).create({
            "name": "Other Company Key",
            "company_id": self.other_company.id,
            "service_user_id": self.other_service.id,
            "scope_ids": [(6, 0, scope.ids)],
        })
        self.assertFalse(self.env["onehr.api.key"].with_user(self.operator).search([("id", "=", other_key.id)]))

    def test_07_api_log_is_not_manually_creatable(self):
        with self.assertRaises(AccessError):
            self.env["onehr.api.log"].with_user(self.admin).create({"direction": "inbound", "outcome": "success"})

    def test_08_api_log_is_immutable(self):
        log = self.env["onehr.api.log"].technical_create({
            "company_id": self.company.id,
            "direction": "inbound",
            "request_id": f"immutable-{self._testMethodName}",
            "method": "GET",
            "path": "/test",
            "http_status": 200,
            "outcome": "success",
        })
        with self.assertRaises(AccessError):
            log.with_user(self.admin).write({"http_status": 500})
        with self.assertRaises(AccessError):
            log.with_user(self.admin).unlink()
