from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OffboardingCase


@tagged("post_install", "-at_install", "onehr_retirement_offboarding")
class TestSecurityAndEvidence(OffboardingCase):
    def test_01_four_application_groups_exist(self):
        for xmlid in (
            "group_onehr_offboarding_task_owner",
            "group_onehr_offboarding_officer",
            "group_onehr_offboarding_manager",
            "group_onehr_offboarding_admin",
        ):
            self.assertTrue(self.env.ref(f"onehr_retirement_offboarding.{xmlid}"))

    def test_02_offboarding_admin_does_not_imply_system_admin(self):
        group = self.env.ref("onehr_retirement_offboarding.group_onehr_offboarding_admin")
        self.assertNotIn(self.env.ref("base.group_system"), group.trans_implied_ids)

    def test_03_task_owner_implies_onehr_security_user(self):
        group = self.env.ref("onehr_retirement_offboarding.group_onehr_offboarding_task_owner")
        self.assertIn(self.env.ref("onehr_security.group_onehr_security_user"), group.trans_implied_ids)

    def test_04_company_rules_exist_for_all_persistent_models(self):
        names = {
            "Offboarding Case — company boundary",
            "Offboarding Checklist — company boundary",
            "Clearance Item — global/company boundary",
            "Exit Interview — company boundary",
        }
        found = set(self.env["ir.rule"].sudo().search([("name", "in", list(names))]).mapped("name"))
        self.assertEqual(found, names)

    def test_05_res_users_offboarding_evidence_is_guarded(self):
        with self.assertRaises(AccessError):
            self.env.user.write({"onehr_offboarding_access_reference": "BAD-DIRECT-WRITE"})

    def test_06_case_access_state_is_guarded(self):
        with self.assertRaises(ValidationError):
            self.case.write({"access_state": "revoked"})

    def test_07_case_final_benefit_state_is_guarded(self):
        with self.assertRaises(ValidationError):
            self.case.write({"final_benefit_state": "confirmed"})

    def test_08_case_contract_state_is_guarded(self):
        with self.assertRaises(ValidationError):
            self.case.write({"contract_termination_state": "terminated"})

    def test_09_closed_evidence_guard_is_present(self):
        self.case.with_context(onehr_offboarding_state_action=True, onehr_offboarding_evidence_action=True).write({"state": "closed"})
        with self.assertRaises(ValidationError):
            self.case.write({"document_reference": "CHANGED"})

    def test_10_checklist_actor_evidence_direct_write_is_blocked(self):
        task = self._task()
        with self.assertRaises(ValidationError):
            task.write({"completed_by_id": self.env.user.id})
