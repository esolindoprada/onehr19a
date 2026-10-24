from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import AnalyticsCase


@tagged("post_install", "-at_install", "onehr_analytics")
class TestAnalyticsTileLifecycle(AnalyticsCase):
    def test_01_model_inventory_is_registered(self):
        self.assertTrue(self.env.registry.get("onehr.analytics.tile"))
        self.assertTrue(self.env.registry.get("onehr.kpi.snapshot"))
        self.assertTrue(self.env.registry.get("onehr.mixin.analytics"))

    def test_02_tile_starts_draft(self):
        tile = self.make_tile(code="test.lifecycle.draft")
        self.assertEqual(tile.state, "draft")

    def test_03_activate_manual_tile(self):
        tile = self.make_tile(code="test.lifecycle.active")
        tile.with_user(self.manager).action_activate()
        self.assertEqual(tile.state, "active")

    def test_04_pause_and_resume(self):
        tile = self.activate(self.make_tile(code="test.lifecycle.pause"))
        tile.with_user(self.manager).action_pause()
        self.assertEqual(tile.state, "paused")
        tile.with_user(self.manager).action_resume()
        self.assertEqual(tile.state, "active")

    def test_05_retired_tile_cannot_reactivate(self):
        tile = self.activate(self.make_tile(code="test.lifecycle.retire"))
        tile.with_user(self.manager).action_retire()
        self.assertEqual(tile.state, "retired")
        with self.assertRaises(UserError):
            tile.with_user(self.manager).action_activate()

    def test_06_direct_state_write_is_blocked(self):
        tile = self.make_tile(code="test.lifecycle.direct")
        with self.assertRaises(AccessError):
            tile.with_user(self.manager).write({"state": "active"})

    def test_07_active_provider_identity_is_frozen(self):
        tile = self.activate(self.make_tile(code="test.lifecycle.identity"))
        with self.assertRaises(AccessError):
            tile.with_user(self.manager).write({"provider_mode": "model_aggregate"})

    def test_08_code_is_normalized(self):
        tile = self.make_tile(code="Test.NORMALIZED")
        self.assertEqual(tile.code, "test.normalized")

    def test_09_invalid_code_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_tile(code="Bad KPI Code")

    def test_10_high_bad_threshold_order(self):
        with self.assertRaises(ValidationError):
            self.make_tile(
                code="test.threshold.high",
                threshold_direction="high_bad",
                warning_threshold=90.0,
                critical_threshold=80.0,
            )

    def test_11_low_bad_threshold_order(self):
        with self.assertRaises(ValidationError):
            self.make_tile(
                code="test.threshold.low",
                threshold_direction="low_bad",
                warning_threshold=80.0,
                critical_threshold=90.0,
            )

    def test_12_analyst_can_toggle_only_own_favorite(self):
        tile = self.make_tile(code="test.favorite.own")
        tile.with_user(self.analyst).action_toggle_favorite()
        self.assertIn(self.analyst, tile.favorite_user_ids)
        with self.assertRaises(AccessError):
            tile.with_user(self.analyst).write({
                "favorite_user_ids": [Command.link(self.admin.id)]
            })
