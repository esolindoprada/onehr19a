from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRKioskCommon


@tagged("post_install", "-at_install", "onehr_mobile_kiosk")
class TestKioskPunchSync(OneHRKioskCommon):
    def test_09_checkin_creates_canonical_hr_attendance(self):
        result = self.submit(self.punch_payload("PUNCH-09", mode="check_in"))
        self.assertEqual(result["state"], "synced")
        attendance = self.env["hr.attendance"].browse(result["attendance_id"])
        self.assertEqual(attendance.employee_id, self.employee)
        self.assertEqual(attendance.onehr_source_channel, "kiosk")
        self.assertEqual(attendance.onehr_source_system, "ONEHR_KIOSK")
        self.assertEqual(attendance.onehr_device_reference, self.device.code)

    def test_10_checkout_updates_same_open_attendance(self):
        start = fields.Datetime.now() - timedelta(hours=8)
        first = self.submit(self.punch_payload("PUNCH-10-IN", mode="check_in", event_at=start))
        second = self.submit(self.punch_payload("PUNCH-10-OUT", mode="check_out"))
        self.assertEqual(first["attendance_id"], second["attendance_id"])
        attendance = self.env["hr.attendance"].browse(second["attendance_id"])
        self.assertTrue(attendance.check_out)

    def test_11_auto_toggle_checks_in_then_out(self):
        start = fields.Datetime.now() - timedelta(hours=1)
        first = self.submit(self.punch_payload("PUNCH-11-A", mode="auto", event_at=start))
        second = self.submit(self.punch_payload("PUNCH-11-B", mode="auto"))
        self.assertEqual(first["attendance_id"], second["attendance_id"])
        self.assertTrue(self.env["hr.attendance"].browse(second["attendance_id"]).check_out)

    def test_12_duplicate_client_event_is_idempotent(self):
        payload = self.punch_payload("PUNCH-IDEMPOTENT-12", mode="check_in")
        first = self.submit(payload)
        second = self.submit(payload)
        self.assertEqual(first["log_id"], second["log_id"])
        self.assertEqual(first["attendance_id"], second["attendance_id"])

    def test_13_geofence_block_retains_evidence_without_attendance(self):
        self.device.with_user(self.admin).write({
            "geolocation_required": True,
            "geofence_policy": "block",
            "geofence_radius_m": 100,
        })
        result = self.submit(self.punch_payload(
            "PUNCH-GEOFENCE-13",
            mode="check_in",
            latitude=-7.0,
            longitude=110.0,
        ))
        self.assertEqual(result["state"], "blocked")
        self.assertFalse(result["attendance_id"])
        log = self.env["onehr.kiosk.log"].browse(result["log_id"])
        self.assertEqual(log.geofence_status, "blocked")

    def test_14_geofence_inside_allows_attendance(self):
        self.device.with_user(self.admin).write({
            "geolocation_required": True,
            "geofence_policy": "block",
            "geofence_radius_m": 100,
        })
        result = self.submit(self.punch_payload(
            "PUNCH-GEOFENCE-14",
            mode="check_in",
            latitude=-8.6500,
            longitude=115.2167,
        ))
        self.assertEqual(result["state"], "synced")
        self.assertTrue(result["attendance_id"])

    def test_15_raw_employee_credential_not_persisted_in_server_summary(self):
        result = self.submit(self.punch_payload("PUNCH-PRIVACY-15", mode="check_in"))
        log = self.env["onehr.kiosk.log"].browse(result["log_id"])
        evidence = " ".join([
            log.request_summary or "",
            log.error_message or "",
            log.payload_hash or "",
        ])
        self.assertNotIn(self.employee.barcode, evidence)

    def test_16_synced_event_evidence_is_immutable(self):
        result = self.submit(self.punch_payload("PUNCH-IMMUTABLE-16", mode="check_in"))
        log = self.env["onehr.kiosk.log"].browse(result["log_id"])
        with self.assertRaises(AccessError):
            log.with_user(self.operator).write({"event_type": "system"})
