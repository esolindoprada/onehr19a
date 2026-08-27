from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRAppraisalCommon


@tagged("post_install", "-at_install", "onehr_appraisal")
class TestAppraisalSecurityAndIntegrations(OneHRAppraisalCommon):
    def test_17_plain_user_has_no_appraisal_model_access(self):
        with self.assertRaises(AccessError):
            self.env["onehr.appraisal.form"].with_user(self.plain_user).search([])

    def test_18_participant_cannot_change_lifecycle_directly(self):
        form = self.make_form()
        with self.assertRaises(AccessError):
            form.with_user(self.employee_user).write({"state": "closed"})

    def test_19_manager_cannot_edit_another_manager_form(self):
        form = self.make_form()
        with self.assertRaises(AccessError):
            form.with_user(self.other_manager_user).write(
                {"manager_summary": "<p>Unauthorized</p>"}
            )

    def test_20_participant_cannot_edit_manager_rating(self):
        form = self.make_form()
        self.start_form(form)
        line = form.score_ids.filtered(lambda score: score.rater_type == "manager")
        with self.assertRaises(AccessError):
            line.with_user(self.employee_user).write({"rating": 5.0})

    def test_21_result_payload_excludes_restricted_corehr_payload(self):
        form = self.make_form()
        payload = form.with_user(self.hr_user).onehr_appraisal_result_payload()[0]
        self.assertIn("employee_number", payload)
        self.assertNotIn("identifier_value", payload)
        self.assertNotIn("medical", payload)
        self.assertNotIn("disability", payload)

    def test_22_kpi_snapshot_contract(self):
        self.make_form()
        payload = self.env["onehr.appraisal.form"].with_user(
            self.hr_user
        ).onehr_appraisal_kpi_snapshot(self.company)
        self.assertIn("completion_rate", payload)
        self.assertIn("rating_distribution", payload)

    def test_23_learning_handoff_remains_soft_dependency(self):
        form = self.make_form()
        line = self.env["onehr.appraisal.score"].with_user(self.hr_user).create(
            {
                "cycle_id": form.cycle_id.id,
                "form_id": form.id,
                "line_type": "development",
                "title": "Advanced Leadership",
                "rater_type": "manager",
                "learning_session_reference": "NOT-CONFIGURED",
            }
        )
        if not self.env.registry.get("onehr.learning.enrollment"):
            with self.assertRaises(UserError):
                line.with_user(self.hr_user).action_push_to_learning()

    def test_24_closed_appraisal_exposes_career_feedback_read_only(self):
        form = self.make_form()
        form.with_context(onehr_appraisal_action_write=True).write(
            {"state": "closed", "final_score": 88.0, "potential_score": 90.0}
        )
        payload = form.with_user(self.hr_user).onehr_career_feedback_payload()
        self.assertEqual(payload[0]["performance_score"], 88.0)
        self.assertIn("nine_box_position", payload[0])
