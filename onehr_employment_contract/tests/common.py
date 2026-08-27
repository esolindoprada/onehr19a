from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRContractCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "OneHR Contract Other Company"}
        )

        def make_user(name, login, group, company=None, companies=None):
            company = company or cls.company
            companies = companies or [company]
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([item.id for item in companies])],
                    "group_ids": [Command.set([group.id])],
                }
            )

        cls.group_line = cls.env.ref(
            "onehr_employment_contract.group_onehr_contract_line_manager"
        )
        cls.group_officer = cls.env.ref(
            "onehr_employment_contract.group_onehr_contract_officer"
        )
        cls.group_manager = cls.env.ref(
            "onehr_employment_contract.group_onehr_contract_manager"
        )

        cls.line_user = make_user(
            "Contract Line Manager",
            "contract_line_test",
            cls.group_line,
        )
        cls.officer = make_user(
            "Contract Officer",
            "contract_officer_test",
            cls.group_officer,
        )
        cls.manager = make_user(
            "Contract Manager",
            "contract_manager_test",
            cls.group_manager,
            companies=[cls.company, cls.other_company],
        )

        cls.manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Line Manager Employee",
                "company_id": cls.company.id,
                "user_id": cls.line_user.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Contract Employee",
                "company_id": cls.company.id,
                "parent_id": cls.manager_employee.id,
                "contract_date_start": fields.Date.today(),
                "contract_wage": 10_000_000.0,
            }
        )
        cls.version = cls.employee.version_ids.filtered(
            lambda row: row.contract_date_start
        )[:1]

        cls.template = cls.env["onehr.contract.template"].with_user(
            cls.manager
        ).create(
            {
                "code": "PERM",
                "name": "Permanent Employment",
                "company_id": cls.company.id,
                "valid_from": fields.Date.today(),
                "state": "draft",
            }
        )
        cls.template.with_user(cls.manager).action_activate()

    def make_contract(self, **overrides):
        values = {
            "employee_id": self.employee.id,
            "company_id": self.company.id,
            "hr_version_id": self.version.id,
            "template_id": self.template.id,
            "responsible_user_id": self.officer.id,
        }
        values.update(overrides)
        return self.env["onehr.contract"].with_user(self.officer).create(values)
