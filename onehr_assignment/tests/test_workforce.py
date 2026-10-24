
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRAssignmentCommon


@tagged("post_install", "-at_install", "onehr_assignment")
class TestWorkforcePlanning(OneHRAssignmentCommon):
    def make_plan(self, **overrides):
        values = {
            "name": "FY Workforce Plan",
            "plan_code": "WF-FY",
            "company_id": self.company.id,
            "scenario": "budget",
            "period_start": fields.Date.today(),
            "period_end": fields.Date.today() + timedelta(days=365),
        }
        values.update(overrides)
        return self.env["onehr.workforce.plan"].with_user(self.manager).create(values)

    def add_line(self, plan, position=None, **overrides):
        values = {
            "plan_id": plan.id,
            "position_id": (position or self.position).id,
            "planned_headcount": 2,
            "planned_fte": 2.0,
            "planned_cost": 120000000.0,
        }
        values.update(overrides)
        return self.env["onehr.workforce.plan.line"].with_user(self.manager).create(values)

    def test_19_plan_totals_roll_up_lines(self):
        plan = self.make_plan()
        self.add_line(plan)
        self.add_line(plan, position=self.position_2, planned_headcount=1, planned_fte=0.5, planned_cost=30000000)
        self.assertEqual(plan.planned_headcount, 3)
        self.assertAlmostEqual(plan.planned_fte, 2.5)
        self.assertAlmostEqual(plan.planned_cost, 150000000)

    def test_20_plan_line_fte_cannot_exceed_headcount(self):
        plan = self.make_plan()
        with self.assertRaises(ValidationError):
            self.add_line(plan, planned_headcount=1, planned_fte=1.5)

    def test_21_plan_version_clones_lines_without_budget_evidence(self):
        plan = self.make_plan()
        self.add_line(plan)
        plan.with_user(self.manager).with_context(onehr_workforce_plan_state_controlled=True).write({"state": "rejected"})
        action = plan.with_user(self.manager).action_create_new_version()
        successor = self.env["onehr.workforce.plan"].browse(action["res_id"])
        self.assertEqual(successor.version, 2)
        self.assertEqual(successor.predecessor_plan_id, plan)
        self.assertEqual(len(successor.line_ids), 1)
        self.assertFalse(successor.line_ids.generated_budget_id)

    def test_22_plan_activation_materializes_active_position_budget(self):
        plan = self.make_plan()
        line = self.add_line(plan)
        plan.with_user(self.manager).with_context(onehr_workforce_plan_state_controlled=True).write({"state": "approved"})
        plan.with_user(self.manager).action_activate()
        self.assertEqual(plan.state, "active")
        self.assertTrue(line.generated_budget_id)
        self.assertEqual(line.generated_budget_id.state, "active")
        self.assertEqual(line.generated_budget_id.authorized_fte, line.planned_fte)

    def test_23_active_position_budget_intervals_cannot_overlap(self):
        first = self.env["onehr.position.budget"].with_user(self.manager).create({
            "position_id": self.position.id,
            "valid_from": fields.Date.today(),
            "valid_to": fields.Date.today() + timedelta(days=100),
            "authorized_headcount": 2,
            "authorized_fte": 2.0,
        })
        first.with_user(self.manager).action_activate()
        second = self.env["onehr.position.budget"].with_user(self.manager).create({
            "position_id": self.position.id,
            "valid_from": fields.Date.today() + timedelta(days=50),
            "valid_to": fields.Date.today() + timedelta(days=150),
            "authorized_headcount": 2,
            "authorized_fte": 2.0,
        })
        with self.assertRaises(ValidationError):
            second.with_user(self.manager).action_activate()

    def test_24_workforce_plan_is_frozen_after_submission(self):
        plan = self.make_plan()
        self.add_line(plan)
        plan.with_user(self.manager).with_context(onehr_workforce_plan_state_controlled=True).write({"state": "approved"})
        with self.assertRaises(AccessError):
            plan.with_user(self.manager).write({"period_end": plan.period_end + timedelta(days=1)})
