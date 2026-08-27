from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRCareerSuccessionCommon


@tagged("post_install", "-at_install", "onehr_career_succession")
class TestTalentWorkflow(OneHRCareerSuccessionCommon):
    def test_09_talent_reference_sequence(self):
        talent = self.make_talent()
        self.assertNotEqual(talent.name, "New")

    def test_10_talent_readiness_composite(self):
        talent = self.make_talent(
            performance_score=80.0,
            potential_score=80.0,
            competency_score=80.0,
            learning_score=80.0,
        )
        self.assertAlmostEqual(talent.readiness_score, 80.0)
        self.assertEqual(talent.readiness_level, "ready_1y")

    def test_11_talent_score_range_validated(self):
        with self.assertRaises(ValidationError):
            self.make_talent(performance_score=120.0)

    def test_12_talent_workflow_draft_to_active(self):
        talent = self.make_talent()
        self.activate_talent(talent)
        self.assertEqual(talent.state, "active")
        self.assertTrue(talent.approved_at)
        self.assertTrue(talent.activated_at)

    def test_13_hrbp_cannot_approve_talent(self):
        talent = self.make_talent()
        talent.with_user(self.hrbp_user).action_propose()
        with self.assertRaises(AccessError):
            talent.with_user(self.hrbp_user).action_approve()

    def test_14_active_talent_identity_is_frozen(self):
        talent = self.activate_talent(self.make_talent())
        with self.assertRaises(AccessError):
            talent.with_user(self.talent_manager).write(
                {"pool_code": "DIFFERENT"}
            )

    def test_15_target_requirements_compute(self):
        self.make_requirement()
        talent = self.make_talent()
        self.assertTrue(talent.target_requirement_ids)
        self.assertGreaterEqual(talent.required_competency_count, 1)

    def test_16_active_talent_cannot_be_deleted(self):
        talent = self.activate_talent(self.make_talent())
        with self.assertRaises(UserError):
            talent.with_user(self.talent_manager).unlink()
