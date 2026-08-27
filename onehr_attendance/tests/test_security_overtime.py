from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRAttendanceCommon


@tagged("post_install", "-at_install", "onehr_attendance")
class TestSecurityOvertime(OneHRAttendanceCommon):
    def test_25_attendance_officer_does_not_gain_corehr_or_hr_officer_authority(self):
        self.assertTrue(self.officer.has_group("hr_attendance.group_hr_attendance_user"))
        self.assertFalse(self.officer.has_group("onehr_corehr.group_onehr_corehr_officer"))
        self.assertFalse(self.officer.has_group("hr.group_hr_user"))

    def test_26_supporting_employee_position_calendar_acl_is_read_only(self):
        Access = self.env["ir.model.access"]
        for model_name in ("hr.employee", "onehr.position", "resource.calendar"):
            rows = Access.search([
                ("model_id.model", "=", model_name),
                ("group_id", "=", self.group_officer.id),
            ])
            self.assertTrue(rows)
            self.assertTrue(any(row.perm_read for row in rows))
            self.assertFalse(any(row.perm_write or row.perm_create or row.perm_unlink for row in rows))

    def test_27_company_record_rule_hides_other_company_shift(self):
        other_shift = self.env["onehr.shift"].with_user(self.manager).create({
            "name": "Other Shift",
            "code": "OTHER",
            "company_id": self.other_company.id,
            "resource_calendar_id": self.other_company.resource_calendar_id.id,
            "timezone": "UTC",
            "start_hour": 8,
            "end_hour": 17,
            "valid_from": self.today,
        })
        visible = self.env["onehr.shift"].with_user(self.officer).search([("id", "=", other_shift.id)])
        self.assertFalse(visible)

    def test_28_native_overtime_contract_is_extended_not_duplicated(self):
        self.assertIn("hr.attendance.overtime.line", self.env)
        self.assertIn("hr.attendance.overtime.rule", self.env)
        self.assertIn("hr.attendance.overtime.ruleset", self.env)
        self.assertNotIn("onehr.attendance", self.env)
        self.assertIn("onehr_export_ready", self.env["hr.attendance.overtime.line"]._fields)
        self.assertIn("onehr_policy_code", self.env["hr.attendance.overtime.rule"]._fields)
        self.assertIn("onehr_policy_reference", self.env["hr.attendance.overtime.ruleset"]._fields)

    def test_29_overtime_ruleset_invalid_policy_interval_is_rejected(self):
        ruleset = self.env["hr.attendance.overtime.ruleset"].new({
            "onehr_valid_from": "2026-08-20",
            "onehr_valid_to": "2026-08-19",
        })
        with self.assertRaises(ValidationError):
            ruleset._check_onehr_policy_interval()
