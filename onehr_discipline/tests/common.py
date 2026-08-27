from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRDisciplineCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"Discipline Other Company {cls.__name__}"}
        )

        cls.group_investigator = cls.env.ref(
            "onehr_discipline.group_onehr_discipline_investigator"
        )
        cls.group_hrbp = cls.env.ref(
            "onehr_discipline.group_onehr_discipline_hrbp"
        )
        cls.group_manager = cls.env.ref(
            "onehr_discipline.group_onehr_discipline_manager"
        )
        cls.group_legal = cls.env.ref(
            "onehr_discipline.group_onehr_discipline_legal"
        )
        cls.group_hr_user = cls.env.ref("hr.group_hr_user")
        cls.group_workflow_manager = cls.env.ref(
            "onehr_workflow_approval.group_onehr_workflow_manager"
        )

        suffix = cls.__name__.lower()

        def make_user(name, login, group, company, companies=None):
            companies = companies or [company]
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": f"{login}_{suffix}",
                    "company_id": company.id,
                    "company_ids": [
                        Command.set([item.id for item in companies])
                    ],
                    "group_ids": [Command.set([group.id])],
                }
            )

        cls.investigator = make_user(
            "Discipline Investigator",
            "disc_investigator",
            cls.group_investigator,
            cls.company,
        )
        cls.hrbp = make_user(
            "Discipline HRBP",
            "disc_hrbp",
            cls.group_hrbp,
            cls.company,
        )
        cls.manager = make_user(
            "Discipline Manager",
            "disc_manager",
            cls.group_manager,
            cls.company,
        )
        cls.legal = make_user(
            "Discipline Legal IR",
            "disc_legal",
            cls.group_legal,
            cls.company,
        )
        cls.plain_hr = make_user(
            "Plain HR User",
            "disc_plain_hr",
            cls.group_hr_user,
            cls.company,
        )
        cls.workflow_manager = make_user(
            "Discipline Workflow Manager",
            "disc_workflow_manager",
            cls.group_workflow_manager,
            cls.company,
            companies=[cls.company, cls.other_company],
        )
        cls.other_hrbp = make_user(
            "Other Company Discipline HRBP",
            "disc_other_hrbp",
            cls.group_hrbp,
            cls.other_company,
        )

        cls.department = cls.env["hr.department"].create(
            {
                "name": "Discipline Finance",
                "company_id": cls.company.id,
            }
        )
        cls.other_department = cls.env["hr.department"].create(
            {
                "name": "Other Discipline Finance",
                "company_id": cls.other_company.id,
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Discipline Analyst",
                "company_id": cls.company.id,
            }
        )
        cls.other_job = cls.env["hr.job"].create(
            {
                "name": "Other Discipline Analyst",
                "company_id": cls.other_company.id,
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Discipline Employee",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "onehr_employee_number": f"DISC-E001-{suffix}",
                "work_email": f"discipline.employee.{suffix}@example.com",
            }
        )
        cls.employee_two = cls.env["hr.employee"].create(
            {
                "name": "Discipline Employee Two",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "onehr_employee_number": f"DISC-E002-{suffix}",
                "work_email": f"discipline.employee2.{suffix}@example.com",
            }
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {
                "name": "Other Discipline Employee",
                "company_id": cls.other_company.id,
                "department_id": cls.other_department.id,
                "job_id": cls.other_job.id,
                "onehr_employee_number": f"DISC-O001-{suffix}",
            }
        )

        sanction_model = cls.env["ir.model"]._get(
            "onehr.discipline.sanction"
        )
        cls.approval_rule = cls.env[
            "onehr.approval.rule"
        ].with_user(cls.workflow_manager).create(
            {
                "code": f"DISC-SAN-{suffix}",
                "name": "Discipline Written Warning Approval",
                "company_id": cls.company.id,
                "model_id": sanction_model.id,
                "document_type": (
                    "onehr.discipline.sanction.written_warning"
                ),
                "risk_level": "normal",
                "valid_from": fields.Date.today(),
                "minimum_distinct_approvers": 1,
                "priority": 900,
            }
        )
        cls.approval_step = cls.env[
            "onehr.approval.step"
        ].with_user(cls.workflow_manager).create(
            {
                "rule_id": cls.approval_rule.id,
                "name": "Discipline Legal Approval",
                "level": 10,
                "sequence": 10,
                "approver_policy": "specific_users",
                "specific_user_ids": [
                    Command.set([cls.legal.id])
                ],
                "decision_mode": "any",
                "quorum_count": 1,
                "valid_from": cls.approval_rule.valid_from,
                "sla_hours": 24,
            }
        )
        cls.approval_rule.with_user(
            cls.workflow_manager
        ).action_activate()

        cls.payroll_approval_rule = cls.env[
            "onehr.approval.rule"
        ].with_user(cls.workflow_manager).create(
            {
                "code": f"DISC-PAY-{suffix}",
                "name": "Discipline Payroll Deduction Approval",
                "company_id": cls.company.id,
                "model_id": sanction_model.id,
                "document_type": (
                    "onehr.discipline.sanction.payroll_deduction"
                ),
                "risk_level": "normal",
                "valid_from": fields.Date.today(),
                "minimum_distinct_approvers": 1,
                "priority": 910,
            }
        )
        cls.payroll_approval_step = cls.env[
            "onehr.approval.step"
        ].with_user(cls.workflow_manager).create(
            {
                "rule_id": cls.payroll_approval_rule.id,
                "name": "Discipline Payroll Legal Approval",
                "level": 10,
                "sequence": 10,
                "approver_policy": "specific_users",
                "specific_user_ids": [
                    Command.set([cls.legal.id])
                ],
                "decision_mode": "any",
                "quorum_count": 1,
                "valid_from": cls.payroll_approval_rule.valid_from,
                "sla_hours": 24,
            }
        )
        cls.payroll_approval_rule.with_user(
            cls.workflow_manager
        ).action_activate()

    def case_values(self, employee=None, **extra):
        employee = employee or self.employee
        values = {
            "name": f"Discipline Case {self._testMethodName}",
            "company_id": employee.company_id.id,
            "employee_id": employee.id,
            "case_owner_user_id": self.hrbp.id,
            "investigator_user_id": self.investigator.id,
            "hrbp_user_id": self.hrbp.id,
            "legal_user_id": self.legal.id,
            "incident_date": fields.Datetime.now() - timedelta(hours=2),
            "incident_location": "Head Office",
            "source_type": "manager_report",
            "allegation_summary": (
                "Reported conduct requires confidential fact-finding."
            ),
            "chronology": "<p>Initial neutral chronology.</p>",
            "policy_reference": "PNP/2026/00001",
            "violation_code": "CONDUCT-01",
            "violation_category": "conduct",
            "severity": "moderate",
            "violation_weight": 45,
        }
        values.update(extra)
        return values

    def make_case(self, **extra):
        return self.env["onehr.discipline.case"].with_user(
            self.hrbp
        ).create(self.case_values(**extra))

    def move_case_to_decision(self, case=None):
        case = case or self.make_case()
        case.with_user(self.hrbp).action_start_investigation()
        case.with_user(self.hrbp).write(
            {
                "investigation_findings": (
                    "<p>Relevant evidence was reviewed and documented.</p>"
                ),
                "investigation_recommendation": (
                    "Proceed to formal hearing for employee clarification."
                ),
                "evidence_assessment": "supported",
                "hearing_scheduled_at": (
                    fields.Datetime.now() + timedelta(days=1)
                ),
            }
        )
        case.with_user(self.hrbp).action_move_to_hearing()
        case.with_user(self.hrbp).write(
            {
                "hearing_minutes": (
                    "<p>Employee received the allegation and provided clarification.</p>"
                ),
                "employee_statement": (
                    "<p>Employee clarification was recorded.</p>"
                ),
                "witness_statement": (
                    "<p>Relevant witness evidence was reviewed.</p>"
                ),
                "hearing_recommendation": (
                    "Proceed to a proportionate written decision."
                ),
            }
        )
        case.with_user(self.hrbp).action_move_to_decision()
        case.invalidate_recordset()
        return case

    def make_sanction(self, case=None, **extra):
        case = case or self.move_case_to_decision()
        if case.final_disposition == "pending":
            case.with_user(self.hrbp).write(
                {
                    "final_disposition": "sanction",
                    "decision_summary": (
                        "<p>Formal sanction is the proportionate case outcome.</p>"
                    ),
                    "decision_rationale": (
                        "<p>Decision follows documented investigation and hearing evidence.</p>"
                    ),
                }
            )
        values = {
            "case_id": case.id,
            "sanction_type": "written_warning",
            "decision_basis": (
                "<p>Decision based on documented findings and hearing.</p>"
            ),
            "sanction_terms": (
                "<p>Written warning with clear conduct expectations.</p>"
            ),
        }
        values.update(extra)
        return self.env["onehr.discipline.sanction"].with_user(
            self.hrbp
        ).create(values)

    def latest_request(self, sanction):
        return self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", "onehr.discipline.sanction"),
                ("source_res_id", "=", sanction.id),
            ],
            order="requested_at desc, id desc",
            limit=1,
        )

    def approve_sanction(self, sanction=None):
        sanction = sanction or self.make_sanction()
        sanction.with_user(
            self.hrbp
        ).action_submit_for_sanction_approval()
        request = self.latest_request(sanction)
        request.with_user(self.legal).action_approve()
        sanction.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(sanction.state, "approved")
        self.assertEqual(request.state, "approved")
        return sanction, request

    def execute_sanction(self, sanction=None):
        sanction, request = (
            self.approve_sanction(sanction)
            if sanction
            else self.approve_sanction()
        )
        sanction.with_user(self.legal).action_execute()
        sanction.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(sanction.state, "executed")
        self.assertEqual(request.state, "executed")
        return sanction

    def close_no_action_case(self, case=None):
        case = self.move_case_to_decision(case)
        case.with_user(self.hrbp).write(
            {
                "final_disposition": "no_action",
                "decision_summary": (
                    "<p>No formal disciplinary action after full review.</p>"
                ),
                "decision_rationale": (
                    "<p>Case resolved through fair-process review.</p>"
                ),
            }
        )
        case.with_user(self.manager).action_close_case()
        case.invalidate_recordset()
        self.assertEqual(case.state, "closed")
        return case
