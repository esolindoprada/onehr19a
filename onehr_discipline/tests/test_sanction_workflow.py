from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRDisciplineCommon


@tagged("post_install", "-at_install", "onehr_discipline")
class TestDisciplineSanctionWorkflow(OneHRDisciplineCommon):
    def test_25_sanction_requires_decision_stage(self):
        case = self.make_case()
        with self.assertRaises(UserError):
            self.env["onehr.discipline.sanction"].with_user(
                self.hrbp
            ).create(
                {
                    "case_id": case.id,
                    "sanction_type": "written_warning",
                    "decision_basis": "<p>Basis.</p>",
                    "sanction_terms": "<p>Terms.</p>",
                }
            )

    def test_26_sanction_reference_uses_sequence(self):
        sanction = self.make_sanction()
        self.assertTrue(sanction.reference.startswith("SAN/"))
        self.assertEqual(sanction.state, "draft")

    def test_27_payroll_deduction_requires_positive_amount(self):
        case = self.move_case_to_decision()
        with self.assertRaises(ValidationError):
            self.make_sanction(
                case=case,
                sanction_type="payroll_deduction",
                payroll_deduction_amount=0,
                payroll_period_date=fields.Date.today(),
            )

    def test_28_probation_requires_dates_and_conditions(self):
        case = self.move_case_to_decision()
        with self.assertRaises(ValidationError):
            self.make_sanction(
                case=case,
                sanction_type="probation",
            )

    def test_29_termination_requires_contract_action(self):
        case = self.move_case_to_decision()
        with self.assertRaises(ValidationError):
            self.make_sanction(
                case=case,
                sanction_type="termination",
                sanction_terms="<p>Termination recommendation.</p>",
            )

    def test_30_submit_creates_workflow_request(self):
        sanction = self.make_sanction()
        sanction.with_user(
            self.hrbp
        ).action_submit_for_sanction_approval()
        request = self.latest_request(sanction)
        self.assertTrue(request)
        self.assertEqual(sanction.state, "approval")
        self.assertIn(request.state, ("submitted", "pending"))

    def test_31_approval_callback_moves_sanction_to_approved(self):
        sanction, request = self.approve_sanction()
        self.assertEqual(sanction.state, "approved")
        self.assertTrue(sanction.approved_at)
        self.assertEqual(request.final_decision, "approve")

    def test_32_sanction_definition_locked_after_submission(self):
        sanction = self.make_sanction()
        sanction.with_user(
            self.hrbp
        ).action_submit_for_sanction_approval()
        with self.assertRaises(AccessError):
            sanction.with_user(self.hrbp).write(
                {"sanction_terms": "<p>Changed after submission.</p>"}
            )

    def test_33_direct_lifecycle_write_is_blocked(self):
        sanction = self.make_sanction()
        with self.assertRaises(AccessError):
            sanction.with_user(self.hrbp).write(
                {"state": "executed"}
            )

    def test_34_execution_requires_approved_sanction(self):
        sanction = self.make_sanction()
        with self.assertRaises(UserError):
            sanction.with_user(self.legal).action_execute()

    def test_35_execution_marks_workflow_request_executed(self):
        sanction, request = self.approve_sanction()
        sanction.with_user(self.legal).action_execute()
        sanction.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(sanction.state, "executed")
        self.assertEqual(request.state, "executed")
        self.assertTrue(sanction.executed_at)

    def test_36_employee_service_recorded_after_execution(self):
        sanction = self.execute_sanction()
        sanction.with_user(self.hrbp).action_mark_served()
        self.assertTrue(sanction.served_at)
        self.assertTrue(sanction.employee_receipt_acknowledged)

    def test_37_execution_evidence_blocked_before_execution(self):
        sanction = self.make_sanction()
        with self.assertRaises(AccessError):
            sanction.with_user(self.hrbp).write(
                {"execution_note": "Premature execution evidence."}
            )

    def test_38_formal_sanction_case_can_close_after_execution(self):
        case = self.move_case_to_decision()
        sanction = self.make_sanction(case=case)
        sanction, request = self.approve_sanction(sanction)
        sanction.with_user(self.legal).action_execute()
        case.invalidate_recordset()
        case.with_user(self.manager).action_close_case()
        self.assertEqual(case.state, "closed")

    def test_39_executed_sanction_cannot_be_deleted(self):
        sanction = self.execute_sanction()
        with self.assertRaises(UserError):
            sanction.with_user(self.legal).unlink()

    def test_40_sanction_physical_table_name_is_safe(self):
        self.assertEqual(
            self.env["onehr.discipline.sanction"]._table,
            "onehr_discipline_sanction",
        )
        self.assertLessEqual(
            len(
                self.env["onehr.discipline.sanction"]._table.encode(
                    "utf-8"
                )
            ),
            63,
        )
