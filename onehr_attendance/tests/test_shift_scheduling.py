from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRAttendanceCommon


@tagged("post_install", "-at_install", "onehr_attendance")
class TestShiftScheduling(OneHRAttendanceCommon):
    def test_01_shift_code_normalization_and_night_interval(self):
        shift = self.make_shift(code="night", start_hour=22.0, end_hour=6.0, spans_next_day=True)
        self.assertEqual(shift.code, "NIGHT")
        start, end = shift._planned_interval_utc(self.today)
        self.assertEqual((end - start).total_seconds() / 3600.0, 8.0)

    def test_02_same_day_invalid_hours_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_shift(code="BAD-HOURS", start_hour=17.0, end_hour=8.0, spans_next_day=False)

    def test_03_active_shift_code_effective_overlap_is_rejected(self):
        first = self.activate_shift(self.make_shift(code="OVERLAP", valid_to=self.today + timedelta(days=20)))
        second = self.make_shift(code="OVERLAP", valid_from=self.today + timedelta(days=5))
        with self.assertRaises(ValidationError):
            second.with_user(self.manager).action_activate()
        self.assertEqual(first.state, "active")

    def test_04_pattern_cycle_resolves_shift_and_off_day(self):
        day = self.activate_shift(self.make_shift(code="D"))
        night = self.activate_shift(self.make_shift(code="N", start_hour=22, end_hour=6, spans_next_day=True))
        pattern = self.make_pattern(day | night, cycle_codes="D,OFF,N")
        pattern.with_user(self.manager).action_activate()
        self.assertEqual(pattern._shift_for_date(self.today), day)
        self.assertFalse(pattern._shift_for_date(self.today + timedelta(days=1)))
        self.assertEqual(pattern._shift_for_date(self.today + timedelta(days=2)), night)

    def test_05_pattern_unknown_token_is_rejected(self):
        shift = self.make_shift(code="D")
        with self.assertRaises(ValidationError):
            self.make_pattern(shift, cycle_codes="D,UNKNOWN")

    def test_06_schedule_requires_exactly_one_source(self):
        shift = self.make_shift(code="SRC")
        pattern = self.make_pattern(shift, code="SRC-PAT", cycle_codes="SRC")
        with self.assertRaises(ValidationError):
            self.make_schedule()
        with self.assertRaises(ValidationError):
            self.make_schedule(shift=shift, pattern=pattern)

    def test_07_employee_schedule_effective_overlap_is_rejected(self):
        shift = self.activate_shift(self.make_shift(code="SCHED-A"))
        first = self.make_schedule(shift=shift)
        with self.assertRaises(ValidationError):
            self.make_schedule(shift=shift, valid_from=first.valid_from + timedelta(days=1))

    def test_08_default_shift_resolver_prefers_location_specific_policy(self):
        generic = self.activate_shift(self.make_shift(code="GEN", priority=100))
        scoped = self.activate_shift(self.make_shift(code="LOC", work_location_id=self.location.id, priority=1))
        resolved = self.env["onehr.shift"].with_user(self.officer).resolve_for_employee_date(self.employee, self.today)
        self.assertEqual(resolved, scoped)
        self.assertNotEqual(resolved, generic)

    def test_09_missing_punch_detection_is_idempotent(self):
        shift = self.activate_shift(self.make_shift(code="MISS"))
        schedule = self.activate_schedule(self.make_schedule(shift=shift, valid_from=self.today - timedelta(days=30)))
        day = self.today - timedelta(days=2)
        first = schedule.with_user(self.manager)._detect_missing_punch_for_date(day)
        second = schedule.with_user(self.manager)._detect_missing_punch_for_date(day)
        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(first.exception_type, "missing_in")
        self.assertEqual(first.severity, "critical")

    def test_10_state_is_governed_not_directly_writable(self):
        shift = self.make_shift(code="STATE")
        with self.assertRaises(AccessError):
            shift.with_user(self.manager).write({"state": "active"})
