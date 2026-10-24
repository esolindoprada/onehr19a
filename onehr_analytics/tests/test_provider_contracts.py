from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..models.provider_engine import AnalyticsProviderEngine
from .common import AnalyticsCase


@tagged("post_install", "-at_install", "onehr_analytics")
class TestAnalyticsProviderContracts(AnalyticsCase):
    def test_25_literal_domain_rejects_python_expression(self):
        tile = self.make_tile(code="test.provider.domain")
        with self.assertRaises(ValidationError):
            tile._analytics_parse_domain("__import__('os').system('echo unsafe')")

    def test_26_model_aggregate_rejects_bad_measure_field(self):
        tile = self.make_tile(
            code="test.provider.measure",
            provider_mode="model_aggregate",
            source_model_name="hr.employee",
            aggregate_function="sum",
            measure_field_name="name",
        )
        with self.assertRaises(ValidationError):
            tile._validate_provider_configuration()

    def test_27_model_aggregate_rejects_bad_date_field(self):
        tile = self.make_tile(
            code="test.provider.date",
            provider_mode="model_aggregate",
            source_model_name="hr.employee",
            aggregate_function="count",
            date_field_name="name",
        )
        with self.assertRaises(ValidationError):
            tile._validate_provider_configuration()

    def test_28_branch_scope_fails_closed_without_source_branch(self):
        tile = self.make_tile(
            code="test.provider.branch",
            provider_mode="model_aggregate",
            source_model_name="hr.employee",
            aggregate_function="count",
            branch_code="BALI",
        )
        with self.assertRaises(ValidationError):
            tile._validate_provider_configuration()

    def test_29_analyst_cannot_manage_tile_configuration(self):
        tile = self.make_tile(code="test.provider.analyst")
        with self.assertRaises(AccessError):
            tile.with_user(self.analyst).write({"target_value": 200.0})

    def test_30_manual_provider_has_no_raw_record_payload(self):
        tile = self.make_tile(code="test.provider.manual.payload", manual_value=88.0)
        period = tile._analytics_period_bounds("monthly")
        result = AnalyticsProviderEngine(tile, *period).evaluate()
        self.assertEqual(result["payload"], {"provider": "manual"})
        self.assertFalse(result["drilldown_model"])

    def test_31_kpi_feed_exposes_cached_aggregate_only(self):
        tile = self.activate(self.make_tile(code="test.provider.feed", manual_value=77.0))
        tile.with_user(self.manager)._generate_snapshot(*tile._analytics_period_bounds("monthly"))
        payload = self.env["onehr.analytics.tile"].with_user(self.analyst).onehr_analytics_kpi_feed(self.company)
        item = next(row for row in payload if row["code"] == tile.code)
        self.assertNotIn("domain_expression", item)
        self.assertNotIn("source_payload_json", item)
        self.assertEqual(item["value"], 77.0)

    def test_32_service_provider_requires_known_metric(self):
        tile = self.make_tile(code="test.provider.service", provider_mode="service")
        with self.assertRaises(ValidationError):
            tile._validate_provider_configuration()

    def test_33_cron_generates_due_daily_manual_snapshot(self):
        tile = self.activate(self.make_tile(
            code="test.provider.cron",
            snapshot_frequency="daily",
            manual_value=55.0,
        ))
        self.env["onehr.analytics.tile"]._cron_generate_due_snapshots()
        self.assertTrue(self.env["onehr.kpi.snapshot"].search_count([("tile_id", "=", tile.id)]))

    def test_34_service_contracts_remain_soft(self):
        optional_models = {
            "onehr.appraisal.form": "onehr_appraisal_kpi_snapshot",
            "onehr.learning.session": "onehr_learning_kpi_snapshot",
            "onehr.talent.pool": "onehr_career_kpi_snapshot",
        }
        for model_name, method_name in optional_models.items():
            if self.env.registry.get(model_name):
                self.assertTrue(hasattr(self.env[model_name], method_name))
