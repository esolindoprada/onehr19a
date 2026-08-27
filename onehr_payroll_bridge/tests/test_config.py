import json
from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRPayrollBridgeCommon


@tagged("post_install", "-at_install", "onehr_payroll_bridge")
class TestPayrollBridgeConfig(OneHRPayrollBridgeCommon):
    def test_01_manager_can_create_configuration(self):
        config = self.make_config()
        self.assertEqual(config.company_id, self.company)
        self.assertEqual(config.code, "PAY-MAIN")

    def test_02_officer_cannot_create_configuration(self):
        with self.assertRaises(AccessError):
            self.env["onehr.payroll.bridge.config"].with_user(self.officer).create(
                {
                    "name": "Unauthorized",
                    "code": "NOPE",
                    "company_id": self.company.id,
                    "external_system_code": "VENDOR",
                }
            )

    def test_03_schedule_day_must_be_one_to_twenty_eight(self):
        with self.assertRaises(ValidationError):
            self.make_config(code="PAY-BAD-DAY", export_schedule_day=29)

    def test_04_mapping_must_be_valid_json_object(self):
        with self.assertRaises(ValidationError):
            self.make_config(code="PAY-BAD-JSON", export_field_mapping="{bad json")

    def test_05_duplicate_external_headers_are_rejected(self):
        bad_mapping = json.dumps(
            {
                "employee_number": "employee",
                "employee_name": "employee",
            }
        )
        with self.assertRaises(ValidationError):
            self.make_config(code="PAY-DUP-HEADER", export_field_mapping=bad_mapping)

    def test_06_used_configuration_cannot_be_deleted(self):
        config = self.make_config()
        self.make_export(config=config, employees=self.employee)
        with self.assertRaises(AccessError):
            config.with_user(self.manager).unlink()

    def test_07_scheduler_prepares_draft_only(self):
        config = self.make_config(
            code="PAY-SCHEDULED",
            export_schedule_enabled=True,
            export_schedule_day=20,
        )
        with patch("odoo.fields.Date.context_today", return_value=date(2026, 8, 20)):
            config._cron_prepare_scheduled_exports()
        export = self.env["onehr.payroll.export"].search(
            [("config_id", "=", config.id)],
            limit=1,
        )
        self.assertTrue(export)
        self.assertEqual(export.state, "draft")
        self.assertFalse(export.generated)
