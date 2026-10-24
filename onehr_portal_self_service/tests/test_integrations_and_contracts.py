
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRPortalCommon


@tagged("post_install", "-at_install", "onehr_portal_self_service")
class TestPortalIntegrationsAndContracts(OneHRPortalCommon):
    def test_22_generic_service_is_not_applicable_integration(self):
        request_type = self.make_type(
            manager_approval_required=False,
            hr_approval_required=False,
        )
        record = self.submit_request(request_type=request_type)
        self.assertEqual(record.integration_status, "not_applicable")

    def test_23_profile_payload_is_safe_display_subset(self):
        payload = self.employee_user.onehr_portal_profile_payload()
        self.assertEqual(payload["employee_name"], self.employee.name)
        self.assertIn("employee_number", payload)
        self.assertNotIn("private_email", payload)
        self.assertNotIn("identification_id", payload)

    def test_24_profile_change_payload_validates_required_changes(self):
        request_type = self.make_type(
            service_kind="profile_change",
            manager_approval_required=False,
            hr_approval_required=True,
        )
        record = self.make_request(request_type=request_type)
        with self.assertRaises(ValidationError):
            record.with_user(self.employee_user).action_submit()

    def test_25_timeoff_payload_requires_service_fields(self):
        request_type = self.make_type(service_kind="timeoff")
        record = self.make_request(request_type=request_type)
        with self.assertRaises(ValidationError):
            record.with_user(self.employee_user).action_submit()

    def test_26_learning_payload_requires_exact_session_reference(self):
        request_type = self.make_type(service_kind="learning")
        record = self.make_request(request_type=request_type)
        with self.assertRaises(ValidationError):
            record.with_user(self.employee_user).action_submit()

    def test_27_document_payload_requires_category_and_attachment(self):
        request_type = self.make_type(service_kind="document")
        record = self.make_request(request_type=request_type)
        with self.assertRaises(ValidationError):
            record.with_user(self.employee_user).action_submit()

    def test_28_only_hr_can_execute_downstream_integration(self):
        request_type = self.make_type(
            manager_approval_required=False,
            hr_approval_required=False,
        )
        record = self.submit_request(request_type=request_type)
        with self.assertRaises(AccessError):
            record.with_user(self.employee_user).action_execute_integration()

    def test_29_missing_soft_addon_does_not_become_hard_dependency(self):
        request_type = self.make_type(
            service_kind="learning",
            manager_approval_required=False,
            hr_approval_required=False,
        )
        record = self.make_request(
            request_type=request_type,
            learning_session_reference="SESSION-NOT-CONFIGURED",
        )
        record.with_user(self.employee_user).action_submit()
        if not self.env.registry.get("onehr.learning.enrollment"):
            with self.assertRaises(UserError):
                record.with_user(self.hr_user).action_execute_integration()

    def test_30_dashboard_contract_has_request_metrics(self):
        self.make_request()
        payload = self.env["onehr.portal.request"].with_user(
            self.employee_user
        ).onehr_my_hr_dashboard_payload()
        self.assertIn("employee", payload)
        self.assertIn("request_metrics", payload)
        self.assertIn("integrations", payload)
        self.assertGreaterEqual(payload["request_metrics"]["total"], 1)
    def test_31_employee_final_approval_never_escalates_auto_execution(self):
        request_type = self.make_type(
            service_kind="learning",
            manager_approval_required=False,
            hr_approval_required=False,
            auto_execute_on_approval=True,
        )
        record = self.make_request(
            request_type=request_type,
            learning_session_reference="SESSION-DEFERRED-EMPLOYEE",
        )
        record.with_user(self.employee_user).action_submit()
        self.assertEqual(record.state, "approved")
        self.assertEqual(record.integration_status, "pending")
        self.assertIn("Portal HR", record.integration_message)

    def test_32_manager_final_approval_never_escalates_auto_execution(self):
        request_type = self.make_type(
            service_kind="learning",
            manager_approval_required=True,
            hr_approval_required=False,
            auto_execute_on_approval=True,
        )
        record = self.make_request(
            request_type=request_type,
            learning_session_reference="SESSION-DEFERRED-MANAGER",
        )
        record.with_user(self.employee_user).action_submit()
        self.assertEqual(record.state, "manager_review")
        record.with_user(self.manager_user).action_manager_approve()
        self.assertEqual(record.state, "approved")
        self.assertEqual(record.integration_status, "pending")
        self.assertIn("Portal HR", record.integration_message)


