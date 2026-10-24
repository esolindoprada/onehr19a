
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRCareerSuccessionCommon


@tagged("post_install", "-at_install", "onehr_career_succession")
class TestCompetencyMatrix(OneHRCareerSuccessionCommon):
    def test_01_exact_four_models_present(self):
        for model_name in (
            "onehr.competency",
            "onehr.position.competency",
            "onehr.talent.pool",
            "onehr.succession.plan",
        ):
            self.assertIn(model_name, self.env)
        self.assertNotIn(
            "onehr_career_succession.onehr_career_succession",
            self.env,
        )

    def test_02_competency_level_scale_validated(self):
        with self.assertRaises(ValidationError):
            self.make_competency(level_min=5, level_max=3)

    def test_03_competency_code_unique_per_company(self):
        competency = self.make_competency(code="UNIQUE-COMP")
        with self.assertRaises(Exception):
            self.make_competency(
                code=competency.code,
                name="Duplicate",
            )

    def test_04_position_requirement_level_within_scale(self):
        competency = self.make_competency(level_min=1, level_max=3)
        with self.assertRaises(ValidationError):
            self.make_requirement(
                competency=competency,
                required_level=5,
            )

    def test_05_position_requirement_weight_validated(self):
        with self.assertRaises(ValidationError):
            self.make_requirement(weight=120.0)

    def test_06_position_competency_identity_unique(self):
        competency = self.make_competency()
        self.make_requirement(competency=competency)
        with self.assertRaises(Exception):
            self.make_requirement(competency=competency)

    def test_07_requirement_opens_talent_gap_action(self):
        requirement = self.make_requirement()
        action = requirement.with_user(self.hrbp_user).action_open_talent_gap()
        self.assertEqual(action["res_model"], "onehr.talent.pool")

    def test_08_used_competency_cannot_be_deleted(self):
        competency = self.make_competency()
        self.make_requirement(competency=competency)
        with self.assertRaises(UserError):
            competency.with_user(self.talent_manager).unlink()

