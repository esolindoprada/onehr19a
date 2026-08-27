import base64
import hashlib
import json

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRPayrollBridgeCommon


@tagged("post_install", "-at_install", "onehr_payroll_bridge")
class TestPayrollExportWorkflow(OneHRPayrollBridgeCommon):
    def test_08_export_sequence_and_configuration_defaults(self):
        config = self.make_config()
        export = self.make_export(config=config, employees=self.employee)
        self.assertNotEqual(export.name, "New")
        self.assertEqual(export.company_id, config.company_id)
        self.assertEqual(export.currency_id, config.currency_id)

    def test_09_employee_number_is_required_for_safe_export(self):
        export = self.make_export(employees=self.employee_without_number)
        with self.assertRaises(UserError):
            export.with_user(self.officer).action_generate_export()

    def test_10_generation_creates_csv_snapshots_and_sha256(self):
        export = self.generate_export(employees=self.employee | self.employee_2)
        self.assertTrue(export.export_file)
        self.assertTrue(export.export_filename.endswith(".csv"))
        self.assertEqual(export.employee_count, 2)
        rows = json.loads(export.source_rows_json)
        canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(export.export_sha256, expected_hash)
        self.assertEqual(len(export.export_sha256), 64)

    def test_11_generated_draft_scope_requires_explicit_reset_before_edit(self):
        export = self.generate_export(employees=self.employee)
        with self.assertRaises(AccessError):
            export.with_user(self.officer).write({"period_start": export.period_start})
        export.with_user(self.officer).action_reset_generation()
        self.assertFalse(export.generated)
        self.assertFalse(export.export_sha256)
        export.with_user(self.officer).write({"period_start": export.period_start})
        export.with_user(self.officer).action_generate_export()
        self.assertTrue(export.generated)

    def test_12_direct_state_write_is_blocked(self):
        export = self.make_export(employees=self.employee)
        with self.assertRaises(AccessError):
            export.with_user(self.manager).write({"state": "posted"})

    def test_13_post_requires_generated_source_package(self):
        export = self.make_export(employees=self.employee)
        with self.assertRaises(UserError):
            export.with_user(self.manager).action_post_to_payroll()

    def test_14_only_manager_can_post_generated_export(self):
        export = self.generate_export(employees=self.employee)
        with self.assertRaises(AccessError):
            export.with_user(self.officer).action_post_to_payroll()
        export.with_user(self.manager).action_post_to_payroll()
        self.assertEqual(export.state, "posted")
        self.assertTrue(export.posted_at)

    def test_15_posted_source_scope_is_immutable(self):
        export = self.post_export(employees=self.employee)
        with self.assertRaises(AccessError):
            export.with_user(self.manager).write({"period_end": fields.Date.today()})

    def test_16_download_action_requires_generated_file(self):
        export = self.make_export(employees=self.employee)
        with self.assertRaises(UserError):
            export.with_user(self.officer).action_download_export()
        export.with_user(self.officer).action_generate_export()
        action = export.with_user(self.officer).action_download_export()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("export_file", action["url"])

    def test_17_csv_manual_post_sets_external_reference_without_transport_secret(self):
        export = self.post_export(employees=self.employee)
        self.assertEqual(export.external_batch_reference, export.name)
        self.assertNotIn("token", export.config_snapshot_json.lower())
        self.assertNotIn("password", export.config_snapshot_json.lower())
