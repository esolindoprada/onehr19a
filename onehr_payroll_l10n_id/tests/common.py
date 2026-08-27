from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRPayrollL10nIdCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "OneHR L10n Other Company"}
        )
        cls.group_officer = cls.env.ref(
            "onehr_payroll_bridge.group_onehr_payroll_officer"
        )
        cls.group_manager = cls.env.ref(
            "onehr_payroll_bridge.group_onehr_payroll_manager"
        )

        def make_user(name, login, groups, companies):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": companies[0].id,
                    "company_ids": [Command.set([company.id for company in companies])],
                    "group_ids": [Command.set(groups.ids)],
                }
            )

        cls.manager = make_user(
            "Indonesia Payroll Manager Test",
            "onehr_l10n_manager_test",
            cls.group_manager,
            [cls.company, cls.other_company],
        )
        cls.officer = make_user(
            "Indonesia Payroll Officer Test",
            "onehr_l10n_officer_test",
            cls.group_officer,
            [cls.company],
        )
        cls.plain_user = make_user(
            "Indonesia Payroll Plain User Test",
            "onehr_l10n_plain_test",
            cls.env.ref("base.group_user"),
            [cls.company],
        )

        cls.department = cls.env["hr.department"].create(
            {"name": "Indonesia Payroll Test", "company_id": cls.company.id}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Indonesia Payroll Employee",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "onehr_employee_number": "IDPAY-001",
            }
        )

    def make_parameter(self, **overrides):
        values = {
            "name": "Indonesia Payroll Parameters",
            "code": overrides.pop("code", "ID-PAYROLL"),
            "company_id": overrides.pop("company_id", self.company.id),
            "valid_from": overrides.pop("valid_from", fields.Date.today()),
        }
        values.update(overrides)
        return self.env["onehr.payroll.l10n.param"].with_user(self.manager).create(values)

    def review_parameter(self, parameter=None):
        parameter = parameter or self.make_parameter()
        parameter.with_user(self.manager).action_mark_regulatory_reviewed()
        return parameter

    def make_bridge_config(self):
        return self.env["onehr.payroll.bridge.config"].with_user(self.manager).create(
            {
                "name": "Indonesia Payroll Vendor",
                "code": "ID-VENDOR",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "external_system_code": "IDVENDOR",
                "provider_mode": "csv_manual",
                "include_work_entries": False,
                "include_attendance": False,
                "include_overtime": False,
                "include_timeoff": False,
                "include_assignment_costing": False,
            }
        )

    def make_export(self, period_end=None):
        period_end = period_end or fields.Date.today()
        period_start = period_end.replace(day=1)
        config = self.make_bridge_config()
        return self.env["onehr.payroll.export"].with_user(self.officer).create(
            {
                "config_id": config.id,
                "period_start": period_start,
                "period_end": period_end,
                "employee_ids": [Command.set(self.employee.ids)],
            }
        )
