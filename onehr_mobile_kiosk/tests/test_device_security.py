from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRKioskCommon


@tagged("post_install", "-at_install", "onehr_mobile_kiosk")
class TestKioskDeviceSecurity(OneHRKioskCommon):
    def test_01_raw_device_token_is_never_persisted(self):
        self.assertTrue(self.device.token_hash)
        self.assertNotEqual(self.device.token_hash, self.token)
        self.assertEqual(self.device.token_last4, self.token[-4:])
        self.assertNotIn(self.token, repr(self.device.read()[0]))

    def test_02_token_validation_and_rotation_invalidates_old_token(self):
        self.assertTrue(self.device.with_user(self.operator)._token_is_valid(self.token))
        new_token = self.device.with_user(self.admin)._issue_token()
        self.assertFalse(self.device.with_user(self.operator)._token_is_valid(self.token))
        self.assertTrue(self.device.with_user(self.operator)._token_is_valid(new_token))

    def test_03_expired_token_is_rejected(self):
        token = self.device.with_user(self.admin)._issue_token()
        self.device.with_user(self.admin)._write_governed({
            "token_expires_at": fields.Datetime.now() - timedelta(seconds=1),
        })
        self.assertFalse(self.device.with_user(self.operator)._token_is_valid(token))
        with self.assertRaises(AccessError):
            self.device.with_user(self.operator).kiosk_bootstrap(token)

    def test_04_operator_cannot_reconfigure_device(self):
        with self.assertRaises(AccessError):
            self.device.with_user(self.operator).write({"name": "Unauthorized Rename"})

    def test_05_other_service_user_cannot_see_device(self):
        visible = self.env["onehr.kiosk.device"].with_user(self.other_operator).search([
            ("id", "=", self.device.id)
        ])
        self.assertFalse(visible)

    def test_06_admin_company_scope_can_manage_both_allowed_companies(self):
        visible = self.env["onehr.kiosk.device"].with_user(self.admin).search([
            ("id", "in", [self.device.id, self.other_device.id])
        ])
        self.assertEqual(set(visible.ids), {self.device.id, self.other_device.id})

    def test_07_activation_requires_service_user_company_alignment(self):
        wrong = self.env["onehr.kiosk.device"].with_user(self.admin)
        with self.assertRaises(ValidationError):
            wrong.create({
                "name": "Bad Company Device",
                "company_id": self.company.id,
                "service_user_id": self.other_operator.id,
            })

    def test_08_kiosk_operator_does_not_gain_general_hr_officer_authority(self):
        self.assertTrue(self.operator.has_group("hr_attendance.group_hr_attendance_user"))
        self.assertFalse(self.operator.has_group("hr.group_hr_user"))
