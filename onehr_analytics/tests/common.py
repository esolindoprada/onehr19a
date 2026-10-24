from odoo import Command, fields
from odoo.tests.common import TransactionCase


class AnalyticsCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Analytics Other Company"})
        cls.group_analyst = cls.env.ref("onehr_analytics.group_onehr_analytics_analyst")
        cls.group_manager = cls.env.ref("onehr_analytics.group_onehr_analytics_manager")
        cls.group_admin = cls.env.ref("onehr_analytics.group_onehr_analytics_admin")

        cls.analyst = cls._make_user("analytics.analyst", cls.group_analyst)
        cls.manager = cls._make_user("analytics.manager", cls.group_manager)
        cls.admin = cls._make_user("analytics.admin", cls.group_admin)

    @classmethod
    def _make_user(cls, login, group):
        return cls.env["res.users"].create({
            "name": login,
            "login": login,
            "email": f"{login}@example.test",
            "company_id": cls.company.id,
            "company_ids": [Command.set([cls.company.id])],
            "group_ids": [Command.set([group.id])],
        })

    def make_tile(self, **overrides):
        values = {
            "name": "Headcount KPI",
            "code": "workforce.headcount",
            "company_id": self.company.id,
            "category": "workforce",
            "provider_mode": "manual",
            "manual_value": 100.0,
            "target_value": 100.0,
            "snapshot_frequency": "monthly",
            "owner_user_id": self.manager.id,
        }
        values.update(overrides)
        return self.env["onehr.analytics.tile"].with_user(self.manager).create(values)

    def activate(self, tile):
        tile.with_user(self.manager).action_activate()
        return tile

    def create_snapshot_evidence(self, tile, **overrides):
        values = {
            "tile_id": tile.id,
            "company_id": tile.company_id.id,
            "snapshot_at": fields.Datetime.now(),
            "period_start": fields.Date.context_today(self.env.user),
            "period_end": fields.Date.context_today(self.env.user),
            "value": 1.0,
            "target_value": 1.0,
            "variance_value": 0.0,
            "status": "normal",
            "source_name": "test",
            "drilldown_domain_expression": "[]",
        }
        values.update(overrides)
        return self.env["onehr.kpi.snapshot"].with_user(self.manager).with_context(
            onehr_analytics_snapshot_create=True
        ).create(values)
