from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import AnalyticsCase


@tagged("post_install", "-at_install", "onehr_analytics")
class TestAnalyticsSnapshotSecurity(AnalyticsCase):
    def test_13_manual_snapshot_is_created(self):
        tile = self.activate(self.make_tile(code="test.snapshot.manual", manual_value=125.0))
        tile.with_user(self.manager).action_snapshot_now()
        snapshot = self.env["onehr.kpi.snapshot"].search([("tile_id", "=", tile.id)])
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot.value, 125.0)

    def test_14_same_period_snapshot_is_idempotent(self):
        tile = self.activate(self.make_tile(code="test.snapshot.idempotent", snapshot_frequency="daily"))
        first = tile.with_user(self.manager)._generate_snapshot(*tile._analytics_period_bounds("daily"))
        second = tile.with_user(self.manager)._generate_snapshot(*tile._analytics_period_bounds("daily"))
        self.assertEqual(first, second)

    def test_15_direct_snapshot_create_is_blocked(self):
        tile = self.make_tile(code="test.snapshot.direct")
        with self.assertRaises(AccessError):
            self.env["onehr.kpi.snapshot"].with_user(self.manager).create({
                "tile_id": tile.id,
                "company_id": self.company.id,
                "period_start": fields.Date.context_today(self.env.user),
                "period_end": fields.Date.context_today(self.env.user),
                "value": 1.0,
                "source_name": "forbidden",
            })

    def test_16_snapshot_business_fields_are_immutable(self):
        tile = self.make_tile(code="test.snapshot.immutable")
        snapshot = self.create_snapshot_evidence(tile)
        with self.assertRaises(AccessError):
            snapshot.with_user(self.manager).write({"value": 999.0})

    def test_17_snapshot_delete_is_blocked(self):
        tile = self.make_tile(code="test.snapshot.delete")
        snapshot = self.create_snapshot_evidence(tile)
        with self.assertRaises(AccessError):
            snapshot.with_user(self.admin).unlink()

    def test_18_controlled_archive_and_restore(self):
        tile = self.make_tile(code="test.snapshot.archive")
        snapshot = self.create_snapshot_evidence(tile)
        snapshot.with_user(self.manager).action_archive_evidence()
        self.assertTrue(snapshot.archived)
        snapshot.with_user(self.admin).action_restore_evidence()
        self.assertFalse(snapshot.archived)

    def test_19_warning_threshold_snapshot_status(self):
        tile = self.activate(self.make_tile(
            code="test.snapshot.warning",
            manual_value=90.0,
            threshold_direction="high_bad",
            warning_threshold=80.0,
            critical_threshold=100.0,
        ))
        snapshot = tile.with_user(self.manager)._generate_snapshot(*tile._analytics_period_bounds("monthly"))
        self.assertEqual(snapshot.status, "warning")

    def test_20_critical_threshold_snapshot_status(self):
        tile = self.activate(self.make_tile(
            code="test.snapshot.critical",
            manual_value=110.0,
            threshold_direction="high_bad",
            warning_threshold=80.0,
            critical_threshold=100.0,
        ))
        snapshot = tile.with_user(self.manager)._generate_snapshot(*tile._analytics_period_bounds("monthly"))
        self.assertEqual(snapshot.status, "critical")

    def test_21_company_rule_hides_other_company_tile(self):
        foreign = self.env["onehr.analytics.tile"].create({
            "name": "Foreign KPI",
            "code": "test.foreign.company",
            "company_id": self.other_company.id,
            "category": "custom",
            "provider_mode": "manual",
            "owner_user_id": self.env.user.id,
        })
        visible = self.env["onehr.analytics.tile"].with_user(self.analyst).search([("id", "=", foreign.id)])
        self.assertFalse(visible)

    def test_22_started_tile_with_snapshot_cannot_be_deleted(self):
        tile = self.make_tile(code="test.snapshot.tile.delete")
        self.create_snapshot_evidence(tile)
        with self.assertRaises(AccessError):
            tile.with_user(self.admin).unlink()

    def test_23_csv_export_generates_download_evidence(self):
        tile = self.make_tile(code="test.snapshot.csv")
        self.create_snapshot_evidence(tile)
        action = tile.with_user(self.manager).action_export_snapshot_csv()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(tile.export_file)
        self.assertTrue(tile.export_filename.endswith(".csv"))

    def test_24_retention_cron_archives_old_evidence(self):
        tile = self.make_tile(code="test.snapshot.retention", retention_months=1)
        old_date = fields.Date.context_today(self.env.user) - relativedelta(months=3)
        snapshot = self.create_snapshot_evidence(tile, period_start=old_date, period_end=old_date)
        self.env["onehr.analytics.tile"]._cron_archive_old_snapshots()
        self.assertTrue(snapshot.archived)
