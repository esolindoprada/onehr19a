
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRDisciplineCommon


@tagged("post_install", "-at_install", "onehr_discipline")
class TestDisciplineSecurityIntegrations(OneHRDisciplineCommon):
    def test_41_plain_hr_user_has_no_discipline_access(self):
        self.make_case()
        with self.assertRaises(AccessError):
            self.env["onehr.discipline.case"].with_user(
                self.plain_hr
            ).search([])

    def test_42_investigator_sees_only_assigned_cases(self):
        assigned = self.make_case()
        other = self.env["onehr.discipline.case"].with_user(
            self.hrbp
        ).create(
            self.case_values(
                employee=self.employee_two,
                investigator_user_id=self.manager.id,
                case_owner_user_id=self.manager.id,
                hrbp_user_id=self.manager.id,
            )
        )
        visible = self.env["onehr.discipline.case"].with_user(
            self.investigator
        ).search(
            [("id", "in", [assigned.id, other.id])]
        )
        self.assertEqual(visible.ids, [assigned.id])

    def test_43_manager_has_company_scope(self):
        first = self.make_case()
        second = self.env["onehr.discipline.case"].with_user(
            self.hrbp
        ).create(
            self.case_values(employee=self.employee_two)
        )
        visible = self.env["onehr.discipline.case"].with_user(
            self.manager
        ).search(
            [("id", "in", [first.id, second.id])]
        )
        self.assertEqual(set(visible.ids), {first.id, second.id})

    def test_44_multi_company_isolation(self):
        other_case = self.env["onehr.discipline.case"].with_user(
            self.other_hrbp
        ).create(
            {
                **self.case_values(employee=self.other_employee),
                "case_owner_user_id": self.other_hrbp.id,
                "investigator_user_id": self.other_hrbp.id,
                "hrbp_user_id": self.other_hrbp.id,
                "legal_user_id": False,
            }
        )
        visible = self.env["onehr.discipline.case"].with_user(
            self.manager
        ).search([("id", "=", other_case.id)])
        self.assertFalse(visible)

    def test_45_kpi_snapshot_returns_enterprise_metrics(self):
        self.close_no_action_case()
        payload = self.env["onehr.discipline.case"].with_user(
            self.manager
        ).onehr_discipline_kpi_snapshot(self.company)
        self.assertGreaterEqual(payload["case_count"], 1)
        self.assertIn("repeat_offense_rate", payload)
        self.assertIn("average_resolution_days", payload)
        self.assertIn("sanction_type_distribution", payload)

    def test_46_payroll_payload_and_callback_preserve_ownership(self):
        case = self.move_case_to_decision()
        sanction = self.make_sanction(
            case=case,
            sanction_type="payroll_deduction",
            decision_basis="<p>Approved deduction request.</p>",
            sanction_terms="<p>Downstream payroll validation required.</p>",
            payroll_deduction_amount=100000.0,
            payroll_period_date=fields.Date.today(),
        )
        sanction, request = self.approve_sanction(sanction)
        sanction.with_user(self.legal).action_execute()
        request.invalidate_recordset()
        self.assertEqual(request.state, "executed")
        rows = self.env["onehr.discipline.sanction"].with_user(
            self.legal
        ).onehr_discipline_payroll_payload(
            sanction.payroll_period_date,
            sanction.payroll_period_date,
            self.company,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sanction_reference"], sanction.reference)

        self.env["onehr.discipline.sanction"].with_user(
            self.legal
        ).onehr_record_payroll_execution(
            sanction.reference,
            "confirmed",
            "PAY-TEST-001",
        )
        sanction.invalidate_recordset()
        self.assertEqual(sanction.payroll_execution_state, "confirmed")
        self.assertEqual(
            sanction.payroll_execution_reference,
            "PAY-TEST-001",
        )

    def test_47_document_and_audit_payloads_are_minimum_necessary(self):
        case = self.close_no_action_case()
        document_payload = self.env[
            "onehr.discipline.case"
        ].with_user(self.legal).onehr_discipline_document_payload(
            case.reference
        )
        audit_payload = self.env[
            "onehr.discipline.case"
        ].with_user(self.legal).onehr_discipline_case_audit_payload(
            case.reference
        )
        self.assertEqual(
            document_payload["source_model"],
            "onehr.discipline.case",
        )
        self.assertEqual(
            document_payload["sensitivity"],
            "restricted",
        )
        self.assertEqual(
            audit_payload["reference"],
            case.reference,
        )
        self.assertIn("resolution_days", audit_payload)

    def test_48_sla_cron_is_idempotent_for_same_summary_deadline(self):
        self.env["ir.config_parameter"].set_param(
            "onehr_discipline.default_investigation_sla_days",
            "1",
        )
        case = self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        model = self.env["onehr.discipline.case"].with_user(
            self.manager
        )
        model._cron_discipline_sla()
        before = len(
            case.activity_ids.filtered(
                lambda activity: activity.summary
                == "Discipline investigation due"
            )
        )
        model._cron_discipline_sla()
        after = len(
            case.activity_ids.filtered(
                lambda activity: activity.summary
                == "Discipline investigation due"
            )
        )
        self.assertEqual(before, after)

