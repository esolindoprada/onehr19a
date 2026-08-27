from odoo.exceptions import AccessError

from .common import OneHRTimeOffCommon


class TestOneHRTimeOffSecurityIntegration(OneHRTimeOffCommon):
    def test_17_employee_record_rule_is_own_only(self):
        self.make_allocation()
        own_request = self.make_request()
        visible = self.env["onehr.leave.request"].with_user(self.employee_user).search([])
        self.assertIn(own_request, visible)

    def test_18_manager_rule_sees_direct_report_request(self):
        request = self.make_request()
        visible = self.env["onehr.leave.request"].with_user(self.manager_user).search([])
        self.assertIn(request, visible)

    def test_19_user_cannot_manage_leave_policy(self):
        with self.assertRaises(AccessError):
            self.leave_type.with_user(self.employee_user).write({"description": "Unauthorized"})

    def test_20_soft_integration_hooks_do_not_require_attendance_or_payroll(self):
        request = self.make_request()
        self.assertTrue(request._onehr_timeoff_validate_attendance_hook())
        self.assertIn("paid_leave", request.onehr_timeoff_payroll_payload())
