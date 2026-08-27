from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRAssignmentCommon


@tagged("post_install", "-at_install", "onehr_assignment")
class TestCostingAndMovement(OneHRAssignmentCommon):
    def make_allocation(self, assignment, **overrides):
        values = {
            "assignment_id": assignment.id,
            "valid_from": assignment.effective_from,
            "valid_to": assignment.effective_to,
            "percentage": 100.0,
            "cost_center_code": "CC-100",
        }
        values.update(overrides)
        return self.env["onehr.assignment.cost.allocation"].with_user(self.officer).create(values)

    def make_active_source(self, **overrides):
        assignment = self.make_assignment(**overrides)
        self.force_active(assignment)
        return assignment

    def test_11_required_costing_must_cover_one_hundred_percent(self):
        assignment = self.make_assignment(costing_required=True)
        self.make_allocation(assignment, percentage=60.0)
        with self.assertRaises(ValidationError):
            assignment._validate_cost_allocation_coverage()

    def test_12_two_costing_lines_can_split_one_hundred_percent(self):
        assignment = self.make_assignment(costing_required=True)
        self.make_allocation(assignment, percentage=60.0, cost_center_code="CC-A")
        self.make_allocation(assignment, percentage=40.0, cost_center_code="CC-B")
        self.assertTrue(assignment._validate_cost_allocation_coverage())

    def test_13_costing_history_freezes_after_submission(self):
        assignment = self.make_assignment(costing_required=True)
        line = self.make_allocation(assignment)
        self.force_approved(assignment)
        with self.assertRaises(AccessError):
            line.with_user(self.officer).write({"percentage": 90.0})

    def test_14_duplicate_cost_dimension_overlap_rejected(self):
        assignment = self.make_assignment()
        self.make_allocation(assignment, percentage=50.0, cost_center_code="DUP")
        with self.assertRaises(ValidationError):
            self.make_allocation(assignment, percentage=50.0, cost_center_code="DUP")

    def test_15_unit_manager_can_propose_only_direct_report(self):
        source = self.make_active_source()
        request = self.env["onehr.assignment.change.request"].with_user(self.proposer).create({
            "company_id": self.company.id,
            "movement_type": "transfer",
            "effective_date": fields.Date.today() + timedelta(days=10),
            "reason": "Governed direct-report transfer",
        })
        line = self.env["onehr.assignment.change.line"].with_user(self.proposer).create({
            "request_id": request.id,
            "source_assignment_id": source.id,
            "target_position_id": self.position_2.id,
        })
        self.assertEqual(line.employee_name, self.employee.name)

        unrelated = self.make_assignment(
            employee_id=self.unrelated_employee.id,
            manager_id=self.unrelated_manager_employee.id,
            assignment_type="secondary",
            position_id=self.position_2.id,
        )
        self.force_active(unrelated)
        with self.assertRaises(AccessError):
            self.env["onehr.assignment.change.line"].with_user(self.proposer).create({
                "request_id": request.id,
                "source_assignment_id": unrelated.id,
                "target_position_id": self.position.id,
            })

    def test_16_movement_execution_creates_linked_successor(self):
        source = self.make_active_source()
        effective_date = fields.Date.today()
        # Source started today; move tomorrow to respect source-history integrity.
        source.with_user(self.manager).with_context(onehr_assignment_state_controlled=True).write({
            "effective_from": fields.Date.today() - timedelta(days=30)
        })
        request = self.env["onehr.assignment.change.request"].with_user(self.proposer).create({
            "company_id": self.company.id,
            "movement_type": "transfer",
            "effective_date": effective_date,
            "reason": "Immediate governed transfer",
        })
        line = self.env["onehr.assignment.change.line"].with_user(self.proposer).create({
            "request_id": request.id,
            "source_assignment_id": source.id,
            "target_position_id": self.position_2.id,
        })
        request.with_user(self.manager).with_context(
            onehr_assignment_change_state_controlled=True,
            onehr_assignment_change_evidence_controlled=True,
        ).write({
            "state": "approved", "approved_at": fields.Datetime.now(),
        })
        request.with_user(self.manager).action_execute()
        self.assertTrue(line.generated_assignment_id)
        self.assertEqual(line.generated_assignment_id.source_assignment_id, source)
        self.assertEqual(line.generated_assignment_id.position_id, self.position_2)
        self.assertEqual(request.state, "executed")

    def test_17_movement_execution_is_idempotent_per_line(self):
        source = self.make_active_source()
        source.with_user(self.manager).with_context(onehr_assignment_state_controlled=True).write({
            "effective_from": fields.Date.today() - timedelta(days=30)
        })
        request = self.env["onehr.assignment.change.request"].with_user(self.proposer).create({
            "company_id": self.company.id, "movement_type": "rotation",
            "effective_date": fields.Date.today(), "reason": "Rotation",
        })
        line = self.env["onehr.assignment.change.line"].with_user(self.proposer).create({
            "request_id": request.id, "source_assignment_id": source.id,
            "target_position_id": self.position_2.id,
        })
        first = line.with_user(self.manager)._execute_line()
        second = line.with_user(self.manager)._execute_line()
        self.assertEqual(first, second)

    def test_18_future_movement_creates_approved_successor_not_active(self):
        source = self.make_active_source()
        effective_date = fields.Date.today() + timedelta(days=20)
        request = self.env["onehr.assignment.change.request"].with_user(self.proposer).create({
            "company_id": self.company.id, "movement_type": "promotion",
            "effective_date": effective_date, "reason": "Future promotion",
        })
        line = self.env["onehr.assignment.change.line"].with_user(self.proposer).create({
            "request_id": request.id, "source_assignment_id": source.id,
            "target_position_id": self.position_2.id,
        })
        request.with_user(self.manager).with_context(
            onehr_assignment_change_state_controlled=True,
            onehr_assignment_change_evidence_controlled=True,
        ).write({
            "state": "approved", "approved_at": fields.Datetime.now(),
        })
        request.with_user(self.manager).action_execute()
        self.assertEqual(line.generated_assignment_id.state, "approved")
        self.assertEqual(source.state, "active")
        self.assertEqual(source.effective_to, effective_date - timedelta(days=1))
