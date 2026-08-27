from odoo.exceptions import AccessError, ValidationError

from .common import OneHRTimeOffCommon


class TestOneHRLeaveType(OneHRTimeOffCommon):
    def test_01_leave_type_activation(self):
        self.assertEqual(self.leave_type.state, "active")
        self.assertTrue(self.leave_type.active)

    def test_02_leave_type_unique_code_per_company(self):
        with self.assertRaises(Exception):
            self.env["onehr.leave.type"].with_user(self.hr_user).create({
                "name": "Duplicate", "code": self.leave_type.code,
                "company_id": self.company.id, "category": "annual",
            })

    def test_03_active_policy_is_frozen(self):
        with self.assertRaises(AccessError):
            self.leave_type.with_user(self.hr_user).write({"base_accrual_days": 99.0})

    def test_04_negative_policy_limit_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.leave.type"].with_user(self.hr_user).create({
                "name": "Invalid", "code": "INVALID-NEG",
                "company_id": self.company.id, "category": "special",
                "minimum_notice_days": -1,
            })
