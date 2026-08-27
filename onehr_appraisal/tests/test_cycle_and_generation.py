from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRAppraisalCommon


@tagged("post_install", "-at_install", "onehr_appraisal")
class TestAppraisalCycleAndGeneration(OneHRAppraisalCommon):
    def test_01_exact_three_models_present(self):
        for model_name in (
            "onehr.appraisal.cycle",
            "onehr.appraisal.form",
            "onehr.appraisal.score",
        ):
            self.assertIn(model_name, self.env)
        self.assertNotIn("onehr_appraisal.onehr_appraisal", self.env)

    def test_02_cycle_weight_must_total_100(self):
        with self.assertRaises(ValidationError):
            self.make_cycle(self_weight=10.0, manager_weight=10.0, peer_weight=10.0)

    def test_03_cycle_date_order_is_validated(self):
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.make_cycle(
                date_start=today + timedelta(days=30),
                date_end=today,
                self_review_deadline=False,
                manager_review_deadline=False,
                consolidation_deadline=False,
            )

    def test_04_cycle_deadline_order_is_validated(self):
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.make_cycle(
                self_review_deadline=today + timedelta(days=50),
                manager_review_deadline=today + timedelta(days=20),
            )

    def test_05_open_cycle_requires_complete_weighted_template(self):
        cycle = self.make_cycle()
        with self.assertRaises(UserError):
            cycle.with_user(self.hr_user).action_open_cycle()

        self.add_template(cycle, weight=70.0)
        with self.assertRaises(ValidationError):
            cycle.with_user(self.hr_user).action_open_cycle()

    def test_06_generate_forms_clones_targets_and_raters(self):
        cycle = self.make_cycle()
        self.add_template(cycle)
        cycle.with_user(self.hr_user).action_generate_appraisal_forms()

        form = cycle.form_ids.filtered(lambda record: record.employee_id == self.employee)
        self.assertTrue(form)
        self.assertTrue(form.score_ids.filtered(lambda line: line.rater_type == "target"))
        self.assertTrue(form.score_ids.filtered(lambda line: line.rater_type == "self"))
        self.assertTrue(form.score_ids.filtered(lambda line: line.rater_type == "manager"))

    def test_07_generation_is_idempotent_per_employee_cycle(self):
        cycle = self.make_cycle()
        self.add_template(cycle)
        cycle.with_user(self.hr_user).action_generate_appraisal_forms()
        before = len(cycle.form_ids)
        cycle.with_user(self.hr_user).action_generate_appraisal_forms()
        self.assertEqual(len(cycle.form_ids), before)

    def test_08_cycle_metrics_reflect_closed_forms(self):
        form = self.make_form()
        form.with_context(onehr_appraisal_action_write=True).write(
            {"state": "closed", "final_score": 90.0}
        )
        form.cycle_id.invalidate_recordset()
        self.assertGreaterEqual(form.cycle_id.form_count, 1)
        self.assertGreaterEqual(form.cycle_id.completed_form_count, 1)
