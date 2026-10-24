
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRCareerSuccessionCommon


@tagged("post_install", "-at_install", "onehr_career_succession")
class TestSuccessionSecurityIntegrations(OneHRCareerSuccessionCommon):
    def test_17_plain_user_has_no_custom_model_access(self):
        with self.assertRaises(AccessError):
            self.env["onehr.talent.pool"].with_user(self.plain_user).search([])

    def test_18_succession_plan_requires_candidate_before_proposal(self):
        talent = self.make_talent()
        plan = self.make_plan(talent=talent)
        plan.with_user(self.hrbp_user).write(
            {"candidate_talent_ids": [(5, talent.id)]}
        )
        with self.assertRaises(UserError):
            plan.with_user(self.hrbp_user).action_propose()

    def test_19_succession_approval_requires_approved_talent(self):
        talent = self.make_talent()
        plan = self.make_plan(talent=talent)
        plan.with_user(self.hrbp_user).action_propose()
        with self.assertRaises(UserError):
            plan.with_user(self.talent_manager).action_approve()

    def test_20_succession_workflow_to_active(self):
        talent = self.activate_talent(self.make_talent())
        plan = self.make_plan(talent=talent)
        plan.with_user(self.hrbp_user).action_propose()
        plan.with_user(self.talent_manager).action_approve()
        plan.with_user(self.talent_manager).action_activate()
        self.assertEqual(plan.state, "active")
        self.assertGreater(plan.coverage_percent, 0.0)

    def test_21_primary_successor_must_be_candidate(self):
        talent = self.make_talent()
        other = self.make_talent(pool_code=f"OTHER-{self._testMethodName}")
        with self.assertRaises(ValidationError):
            self.make_plan(
                talent=talent,
                primary_successor_id=other.id,
            )

    def test_22_kpi_snapshot_contract(self):
        talent = self.activate_talent(self.make_talent())
        plan = self.make_plan(talent=talent)
        plan.with_user(self.hrbp_user).action_propose()
        plan.with_user(self.talent_manager).action_approve()
        plan.with_user(self.talent_manager).action_activate()

        payload = self.env["onehr.talent.pool"].with_user(
            self.talent_manager
        ).onehr_career_kpi_snapshot(self.company)
        self.assertIn("succession_coverage_percent", payload)
        self.assertIn("average_bench_strength", payload)
        self.assertIn("average_readiness", payload)

    def test_23_bi_payload_contains_talent_readiness(self):
        talent = self.make_talent()
        payload = talent.with_user(
            self.talent_manager
        ).onehr_talent_bi_payload()[0]
        self.assertIn("readiness_score", payload)
        self.assertIn("nine_box_position", payload)
        self.assertIn("target_position_id", payload)

    def test_24_plan_risk_reacts_to_coverage(self):
        talent = self.activate_talent(self.make_talent())
        plan = self.make_plan(talent=talent, target_coverage=2)
        self.assertLess(plan.coverage_percent, 100.0)
        self.assertGreater(plan.risk_index, 0.0)

