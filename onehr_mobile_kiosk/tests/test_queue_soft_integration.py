from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRKioskCommon


@tagged("post_install", "-at_install", "onehr_mobile_kiosk")
class TestKioskQueueSoftIntegration(OneHRKioskCommon):
    def test_17_offline_origin_is_retained_as_evidence(self):
        payload = self.punch_payload("OFFLINE-17", mode="check_in", offline=True)
        result = self.submit(payload)
        log = self.env["onehr.kiosk.log"].browse(result["log_id"])
        self.assertTrue(log.offline_event)

    def test_18_heartbeat_syncs_without_creating_attendance(self):
        before = self.env["hr.attendance"].search_count([])
        result = self.device.with_user(self.operator).kiosk_heartbeat(
            self.token, {"client_event_id": "HEARTBEAT-18"}
        )
        self.assertEqual(result["state"], "synced")
        self.assertEqual(self.env["hr.attendance"].search_count([]), before)

    def test_19_quick_timeoff_fails_safely_without_employee_self_service_authority(self):
        result = self.device.with_user(self.operator).kiosk_submit_timeoff(
            self.token,
            {
                "identity": self.employee.barcode,
                "credential_type": "qr",
                "client_event_id": "TIMEOFF-19",
                "event_at": fields.Datetime.to_string(fields.Datetime.now()),
                "leave_type_code": "ANNUAL",
                "date_from": fields.Date.to_string(fields.Date.context_today(self.device)),
                "date_to": fields.Date.to_string(fields.Date.context_today(self.device)),
                "reason": "Kiosk test",
            },
        )
        self.assertIn(result["state"], ("failed", "dead_letter"))
        self.assertFalse(result["target"])

    def test_20_employee_snapshot_handles_soft_timeoff_boundary(self):
        snapshot = self.device.with_user(self.operator).kiosk_employee_snapshot(
            self.token, self.employee.barcode
        )
        self.assertIn("timeoff", snapshot)
        self.assertFalse(snapshot["timeoff"]["available"])

    def test_21_max_attempts_moves_failed_event_to_dead_letter(self):
        self.device.with_user(self.admin).write({"max_sync_attempts": 1})
        result = self.device.with_user(self.operator).kiosk_submit_timeoff(
            self.token,
            {
                "identity": self.employee.barcode,
                "client_event_id": "DEAD-LETTER-21",
                "event_at": fields.Datetime.to_string(fields.Datetime.now()),
                "leave_type_code": "ANNUAL",
                "date_from": fields.Date.to_string(fields.Date.context_today(self.device)),
            },
        )
        self.assertEqual(result["state"], "dead_letter")

    def test_22_processed_log_cannot_be_deleted(self):
        result = self.submit(self.punch_payload("DELETE-GUARD-22", mode="check_in"))
        log = self.env["onehr.kiosk.log"].browse(result["log_id"])
        with self.assertRaises(AccessError):
            log.with_user(self.admin).unlink()

    def test_23_cross_company_employee_identifier_is_not_resolved(self):
        with self.assertRaises(ValidationError):
            self.device.with_user(self.operator).kiosk_employee_snapshot(
                self.token, self.other_employee.barcode
            )

    def test_24_no_parallel_onehr_attendance_transaction_model_is_created(self):
        self.assertNotIn("onehr.attendance", self.env)
        self.assertIn("hr.attendance", self.env)
