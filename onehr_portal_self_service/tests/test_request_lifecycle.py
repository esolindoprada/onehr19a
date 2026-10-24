
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRPortalCommon


@tagged("post_install", "-at_install", "onehr_portal_self_service")
class TestPortalRequestLifecycle(OneHRPortalCommon):
    def test_01_exact_portal_business_models_present(self):
        for model_name in (
            "onehr.portal.request.type",
            "onehr.portal.request.stage",
            "onehr.portal.request",
        ):
            self.assertIn(model_name, self.env)
        self.assertNotIn("onehr_portal_self_service.onehr_portal_self_service", self.env)

    def test_02_employee_creates_own_draft(self):
        record = self.make_request()
        self.assertEqual(record.employee_user_id, self.employee_user)
        self.assertEqual(record.state, "draft")
        self.assertTrue(record.name.startswith("HRSS/"))

    def test_03_submission_sets_manager_review_and_sla(self):
        record = self.submit_request()
        self.assertEqual(record.state, "manager_review")
        self.assertTrue(record.submitted_at)
        self.assertTrue(record.sla_deadline)

    def test_04_manager_approval_routes_to_hr(self):
        record = self.submit_request()
        record.with_user(self.manager_user).action_manager_approve("Approved by manager")
        self.assertEqual(record.state, "hr_review")
        self.assertEqual(record.manager_decision_by_id, self.manager_user)

    def test_05_hr_approval_processing_completion(self):
        record = self.submit_request()
        record.with_user(self.manager_user).action_manager_approve()
        record.with_user(self.hr_user).action_hr_approve("HR approved")
        self.assertEqual(record.state, "approved")
        record.with_user(self.hr_user).action_start_processing()
        self.assertEqual(record.state, "processing")
        record.with_user(self.hr_user).action_complete()
        self.assertEqual(record.state, "done")
        self.assertTrue(record.completed_at)

    def test_06_manager_rejection_requires_note(self):
        record = self.submit_request()
        with self.assertRaises(ValidationError):
            record.with_user(self.manager_user).action_manager_reject("")
        record.with_user(self.manager_user).action_manager_reject("Not supported")
        self.assertEqual(record.state, "rejected")

    def test_07_hr_rejection_requires_note(self):
        request_type = self.make_type(manager_approval_required=False)
        record = self.submit_request(request_type=request_type)
        self.assertEqual(record.state, "hr_review")
        with self.assertRaises(ValidationError):
            record.with_user(self.hr_user).action_hr_reject("")

    def test_08_employee_can_cancel_open_request(self):
        record = self.submit_request()
        record.with_user(self.employee_user).action_cancel()
        self.assertEqual(record.state, "cancelled")

    def test_09_employee_cannot_cancel_approved_request(self):
        request_type = self.make_type(manager_approval_required=False)
        record = self.submit_request(request_type=request_type)
        record.with_user(self.hr_user).action_hr_approve()
        with self.assertRaises(AccessError):
            record.with_user(self.employee_user).action_cancel()

    def test_10_completed_request_cannot_restart(self):
        request_type = self.make_type(
            manager_approval_required=False,
            hr_approval_required=False,
        )
        record = self.submit_request(request_type=request_type)
        record.with_user(self.hr_user).action_complete()
        with self.assertRaises(UserError):
            record.with_user(self.employee_user).action_submit()

    def test_11_profile_change_requires_hr_approval(self):
        with self.assertRaises(ValidationError):
            self.make_type(
                service_kind="profile_change",
                manager_approval_required=False,
                hr_approval_required=False,
            )

    def test_12_sla_values_are_validated(self):
        with self.assertRaises(ValidationError):
            self.make_type(sla_hours=12, reminder_hours_before=24)

