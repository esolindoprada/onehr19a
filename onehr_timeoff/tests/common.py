from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRTimeOffCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Time Off Other Company"})

        cls.group_user = cls.env.ref("onehr_timeoff.group_onehr_timeoff_user")
        cls.group_manager = cls.env.ref("onehr_timeoff.group_onehr_timeoff_manager")
        cls.group_hr = cls.env.ref("onehr_timeoff.group_onehr_timeoff_hr")

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

        cls.employee_user = make_user("Time Off Employee User", "timeoff_employee_test", cls.group_user)
        cls.manager_user = make_user("Time Off Manager", "timeoff_manager_test", cls.group_manager)
        cls.hr_user = make_user(
            "Time Off HR", "timeoff_hr_test", cls.group_hr, companies=[cls.company, cls.other_company]
        )
        cls.other_user = make_user(
            "Other Company Time Off HR", "timeoff_other_hr_test", cls.group_hr,
            company=cls.other_company, companies=[cls.other_company],
        )

        cls.department = cls.env["hr.department"].create({
            "name": "Time Off Engineering", "company_id": cls.company.id, "onehr_code": "TO-ENG",
        })
        cls.manager_employee = cls.env["hr.employee"].create({
            "name": "Time Off Reporting Manager", "company_id": cls.company.id,
            "department_id": cls.department.id, "user_id": cls.manager_user.id,
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Time Off Employee", "company_id": cls.company.id,
            "department_id": cls.department.id, "parent_id": cls.manager_employee.id,
            "user_id": cls.employee_user.id,
        })
        cls.other_employee = cls.env["hr.employee"].create({
            "name": "Other Company Employee", "company_id": cls.other_company.id,
            "user_id": cls.other_user.id,
        })

        # Use a future Monday so request-duration tests are deterministic.
        candidate = fields.Date.today() + timedelta(days=7)
        while candidate.weekday() != 0:
            candidate += timedelta(days=1)
        cls.future_monday = candidate
        cls.year_start = candidate.replace(month=1, day=1)
        cls.year_end = candidate.replace(month=12, day=31)

        cls.leave_type = cls.env["onehr.leave.type"].with_user(cls.hr_user).create({
            "name": "Annual Leave Test",
            "code": "ANNUAL-TEST",
            "company_id": cls.company.id,
            "category": "annual",
            "approval_required": False,
            "allocation_required": True,
            "valid_from": cls.year_start,
            "base_accrual_days": 1.0,
        })
        cls.leave_type.with_user(cls.hr_user).action_activate()

    def make_allocation(self, employee=None, days=10.0, leave_type=None, **overrides):
        values = {
            "company_id": self.company.id,
            "allocation_scope": "single",
            "employee_id": (employee or self.employee).id,
            "leave_type_id": (leave_type or self.leave_type).id,
            "source": "manual",
            "period_start": self.year_start,
            "period_end": self.year_end,
            "allocated_days": days,
        }
        values.update(overrides)
        allocation = self.env["onehr.leave.allocation"].with_user(self.hr_user).create(values)
        allocation.with_user(self.hr_user).action_confirm()
        return allocation

    def make_request(self, **overrides):
        values = {
            "leave_type_id": self.leave_type.id,
            "date_from": self.future_monday,
            "date_to": self.future_monday,
            "reason": "Automated Time Off test",
        }
        values.update(overrides)
        return self.env["onehr.leave.request"].with_user(self.employee_user).create(values)
