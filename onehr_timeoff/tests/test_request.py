from datetime import timedelta

from odoo.exceptions import ValidationError

from .common import OneHRTimeOffCommon


class TestOneHRLeaveRequest(OneHRTimeOffCommon):
    def test_10_work_schedule_duration_is_positive(self):
        request = self.make_request()
        self.assertGreater(request.requested_days, 0.0)

    def test_11_auto_approval_reserves_entitlement(self):
        allocation = self.make_allocation(days=5.0)
        request = self.make_request()
        request.action_submit_for_approval()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.allocation_usage_json)
        self.assertLess(allocation.available_on(self.future_monday, include_future_reservations=True), 5.0)

    def test_12_insufficient_balance_blocks_submission(self):
        self.make_allocation(days=0.5)
        request = self.make_request(date_to=self.future_monday + timedelta(days=1))
        with self.assertRaises(ValidationError):
            request.action_submit_for_approval()

    def test_13_overlapping_request_is_rejected(self):
        self.make_allocation(days=10.0)
        first = self.make_request()
        first.action_submit_for_approval()
        second = self.make_request(reason="Overlapping request")
        with self.assertRaises(ValidationError):
            second.action_submit_for_approval()

    def test_14_half_day_request(self):
        self.make_allocation(days=2.0)
        request = self.make_request(half_day=True)
        self.assertEqual(request.requested_days, 0.5)
        request.action_submit_for_approval()
        self.assertEqual(request.state, "approved")

    def test_15_cancelled_approved_request_releases_reservation(self):
        allocation = self.make_allocation(days=5.0)
        request = self.make_request()
        request.action_submit_for_approval()
        reserved_balance = allocation.available_on(self.future_monday, include_future_reservations=True)
        request.with_user(self.hr_user).action_cancel()
        released_balance = allocation.available_on(self.future_monday, include_future_reservations=True)
        self.assertGreater(released_balance, reserved_balance)

    def test_16_payroll_payload_preserves_paid_unpaid_flag(self):
        request = self.make_request()
        payload = request.onehr_timeoff_payroll_payload()
        self.assertTrue(payload["paid_leave"])
        self.assertEqual(payload["request_no"], request.name)
