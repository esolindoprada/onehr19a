import json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRLearningCommon


@tagged("post_install", "-at_install", "onehr_learning")
class TestLearningBudgetSecurityIntegrations(OneHRLearningCommon):
    def test_37_budget_creation_requires_learning_manager(self):
        today = __import__("odoo").fields.Date.today()
        with self.assertRaises(AccessError):
            self.env["onehr.learning.budget"].with_user(self.officer_user).create(
                {
                    "name": "Unauthorized Budget",
                    "code": "BUD-NO",
                    "company_id": self.company.id,
                    "period_start": today,
                    "period_end": today,
                    "allocated_amount": 100.0,
                }
            )

    def test_38_budget_activate_and_close_lifecycle(self):
        budget = self.make_budget(activate=False, code="BUD-LIFE")
        self.assertEqual(budget.state, "draft")
        budget.with_user(self.manager_user).action_activate()
        self.assertEqual(budget.state, "active")
        budget.with_user(self.manager_user).action_close()
        self.assertEqual(budget.state, "closed")

    def test_39_budget_overrun_policy_blocks_commitment(self):
        budget = self.make_budget(allocated_amount=100.0, code="BUD-BLOCK")
        line = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "Over budget certification",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "amount": 150.0,
                "cost_type": "certification",
            }
        )
        with self.assertRaises(ValidationError):
            line.with_user(self.officer_user).action_commit()

    def test_40_cost_lifecycle_planned_committed_actual(self):
        budget = self.make_budget(allocated_amount=1000.0, code="BUD-COST")
        line = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "Training material",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "amount": 250.0,
                "cost_type": "material",
            }
        )
        self.assertEqual(line.state, "planned")
        line.with_user(self.officer_user).action_commit()
        self.assertEqual(line.state, "committed")
        line.with_user(self.officer_user).action_mark_actual()
        self.assertEqual(line.state, "actual")
        with self.assertRaises(AccessError):
            line.with_user(self.officer_user).write({"amount": 260.0})

    def test_41_payroll_cost_payload_requires_actual_reimbursable_eligible(self):
        budget = self.make_budget(allocated_amount=1000.0, code="BUD-PAY")
        session = self.make_session()
        enrollment = self.make_enrollment(session=session)
        line = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "Employee training reimbursement",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "session_id": session.id,
                "enrollment_id": enrollment.id,
                "amount": 100.0,
                "cost_type": "reimbursement",
                "reimbursable": True,
                "payroll_bridge_eligible": True,
            }
        )
        line.with_user(self.officer_user).action_commit()
        line.with_user(self.officer_user).action_mark_actual()
        payload = line.with_user(self.manager_user).onehr_payroll_cost_payload()
        self.assertEqual(payload["employee_id"], self.participant.id)
        self.assertEqual(payload["amount"], 100.0)

    def test_42_budget_payroll_json_export_contains_only_eligible_actual_costs(self):
        budget = self.make_budget(allocated_amount=1000.0, code="BUD-JSON")
        session = self.make_session()
        enrollment = self.make_enrollment(session=session)
        eligible = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "Eligible reimbursement",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "session_id": session.id,
                "enrollment_id": enrollment.id,
                "amount": 80.0,
                "cost_type": "reimbursement",
                "reimbursable": True,
                "payroll_bridge_eligible": True,
            }
        )
        excluded = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "Venue cost",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "amount": 300.0,
                "cost_type": "venue",
            }
        )
        for line in (eligible, excluded):
            line.with_user(self.officer_user).action_commit()
            line.with_user(self.officer_user).action_mark_actual()

        action = budget.with_user(self.manager_user).action_export_payroll_cost_json()
        self.assertEqual(action["type"], "ir.actions.act_url")
        document = json.loads(
            __import__("base64").b64decode(budget.payroll_download_file).decode("utf-8")
        )
        self.assertEqual(len(document["costs"]), 1)
        self.assertEqual(document["costs"][0]["amount"], 80.0)

    def test_43_plain_internal_user_has_no_learning_model_acl(self):
        course = self.make_course(code="SEC-PLAIN")
        with self.assertRaises(AccessError):
            course.with_user(self.plain_user).read(["name"])

    def test_44_trainer_cannot_create_catalog_master(self):
        with self.assertRaises(AccessError):
            self.env["onehr.learning.course"].with_user(self.trainer_user).create(
                {
                    "name": "Unauthorized Course",
                    "code": "SEC-TRAINER",
                    "company_id": self.company.id,
                }
            )

    def test_45_trainer_record_rule_limits_sessions_to_assignment(self):
        assigned = self.make_session(title="Assigned Session")
        unassigned = self.make_session(title="Unassigned Session")
        unassigned.with_user(self.officer_user).write(
            {"trainer_employee_id": False}
        )
        visible = self.env["onehr.learning.session"].with_user(
            self.trainer_user
        ).search([("id", "in", [assigned.id, unassigned.id])])
        self.assertIn(assigned, visible)
        self.assertNotIn(unassigned, visible)

    def test_46_company_rule_hides_other_company_course(self):
        main = self.make_course(code="SEC-MAIN")
        other = self.env["onehr.learning.course"].create(
            {
                "name": "Other Company Course",
                "code": "SEC-OTHER",
                "company_id": self.other_company.id,
                "duration_hours": 1.0,
            }
        )
        visible = self.env["onehr.learning.course"].with_user(
            self.officer_user
        ).search([("id", "in", [main.id, other.id])])
        self.assertIn(main, visible)
        self.assertNotIn(other, visible)

    def test_47_learning_kpi_snapshot_reports_hours_completion_and_cost(self):
        session = self.make_session()
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()

        budget = self.make_budget(allocated_amount=1000.0, code="BUD-KPI")
        cost = self.env["onehr.learning.cost.line"].with_user(
            self.officer_user
        ).create(
            {
                "description": "KPI cost",
                "company_id": self.company.id,
                "budget_id": budget.id,
                "session_id": session.id,
                "amount": 200.0,
                "cost_type": "trainer",
            }
        )
        cost.with_user(self.officer_user).action_commit()
        cost.with_user(self.officer_user).action_mark_actual()

        today = session.start_datetime.date()
        snapshot = self.env["onehr.learning.session"].with_user(
            self.officer_user
        ).onehr_learning_kpi_snapshot(self.company, today, today)
        self.assertEqual(snapshot["session_count"], 1)
        self.assertEqual(snapshot["learner_count"], 1)
        self.assertEqual(snapshot["completion_rate"], 100.0)
        self.assertEqual(snapshot["training_hours"], session.planned_hours)
        self.assertEqual(snapshot["actual_cost"], 200.0)

    def test_48_participant_portal_payload_is_read_only_contract(self):
        enrollment = self.enrolled_participant()
        payload = self.env["onehr.learning.enrollment"].with_user(
            self.officer_user
        ).onehr_participant_portal_payload(self.participant)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["enrollment_id"], enrollment.id)
        self.assertEqual(payload[0]["state"], "enrolled")

    def test_49_used_course_cannot_be_deleted(self):
        course = self.make_course(code="HIST-COURSE")
        self.make_session(course=course, open_enrollment=False)
        with self.assertRaises(AccessError):
            course.with_user(self.manager_user).unlink()

    def test_50_non_draft_session_cannot_be_deleted(self):
        session = self.make_session()
        with self.assertRaises(AccessError):
            session.with_user(self.manager_user).unlink()

    def test_51_active_budget_cannot_be_deleted(self):
        budget = self.make_budget(code="HIST-BUDGET")
        with self.assertRaises(AccessError):
            budget.with_user(self.manager_user).unlink()

    def test_52_reimbursable_flag_required_for_payroll_eligibility(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.learning.cost.line"].with_user(
                self.officer_user
            ).create(
                {
                    "description": "Invalid payroll eligibility",
                    "company_id": self.company.id,
                    "amount": 10.0,
                    "cost_type": "reimbursement",
                    "payroll_bridge_eligible": True,
                    "reimbursable": False,
                }
            )
