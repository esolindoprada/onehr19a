from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRRecruitmentCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Recruitment Other Company"})

        cls.group_recruiter = cls.env.ref("onehr_recruitment.group_onehr_recruiter")
        cls.group_hiring_manager = cls.env.ref("onehr_recruitment.group_onehr_hiring_manager")
        cls.group_manager = cls.env.ref("onehr_recruitment.group_onehr_recruitment_manager")

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

        cls.recruiter = make_user("OneHR Recruiter Test", "onehr_recruiter_test", cls.group_recruiter)
        cls.hiring_manager = make_user("OneHR Hiring Manager Test", "onehr_hiring_manager_test", cls.group_hiring_manager)
        cls.manager = make_user(
            "OneHR Recruitment Manager Test", "onehr_recruitment_manager_test", cls.group_manager,
            companies=[cls.company, cls.other_company],
        )
        cls.other_company_recruiter = make_user(
            "Other Company Recruiter", "onehr_other_recruiter_test", cls.group_recruiter,
            company=cls.other_company, companies=[cls.other_company],
        )

        cls.department = cls.env["hr.department"].create({"name": "Recruitment Test Department", "company_id": cls.company.id})
        cls.job = cls.env["hr.job"].create({
            "name": "Recruitment Test Engineer",
            "company_id": cls.company.id,
            "department_id": cls.department.id,
            "interviewer_ids": [Command.link(cls.hiring_manager.id)],
        })
        cls.other_job = cls.env["hr.job"].create({"name": "Other Company Job", "company_id": cls.other_company.id})

        cls.requisition = cls.env["onehr.recruitment.requisition"].with_user(cls.manager).create({
            "title": "Engineer Replacement",
            "company_id": cls.company.id,
            "job_id": cls.job.id,
            "hiring_manager_user_id": cls.hiring_manager.id,
            "recruiter_user_id": cls.recruiter.id,
            "requested_headcount": 1,
            "employment_basis": "replacement",
            "reason": "Replace a confirmed vacancy with governed headcount evidence.",
        })
        cls.applicant = cls.env["hr.applicant"].with_user(cls.recruiter).create({
            "partner_name": "Recruitment Candidate",
            "email_from": "candidate@example.test",
            "job_id": cls.job.id,
            "company_id": cls.company.id,
            "user_id": cls.recruiter.id,
            "interviewer_ids": [Command.link(cls.hiring_manager.id)],
            "onehr_requisition_id": cls.requisition.id,
        })
        cls.template = cls.env["onehr.interview.template"].with_user(cls.manager).create({
            "code": "INT-ENG",
            "name": "Engineering Structured Interview",
            "company_id": cls.company.id,
            "job_id": cls.job.id,
            "valid_from": fields.Date.today() - timedelta(days=1),
            "duration_minutes": 60,
            "minimum_overall_score": 3.0,
        })
        cls.template.with_user(cls.manager).action_activate()

    def make_session(self, **overrides):
        values = {
            "applicant_id": self.applicant.id,
            "requisition_id": self.requisition.id,
            "template_id": self.template.id,
            "scheduled_start": fields.Datetime.now() + timedelta(days=1),
            "scheduled_end": fields.Datetime.now() + timedelta(days=1, hours=1),
            "interviewer_user_ids": [Command.link(self.hiring_manager.id)],
            "lead_interviewer_user_id": self.hiring_manager.id,
        }
        values.update(overrides)
        return self.env["onehr.interview.session"].with_user(self.manager).create(values)

    def make_offer(self, **overrides):
        values = {
            "applicant_id": self.applicant.id,
            "requisition_id": self.requisition.id,
            "offer_date": fields.Date.today(),
            "expiry_date": fields.Date.today() + timedelta(days=7),
            "proposed_start_date": fields.Date.today() + timedelta(days=30),
            "base_salary": 10000000,
            "variable_compensation": 1000000,
            "other_compensation": 500000,
            "terms": "<p>Standard governed recruitment offer.</p>",
        }
        values.update(overrides)
        return self.env["onehr.offer"].with_user(self.manager).create(values)
