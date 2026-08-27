from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRAttendanceCommon


@tagged("post_install", "-at_install", "onehr_attendance")
class TestAttendanceWorkflow(OneHRAttendanceCommon):
    def test_11_ingestion_service_is_idempotent(self):
        shift = self.activate_shift(self.make_shift(code="INGEST"))
        start, end = shift._planned_interval_utc(self.today)
        payload = {
            "employee_id": self.employee.id,
            "check_in": start,
            "check_out": end,
            "source_channel": "api",
            "source_system": "DEVICE-A",
            "external_reference": "DEVICE-A-001",
        }
        first = self.env["hr.attendance"].with_user(self.officer).onehr_ingest_interval(payload)
        second = self.env["hr.attendance"].with_user(self.officer).onehr_ingest_interval(payload)
        self.assertEqual(first, second)
        self.assertEqual(first.onehr_source_system, "DEVICE-A")

    def test_12_ingestion_rejects_invalid_interval(self):
        shift = self.activate_shift(self.make_shift(code="INGEST-BAD"))
        start, _end = shift._planned_interval_utc(self.today)
        with self.assertRaises(ValidationError):
            self.env["hr.attendance"].with_user(self.officer).onehr_ingest_interval({
                "employee_id": self.employee.id,
                "check_in": start,
                "check_out": start - timedelta(minutes=1),
                "source_system": "BAD",
                "external_reference": "BAD-001",
            })

    def test_13_late_early_rounding_and_shift_resolution(self):
        shift = self.activate_shift(self.make_shift(
            code="LATE", late_grace_minutes=5, early_leave_grace_minutes=5, rounding_minutes="15"
        ))
        schedule = self.activate_schedule(self.make_schedule(shift=shift))
        attendance = self.make_attendance_for_shift(shift, start_delta=20, end_delta=-20)
        attendance.with_user(self.officer).action_onehr_recalculate()
        self.assertEqual(attendance.onehr_shift_assignment_id, schedule)
        self.assertEqual(attendance.onehr_shift_id, shift)
        self.assertEqual(attendance.onehr_exception_state, "late_early")
        self.assertAlmostEqual(attendance.onehr_late_minutes, 15.0)
        self.assertAlmostEqual(attendance.onehr_early_leave_minutes, 15.0)
        self.assertTrue(attendance.onehr_rounded_worked_hours > 0)

    def test_14_incomplete_attendance_requires_review_and_cannot_confirm(self):
        shift = self.activate_shift(self.make_shift(code="INCOMPLETE"))
        start, _end = shift._planned_interval_utc(self.today)
        attendance = self.env["hr.attendance"].with_user(self.officer).create({
            "employee_id": self.employee.id,
            "check_in": start,
            "onehr_source_channel": "manual",
        })
        self.assertTrue(attendance.onehr_requires_review)
        self.assertEqual(attendance.onehr_exception_state, "incomplete")
        with self.assertRaises(UserError):
            attendance.with_user(self.officer).action_onehr_confirm()

    def test_15_confirm_creates_exception_evidence_and_freezes_facts(self):
        shift = self.activate_shift(self.make_shift(code="CONFIRM"))
        self.activate_schedule(self.make_schedule(shift=shift))
        attendance = self.make_attendance_for_shift(shift, start_delta=20)
        attendance.with_user(self.officer).action_onehr_confirm()
        self.assertEqual(attendance.onehr_processing_state, "confirmed")
        self.assertTrue(attendance.onehr_exception_ids.filtered(lambda rec: rec.exception_type == "late"))
        with self.assertRaises(AccessError):
            attendance.with_user(self.manager).write({"check_in": attendance.check_in + timedelta(minutes=1)})

    def test_16_confirmed_attendance_can_reset_but_posted_cannot(self):
        shift = self.activate_shift(self.make_shift(code="RESET"))
        attendance = self.make_attendance_for_shift(shift)
        attendance.with_user(self.officer).action_onehr_confirm()
        attendance.with_user(self.manager).action_onehr_reset_draft()
        self.assertEqual(attendance.onehr_processing_state, "draft")
        attendance.with_user(self.officer).action_onehr_confirm()
        self.approve_native_overtime_if_needed(attendance)
        attendance.with_user(self.manager).action_onehr_post()
        self.assertEqual(attendance.onehr_processing_state, "posted")
        with self.assertRaises(UserError):
            attendance.with_user(self.manager).action_onehr_reset_draft()

    def test_17_posted_attendance_cannot_be_deleted(self):
        shift = self.activate_shift(self.make_shift(code="DELETE"))
        attendance = self.make_attendance_for_shift(shift)
        attendance.with_user(self.officer).action_onehr_confirm()
        self.approve_native_overtime_if_needed(attendance)
        attendance.with_user(self.manager).action_onehr_post()
        with self.assertRaises(AccessError):
            attendance.with_user(self.manager).unlink()

    def test_18_critical_exception_blocks_post_until_resolved(self):
        shift = self.activate_shift(self.make_shift(code="CRITICAL", geofence_radius_m=100, work_location_id=self.location.id))
        attendance = self.make_attendance_for_shift(
            shift,
            in_latitude=-7.0,
            in_longitude=107.0,
        )
        attendance.with_user(self.officer).action_onehr_confirm()
        critical = attendance.onehr_exception_ids.filtered(lambda rec: rec.severity == "critical")
        self.assertTrue(critical)
        with self.assertRaises(UserError):
            attendance.with_user(self.manager).action_onehr_post()
        critical.with_user(self.officer).write({"resolution_reason": "Verified legitimate remote check-in"})
        critical.with_user(self.officer).action_resolve()
        self.approve_native_overtime_if_needed(attendance)
        attendance.with_user(self.manager).action_onehr_post()
        self.assertEqual(attendance.onehr_processing_state, "posted")
