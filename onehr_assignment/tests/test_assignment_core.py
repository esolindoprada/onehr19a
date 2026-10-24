
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRAssignmentCommon


@tagged("post_install", "-at_install", "onehr_assignment")
class TestAssignmentCore(OneHRAssignmentCommon):
    def test_01_sequence_and_position_projection(self):
        assignment = self.make_assignment()
        self.assertNotEqual(assignment.name, "New")
        self.assertEqual(assignment.job_id, self.position.job_id)
        self.assertEqual(assignment.department_id, self.position.department_id)
        self.assertEqual(assignment.grade_id, self.position.grade_id)

    def test_02_invalid_fte_and_date_range_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_assignment(fte=1.1)
        with self.assertRaises(ValidationError):
            self.make_assignment(
                effective_from=fields.Date.today(),
                effective_to=fields.Date.today() - timedelta(days=1),
            )

    def test_03_direct_state_write_is_blocked(self):
        assignment = self.make_assignment()
        with self.assertRaises(AccessError):
            assignment.with_user(self.officer).write({"state": "approved"})

    def test_04_submitted_facts_are_immutable(self):
        assignment = self.make_assignment()
        self.force_approved(assignment)
        with self.assertRaises(AccessError):
            assignment.with_user(self.manager).write({"fte": 0.5})

    def test_05_primary_overlap_is_rejected(self):
        first = self.make_assignment()
        self.force_approved(first)
        second = self.make_assignment(position_id=self.position_2.id)
        with self.assertRaises(ValidationError):
            self.force_approved(second)

    def test_06_employee_total_fte_cannot_exceed_one(self):
        first = self.make_assignment(assignment_type="secondary", fte=0.6)
        self.force_approved(first)
        second = self.make_assignment(
            assignment_type="secondary", position_id=self.position_2.id, fte=0.5,
        )
        with self.assertRaises(ValidationError):
            self.force_approved(second)

    def test_07_position_headcount_and_fte_capacity_are_enforced(self):
        first = self.make_assignment(
            assignment_type="secondary", position_id=self.position_tight.id,
            employee_id=self.employee.id, fte=0.5,
        )
        self.force_approved(first)
        second = self.make_assignment(
            assignment_type="secondary", position_id=self.position_tight.id,
            employee_id=self.employee_2.id, fte=0.6,
        )
        with self.assertRaises(ValidationError):
            self.force_approved(second)

    def test_08_primary_activation_syncs_native_hr_version_and_manager(self):
        assignment = self.make_assignment()
        self.force_approved(assignment)
        assignment.with_user(self.manager)._activate_from_governed_execution()
        version = self.employee._get_version(assignment.effective_from)
        self.assertEqual(version.onehr_primary_position_id, self.position)
        self.assertEqual(version.onehr_grade_id, self.grade)
        self.assertEqual(version.job_id, self.job)
        self.assertEqual(version.department_id, self.department)
        self.assertEqual(self.employee.parent_id, self.manager_employee)

    def test_09_secondary_activation_does_not_sync_primary_position(self):
        version_before = self.employee._get_version(fields.Date.today())
        prior_position = version_before.onehr_primary_position_id
        assignment = self.make_assignment(assignment_type="secondary", movement_type="secondment")
        self.force_approved(assignment)
        assignment.with_user(self.manager)._activate_from_governed_execution()
        version_after = self.employee._get_version(fields.Date.today())
        self.assertEqual(version_after.onehr_primary_position_id, prior_position)

    def test_10_future_assignment_cannot_be_manually_activated_early(self):
        start, _end = self.make_future_dates()
        assignment = self.make_assignment(effective_from=start)
        self.force_approved(assignment)
        with self.assertRaises(UserError):
            assignment.with_user(self.manager).action_activate()
