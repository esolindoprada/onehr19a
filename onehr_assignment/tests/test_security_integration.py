from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRAssignmentCommon


@tagged("post_install", "-at_install", "onehr_assignment")
class TestAssignmentSecurityIntegration(OneHRAssignmentCommon):
    def test_25_proposer_sees_direct_report_but_not_unrelated_assignment(self):
        own = self.make_assignment(assignment_type="secondary")
        unrelated = self.make_assignment(
            employee_id=self.unrelated_employee.id,
            manager_id=self.unrelated_manager_employee.id,
            assignment_type="secondary",
            position_id=self.position_2.id,
        )
        visible = self.env["onehr.assignment"].with_user(self.proposer).search([
            ("id", "in", [own.id, unrelated.id])
        ])
        self.assertIn(own, visible)
        self.assertNotIn(unrelated, visible)
        with self.assertRaises(AccessError):
            own.with_user(self.proposer).read(["employee_id"])

    def test_26_officer_company_scope_and_history_delete_protection(self):
        main = self.make_assignment(assignment_type="secondary")
        other = self.env["onehr.assignment"].with_user(self.manager).create({
            "company_id": self.other_company.id,
            "employee_id": self.other_employee.id,
            "assignment_type": "secondary",
            "movement_type": "initial",
            "position_id": self.other_position.id,
            "effective_from": main.effective_from,
            "fte": 1.0,
        })
        visible = self.env["onehr.assignment"].with_user(self.officer).search([
            ("id", "in", [main.id, other.id])
        ])
        self.assertIn(main, visible)
        self.assertNotIn(other, visible)
        self.force_approved(main)
        with self.assertRaises(AccessError):
            main.unlink()
