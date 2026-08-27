import base64
import csv
import io
from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRPayrollBridgeCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Payroll Other Company"})

        cls.group_officer = cls.env.ref("onehr_payroll_bridge.group_onehr_payroll_officer")
        cls.group_manager = cls.env.ref("onehr_payroll_bridge.group_onehr_payroll_manager")

        def make_user(name, login, group, company=None, companies=None):
            company = company or cls.company
            companies = companies or [company]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([item.id for item in companies])],
                    "group_ids": [Command.set(group.ids)],
                }
            )

        cls.officer = make_user(
            "Payroll Officer Test",
            "onehr_payroll_officer_test",
            cls.group_officer,
        )
        cls.manager = make_user(
            "Payroll Manager Test",
            "onehr_payroll_manager_test",
            cls.group_manager,
            companies=[cls.company, cls.other_company],
        )
        cls.plain_user = make_user(
            "Plain Internal User Test",
            "onehr_payroll_plain_user_test",
            cls.env.ref("base.group_user"),
        )

        cls.department = cls.env["hr.department"].create(
            {"name": "Payroll Operations", "company_id": cls.company.id}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Payroll Employee One",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "onehr_employee_number": "PAY-EMP-001",
            }
        )
        cls.employee_2 = cls.env["hr.employee"].create(
            {
                "name": "Payroll Employee Two",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "onehr_employee_number": "PAY-EMP-002",
            }
        )
        cls.employee_without_number = cls.env["hr.employee"].create(
            {
                "name": "Payroll Employee Missing Number",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
            }
        )

    def make_config(self, **overrides):
        values = {
            "name": "Primary Payroll Exchange",
            "code": "PAY-MAIN",
            "company_id": self.company.id,
            "external_system_code": "VENDOR",
            "provider_mode": "csv_manual",
            "currency_id": self.company.currency_id.id,
            "include_work_entries": False,
            "include_attendance": False,
            "include_overtime": False,
            "include_timeoff": False,
            "include_assignment_costing": False,
            "require_full_reconciliation": True,
        }
        values.update(overrides)
        return self.env["onehr.payroll.bridge.config"].with_user(self.manager).create(values)

    def make_export(self, config=None, employees=None, **overrides):
        config = config or self.make_config()
        today = fields.Date.today()
        values = {
            "config_id": config.id,
            "period_start": today.replace(day=1),
            "period_end": today,
        }
        if employees is not None:
            values["employee_ids"] = [Command.set(employees.ids)]
        values.update(overrides)
        return self.env["onehr.payroll.export"].with_user(self.officer).create(values)

    def generate_export(self, export=None, employees=None):
        export = export or self.make_export(employees=employees or (self.employee | self.employee_2))
        export.with_user(self.officer).action_generate_export()
        return export

    def post_export(self, export=None, employees=None):
        export = self.generate_export(export=export, employees=employees)
        export.with_user(self.manager).action_post_to_payroll()
        return export

    def make_import(self, export=None, employee=None, **overrides):
        export = export or self.post_export(employees=self.employee)
        employee = employee or self.employee
        values = {
            "export_id": export.id,
            "employee_id": employee.id,
            "external_reference": "EXT-%s" % employee.onehr_employee_number,
            "payslip_number": "PS-%s" % employee.onehr_employee_number,
            "gross_amount": 1000.0,
            "deduction_amount": 100.0,
            "net_amount": 900.0,
            "employer_cost": 1100.0,
            "currency_id": export.currency_id.id,
        }
        values.update(overrides)
        return self.env["onehr.payroll.import"].with_user(self.officer).create(values)

    def vendor_csv_binary(self, rows, config):
        mapping = config._parse_mapping("import_field_mapping")
        headers = [
            mapping["employee_number"],
            mapping["external_reference"],
            mapping.get("payslip_number"),
            mapping.get("payment_date"),
            mapping.get("gross_amount"),
            mapping.get("deduction_amount"),
            mapping["net_amount"],
            mapping.get("employer_cost"),
            mapping.get("currency_code"),
        ]
        headers = [item for item in headers if item]
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter=config.csv_delimiter_character())
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return base64.b64encode(stream.getvalue().encode(config.csv_encoding))
