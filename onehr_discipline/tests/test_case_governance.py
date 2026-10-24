
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRDisciplineCommon


@tagged("post_install", "-at_install", "onehr_discipline")
class TestDisciplineCaseGovernance(OneHRDisciplineCommon):
    def test_01_exact_two_persistent_models(self):
        self.assertIn("onehr.discipline.case", self.env)
        self.assertIn("onehr.discipline.sanction", self.env)
        self.assertNotIn("onehr.discipline.policy", self.env)
        self.assertNotIn("onehr.discipline.violation", self.env)
        self.assertNotIn("onehr.discipline.investigation", self.env)
        self.assertNotIn("onehr.discipline.hearing", self.env)
        self.assertNotIn("onehr.discipline.appeal", self.env)

    def test_02_settings_extension_is_transient(self):
        self.assertTrue(self.env["res.config.settings"].is_transient())

    def test_03_case_reference_uses_sequence(self):
        case = self.make_case()
        self.assertNotEqual(case.reference, "New")
        self.assertTrue(case.reference.startswith("DISC/"))

    def test_04_case_defaults_to_reported(self):
        case = self.make_case()
        self.assertEqual(case.state, "reported")
        self.assertEqual(case.appeal_state, "none")

    def test_05_cross_company_employee_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.discipline.case"].with_user(
                self.hrbp
            ).create(
                self.case_values(
                    employee=self.other_employee,
                    company_id=self.company.id,
                )
            )

    def test_06_violation_weight_range_enforced(self):
        with self.assertRaises(ValidationError):
            self.make_case(violation_weight=101)

    def test_07_start_investigation_sets_sla(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        self.assertEqual(case.state, "investigation")
        self.assertTrue(case.investigation_started_at)
        self.assertTrue(case.investigation_due_date)
        self.assertEqual(case.stage_due_date, case.investigation_due_date)

    def test_08_hearing_requires_investigation_evidence(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        with self.assertRaises(UserError):
            case.with_user(self.hrbp).action_move_to_hearing()

    def test_09_investigation_moves_to_hearing(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        case.with_user(self.hrbp).write(
            {
                "investigation_findings": "<p>Findings.</p>",
                "investigation_recommendation": "Hearing recommended.",
                "evidence_assessment": "supported",
                "hearing_scheduled_at": fields.Datetime.now()
                + timedelta(days=1),
            }
        )
        case.with_user(self.hrbp).action_move_to_hearing()
        self.assertEqual(case.state, "hearing")
        self.assertTrue(case.hearing_due_date)

    def test_10_hearing_requires_minutes_before_decision(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        case.with_user(self.hrbp).write(
            {
                "investigation_findings": "<p>Findings.</p>",
                "investigation_recommendation": "Hearing.",
                "evidence_assessment": "supported",
                "hearing_scheduled_at": fields.Datetime.now()
                + timedelta(days=1),
            }
        )
        case.with_user(self.hrbp).action_move_to_hearing()
        with self.assertRaises(UserError):
            case.with_user(self.hrbp).action_move_to_decision()

    def test_11_complete_hearing_moves_to_decision(self):
        case = self.move_case_to_decision()
        self.assertEqual(case.state, "decision")
        self.assertTrue(case.decision_due_date)

    def test_12_report_classification_locked_after_hearing(self):
        case = self.move_case_to_decision()
        with self.assertRaises(AccessError):
            case.with_user(self.hrbp).write(
                {"severity": "critical"}
            )

    def test_13_investigator_cannot_reclassify_case(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        with self.assertRaises(AccessError):
            case.with_user(self.investigator).write(
                {"severity": "serious"}
            )

    def test_14_investigator_can_update_assigned_findings(self):
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        case.with_user(self.investigator).write(
            {"investigation_findings": "<p>Assigned investigator finding.</p>"}
        )
        self.assertIn(
            "Assigned investigator",
            case.investigation_findings,
        )

    def test_15_case_identity_is_immutable(self):
        case = self.make_case()
        with self.assertRaises(AccessError):
            case.with_user(self.hrbp).write(
                {"employee_id": self.employee_two.id}
            )

    def test_16_no_action_case_can_close(self):
        case = self.close_no_action_case()
        self.assertTrue(case.closed_at)
        self.assertTrue(case.retention_until)
        self.assertGreaterEqual(case.resolution_days, 0.0)

    def test_17_formal_sanction_case_requires_executed_sanction(self):
        case = self.move_case_to_decision()
        case.with_user(self.hrbp).write(
            {
                "final_disposition": "sanction",
                "decision_summary": "<p>Formal sanction required.</p>",
            }
        )
        with self.assertRaises(UserError):
            case.with_user(self.manager).action_close_case()

    def test_18_prior_closed_case_sets_repeat_indicator(self):
        first = self.close_no_action_case()
        second = self.make_case()
        second.invalidate_recordset()
        self.assertGreaterEqual(second.prior_case_count, 1)
        self.assertTrue(second.repeat_offense)

    def test_19_appeal_requires_reason(self):
        case = self.move_case_to_decision()
        with self.assertRaises(UserError):
            case.with_user(self.hrbp).action_record_appeal()

    def test_20_appeal_can_be_recorded_and_reviewed(self):
        case = self.move_case_to_decision()
        case.with_user(self.hrbp).write(
            {"appeal_reason": "Employee requests formal review."}
        )
        case.with_user(self.hrbp).action_record_appeal()
        self.assertEqual(case.appeal_state, "submitted")
        case.with_user(self.legal).action_start_appeal_review()
        self.assertEqual(case.appeal_state, "review")

    def test_21_active_appeal_blocks_closure(self):
        case = self.move_case_to_decision()
        case.with_user(self.hrbp).write(
            {
                "final_disposition": "no_action",
                "decision_summary": "<p>Decision.</p>",
                "appeal_reason": "Formal appeal.",
            }
        )
        case.with_user(self.hrbp).action_record_appeal()
        with self.assertRaises(UserError):
            case.with_user(self.manager).action_close_case()

    def test_22_legal_can_finalize_appeal(self):
        case = self.move_case_to_decision()
        case.with_user(self.hrbp).write(
            {"appeal_reason": "Formal appeal."}
        )
        case.with_user(self.hrbp).action_record_appeal()
        case.with_user(self.legal).action_start_appeal_review()
        case.with_user(self.legal).write(
            {"appeal_outcome_summary": "<p>Decision upheld after review.</p>"}
        )
        case.with_user(self.legal).action_uphold_appeal()
        self.assertEqual(case.appeal_state, "upheld")
        self.assertTrue(case.appeal_decided_at)

    def test_23_hrbp_cannot_cancel_case_as_legal(self):
        case = self.make_case()
        with self.assertRaises(AccessError):
            case.with_user(self.hrbp).action_cancel_case()

    def test_24_case_physical_table_name_is_safe(self):
        self.assertEqual(
            self.env["onehr.discipline.case"]._table,
            "onehr_discipline_case",
        )
        self.assertLessEqual(
            len(
                self.env["onehr.discipline.case"]._table.encode(
                    "utf-8"
                )
            ),
            63,
        )

    def test_49_repeat_offense_search_true_matches_dynamic_compute(self):
        first = self.close_no_action_case()
        second = self.make_case()
        second.invalidate_recordset()

        found = self.env["onehr.discipline.case"].with_user(
            self.manager
        ).search(
            [
                ("id", "in", [first.id, second.id]),
                ("repeat_offense", "=", True),
            ]
        )
        self.assertNotIn(first, found)
        self.assertIn(second, found)

    def test_50_repeat_offense_search_false_matches_dynamic_compute(self):
        first = self.close_no_action_case()
        second = self.make_case()
        second.invalidate_recordset()

        found = self.env["onehr.discipline.case"].with_user(
            self.manager
        ).search(
            [
                ("id", "in", [first.id, second.id]),
                ("repeat_offense", "=", False),
            ]
        )
        self.assertIn(first, found)
        self.assertNotIn(second, found)


