from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRAppraisalCommon


@tagged("post_install", "-at_install", "onehr_appraisal")
class TestAppraisalWorkflowAndScoring(OneHRAppraisalCommon):
    def test_09_start_review(self):
        form = self.make_form()
        self.start_form(form)
        self.assertEqual(form.state, "in_review")

    def test_10_employee_submits_self_rating(self):
        form = self.make_form()
        self.start_form(form)
        line = form.score_ids.filtered(lambda score: score.rater_type == "self")
        line.with_user(self.employee_user).write({"rating": 4.0})
        form.with_user(self.employee_user).action_submit_self_review()
        self.assertEqual(form.self_review_state, "done")
        self.assertEqual(line.rating_state, "submitted")

    def test_11_manager_submits_manager_rating(self):
        form = self.make_form()
        self.start_form(form)
        line = form.score_ids.filtered(lambda score: score.rater_type == "manager")
        line.with_user(self.manager_user).write({"rating": 5.0})
        form.with_user(self.manager_user).action_submit_manager_review()
        self.assertEqual(form.manager_review_state, "done")
        self.assertEqual(line.rating_state, "submitted")

    def test_12_submitted_rating_is_locked_for_rater(self):
        form = self.make_form()
        self.start_form(form)
        line = form.score_ids.filtered(lambda score: score.rater_type == "self")
        line.with_user(self.employee_user).write({"rating": 4.0})
        line.with_user(self.employee_user).action_submit_rating()
        with self.assertRaises(AccessError):
            line.with_user(self.employee_user).write({"rating": 5.0})

    def test_13_peer_feedback_lines_are_generated(self):
        form = self.make_form()
        self.start_form(form)
        form.with_user(self.hr_user).write(
            {"peer_reviewer_ids": [(6, 0, [self.peer_employee.id])]}
        )
        form.with_user(self.hr_user).action_request_peer_feedback()
        self.assertTrue(
            form.score_ids.filtered(lambda line: line.rater_type == "peer")
        )

    def test_14_assigned_peer_can_submit_rating(self):
        form = self.make_form()
        self.start_form(form)
        form.with_user(self.hr_user).write(
            {"peer_reviewer_ids": [(6, 0, [self.peer_employee.id])]}
        )
        form.with_user(self.hr_user).action_request_peer_feedback()
        line = form.score_ids.filtered(lambda score: score.rater_type == "peer")[:1]
        line.with_user(self.peer_user).write({"rating": 4.0})
        line.with_user(self.peer_user).action_submit_rating()
        self.assertEqual(line.rating_state, "submitted")

    def test_15_consolidation_requires_self_and_manager(self):
        form = self.make_form()
        self.start_form(form)
        with self.assertRaises(UserError):
            form.with_user(self.manager_user).action_move_to_consolidation()

    def test_16_score_normalization_and_weighted_overall(self):
        form = self.make_form()
        self.start_form(form)
        self_line = form.score_ids.filtered(lambda line: line.rater_type == "self")
        manager_line = form.score_ids.filtered(lambda line: line.rater_type == "manager")
        self_line.with_user(self.employee_user).write({"rating": 4.0})
        manager_line.with_user(self.manager_user).write({"rating": 5.0})
        form.with_user(self.employee_user).action_submit_self_review()
        form.with_user(self.manager_user).action_submit_manager_review()
        self.assertGreater(form.self_score, 0.0)
        self.assertGreater(form.manager_score, 0.0)
        self.assertGreater(form.overall_score, 0.0)
