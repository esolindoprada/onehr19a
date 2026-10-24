

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "OneHR Other Company"}
        )
        cls.department = cls.env["hr.department"].create(
            {
                "name": "Engineering",
                "company_id": cls.company.id,
                "onehr_code": "ENG",
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Engineer",
                "company_id": cls.company.id,
                "onehr_code": "ENG-JOB",
            }
        )
        cls.work_address = cls.env["res.partner"].create(
            {"name": "Head Office Address"}
        )
        cls.location = cls.env["hr.work.location"].create(
            {
                "name": "Head Office",
                "company_id": cls.company.id,
                "address_id": cls.work_address.id,
                "onehr_site_code": "HQ",
            }
        )
        cls.grade = cls.env["onehr.grade"].create(
            {
                "code": "G1",
                "name": "Grade 1",
                "company_id": cls.company.id,
            }
        )
        cls.position = cls.env["onehr.position"].create(
            {
                "code": "POS-1",
                "name": "Engineer Seat",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "work_location_id": cls.location.id,
                "grade_id": cls.grade.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Test Employee", "company_id": cls.company.id}
        )
        cls.officer = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "OneHR Officer",
                "login": "onehr_officer",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.link(cls.env.ref("hr.group_hr_user").id)],
            }
        )
        cls.manager = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "OneHR Manager",
                "login": "onehr_manager",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.link(cls.env.ref("hr.group_hr_manager").id)],
            }
        )

    @classmethod
    def active_template(cls, code="ONBOARD", version=1, date=None):
        date = date or fields.Date.today()
        return cls.env["onehr.checklist.template"].create(
            {
                "code": code,
                "name": "Onboarding",
                "version": version,
                "lifecycle_event_type_id": cls.env.ref(
                    "onehr_base.lifecycle_event_hire"
                ).id,
                "company_id": cls.company.id,
                "valid_from": date,
                "state": "draft",
            }
        )
