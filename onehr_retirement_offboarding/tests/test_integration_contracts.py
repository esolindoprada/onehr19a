from odoo.tests import tagged

from .common import OffboardingCase


@tagged("post_install", "-at_install", "onehr_retirement_offboarding")
class TestIntegrationContracts(OffboardingCase):
    def test_01_workflow_approval_mixin_is_inherited(self):
        self.assertIn("onehr.mixin.approvable", self.env["onehr.offboarding"]._inherit)

    def test_02_audit_mixin_is_inherited(self):
        self.assertIn("onehr.mixin.audit", self.env["onehr.offboarding"]._inherit)

    def test_03_portal_payload_is_sanitized(self):
        payload = self.case.onehr_offboarding_portal_payload()
        self.assertNotIn("exit_reason_notes", payload)
        self.assertNotIn("final_benefit_amount", payload)

    def test_04_api_payload_is_structured_without_transport(self):
        payload = self.case.onehr_offboarding_api_payload()
        self.assertEqual(payload["reference"], self.case.name)
        self.assertIn("access_state", payload)

    def test_05_document_payload_preserves_source_reference(self):
        payload = self.case.onehr_offboarding_document_payload()
        self.assertEqual(payload["source_model"], "onehr.offboarding")
        self.assertEqual(payload["source_res_id"], self.case.id)

    def test_06_payroll_payload_never_claims_to_calculate_amount(self):
        payload = self.case.onehr_offboarding_payroll_payload()
        self.assertFalse(payload["calculate_amount"])

    def test_07_access_revoke_payload_has_no_secret_material(self):
        payload = self.case.onehr_offboarding_access_revoke_payload()
        self.assertNotIn("password", payload)
        self.assertNotIn("token", payload)

    def test_08_analytics_snapshot_has_required_kpis(self):
        snapshot = self.Case.onehr_offboarding_kpi_snapshot(company=self.env.company)
        for key in ("case_count", "closed_count", "open_count", "overdue_task_count", "average_time_to_close_days"):
            self.assertIn(key, snapshot)

    def test_09_employment_contract_is_runtime_soft_dependency(self):
        value = self.case._employment_contract_model()
        self.assertIn(value, (False, "onehr.contract"))

    def test_10_no_public_controller_model_is_required(self):
        self.assertFalse(self.env.registry.get("onehr_retirement_offboarding.onehr_retirement_offboarding"))
