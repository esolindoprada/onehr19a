from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRApiCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": f"API Other Company {cls.__name__}"})
        cls.group_api_user = cls.env.ref("onehr_integrations_api.group_onehr_api_user")
        cls.group_api_admin = cls.env.ref("onehr_integrations_api.group_onehr_api_admin")
        cls.group_internal = cls.env.ref("base.group_user")

        def make_user(name, login, groups, companies):
            return cls.env["res.users"].with_context(no_reset_password=True).create({
                "name": name,
                "login": login,
                "company_id": companies[0].id,
                "company_ids": [Command.set([company.id for company in companies])],
                "group_ids": [Command.set(groups.ids)],
            })

        suffix = cls.__name__.lower()
        cls.operator = make_user("API Operator", f"api_operator_{suffix}", cls.group_api_user, [cls.company])
        cls.admin = make_user("API Administrator", f"api_admin_{suffix}", cls.group_api_admin, [cls.company])
        cls.service_user = make_user("API Service User", f"api_service_{suffix}", cls.group_internal, [cls.company])
        cls.other_service = make_user("Other API Service", f"api_other_service_{suffix}", cls.group_internal, [cls.other_company])
        cls.plain_user = make_user("Plain User", f"api_plain_{suffix}", cls.group_internal, [cls.company])

    def make_scope(self, code=None, **extra):
        code = code or f"test.{self._testMethodName.lower()}"
        values = {"name": code.replace(".", " ").title(), "code": code, "risk_level": "medium"}
        values.update(extra)
        return self.env["onehr.api.scope"].with_user(self.admin).create(values)

    def make_key(self, scope=None, **extra):
        scope = scope or self.make_scope()
        values = {
            "name": f"Key {self._testMethodName}",
            "company_id": self.company.id,
            "service_user_id": self.service_user.id,
            "scope_ids": [Command.set(scope.ids)],
        }
        values.update(extra)
        return self.env["onehr.api.key"].with_user(self.admin).create(values)

    def generated_raw_key(self, key):
        notification = key.with_user(self.admin).action_generate_secret()
        message = notification["params"]["message"]
        return message.split("\n")[-1].strip()

    def make_outbound_webhook(self, **extra):
        values = {
            "name": f"Webhook {self._testMethodName}",
            "company_id": self.company.id,
            "direction": "outbound",
            "event_code": "test.event",
            "target_url": "https://example.com/webhook",
        }
        values.update(extra)
        return self.env["onehr.webhook"].with_user(self.admin).create(values)
