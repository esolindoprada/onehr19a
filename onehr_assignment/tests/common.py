from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRAssignmentCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Assignment Other Company"})

        cls.group_proposer = cls.env.ref("onehr_assignment.group_onehr_assignment_proposer")
        cls.group_officer = cls.env.ref("onehr_assignment.group_onehr_assignment_officer")
        cls.group_manager = cls.env.ref("onehr_assignment.group_onehr_assignment_manager")

        def make_user(name, login, group, company=None, companies=None):
            company = company or cls.company
            companies = companies or [company]
            return cls.env["res.users"].with_context(no_reset_password=True).create({
                "name": name,
                "login": login,
                "company_id": company.id,
                "company_ids": [Command.set([item.id for item in companies])],
                "group_ids": [Command.set(group.ids)],
            })

        cls.proposer = make_user("Assignment Unit Manager", "assignment_proposer_test", cls.group_proposer)
        cls.officer = make_user("Assignment Officer", "assignment_officer_test", cls.group_officer)
        cls.manager = make_user(
            "Assignment Manager", "assignment_manager_test", cls.group_manager,
            companies=[cls.company, cls.other_company],
        )
        cls.other_officer = make_user(
            "Other Assignment Officer", "assignment_other_officer_test", cls.group_officer,
            company=cls.other_company, companies=[cls.other_company],
        )

        cls.department = cls.env["hr.department"].create({
            "name": "Assignment Engineering", "company_id": cls.company.id, "onehr_code": "ASG-ENG",
        })
        cls.job = cls.env["hr.job"].create({
            "name": "Assignment Engineer", "company_id": cls.company.id, "onehr_code": "ASG-JOB",
        })
        cls.work_address = cls.env["res.partner"].create({"name": "Assignment HQ Address"})
        cls.location = cls.env["hr.work.location"].create({
            "name": "Assignment HQ", "company_id": cls.company.id,
            "address_id": cls.work_address.id, "onehr_site_code": "ASG-HQ",
        })
        cls.grade = cls.env["onehr.grade"].create({
            "code": "ASG-G1", "name": "Assignment Grade 1", "company_id": cls.company.id,
        })
        cls.position = cls.env["onehr.position"].create({
            "code": "ASG-POS-1", "name": "Assignment Engineer Seat",
            "company_id": cls.company.id, "department_id": cls.department.id,
            "job_id": cls.job.id, "work_location_id": cls.location.id,
            "grade_id": cls.grade.id, "authorized_headcount": 2,
            "authorized_fte": 2.0, "status": "open",
        })
        cls.position_2 = cls.env["onehr.position"].create({
            "code": "ASG-POS-2", "name": "Assignment Senior Engineer Seat",
            "company_id": cls.company.id, "department_id": cls.department.id,
            "job_id": cls.job.id, "work_location_id": cls.location.id,
            "grade_id": cls.grade.id, "authorized_headcount": 2,
            "authorized_fte": 2.0, "status": "open",
        })
        cls.position_tight = cls.env["onehr.position"].create({
            "code": "ASG-POS-TIGHT", "name": "Assignment Controlled Seat",
            "company_id": cls.company.id, "department_id": cls.department.id,
            "job_id": cls.job.id, "work_location_id": cls.location.id,
            "grade_id": cls.grade.id, "authorized_headcount": 1,
            "authorized_fte": 1.0, "status": "open",
        })

        cls.manager_employee = cls.env["hr.employee"].create({
            "name": "Assignment Reporting Manager", "company_id": cls.company.id,
            "user_id": cls.proposer.id,
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Assignment Employee", "company_id": cls.company.id,
            "parent_id": cls.manager_employee.id,
        })
        cls.employee_2 = cls.env["hr.employee"].create({
            "name": "Assignment Employee Two", "company_id": cls.company.id,
            "parent_id": cls.manager_employee.id,
        })
        cls.unrelated_manager_user = make_user(
            "Unrelated Unit Manager", "assignment_unrelated_manager_test", cls.group_proposer,
        )
        cls.unrelated_manager_employee = cls.env["hr.employee"].create({
            "name": "Unrelated Reporting Manager", "company_id": cls.company.id,
            "user_id": cls.unrelated_manager_user.id,
        })
        cls.unrelated_employee = cls.env["hr.employee"].create({
            "name": "Unrelated Employee", "company_id": cls.company.id,
            "parent_id": cls.unrelated_manager_employee.id,
        })

        cls.other_department = cls.env["hr.department"].create({
            "name": "Other Assignment Department", "company_id": cls.other_company.id,
            "onehr_code": "ASG-OTH-DEP",
        })
        cls.other_job = cls.env["hr.job"].create({
            "name": "Other Assignment Job", "company_id": cls.other_company.id,
            "onehr_code": "ASG-OTH-JOB",
        })
        cls.other_grade = cls.env["onehr.grade"].create({
            "code": "ASG-OTH-G1", "name": "Other Assignment Grade", "company_id": cls.other_company.id,
        })
        cls.other_position = cls.env["onehr.position"].create({
            "code": "ASG-OTH-POS", "name": "Other Assignment Position",
            "company_id": cls.other_company.id, "department_id": cls.other_department.id,
            "job_id": cls.other_job.id, "grade_id": cls.other_grade.id,
            "authorized_headcount": 1, "authorized_fte": 1.0, "status": "open",
        })
        cls.other_employee = cls.env["hr.employee"].create({
            "name": "Other Assignment Employee", "company_id": cls.other_company.id,
        })

    def make_assignment(self, **overrides):
        values = {
            "company_id": self.company.id,
            "employee_id": self.employee.id,
            "assignment_type": "primary",
            "movement_type": "initial",
            "position_id": self.position.id,
            "manager_id": self.manager_employee.id,
            "effective_from": fields.Date.today(),
            "fte": 1.0,
        }
        values.update(overrides)
        return self.env["onehr.assignment"].with_user(self.officer).create(values)

    def force_approved(self, assignment, user=None):
        user = user or self.manager
        assignment.with_user(user).with_context(
            onehr_assignment_state_controlled=True,
            onehr_assignment_evidence_controlled=True,
        ).write({
            "state": "approved",
            "approved_at": fields.Datetime.now(),
            "approved_by_id": user.id,
        })
        return assignment

    def force_active(self, assignment, user=None):
        user = user or self.manager
        self.force_approved(assignment, user=user)
        assignment.with_user(user)._activate_from_governed_execution()
        return assignment

    def make_future_dates(self, days=30, duration=90):
        start = fields.Date.today() + timedelta(days=days)
        return start, start + timedelta(days=duration)
