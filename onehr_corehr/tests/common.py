from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRCoreHRCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR CoreHR Other Company"})

        cls.group_officer = cls.env.ref("onehr_corehr.group_onehr_corehr_officer")
        cls.group_manager = cls.env.ref("onehr_corehr.group_onehr_corehr_manager")
        cls.group_steward = cls.env.ref("onehr_corehr.group_onehr_identifier_steward")
        cls.group_oh = cls.env.ref("onehr_corehr.group_onehr_occupational_health_officer")

        def make_user(name, login, group, companies=None):
            companies = companies or cls.company
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": cls.company.id,
                    "company_ids": [Command.set(companies.ids)],
                    "group_ids": [Command.set(group.ids)],
                }
            )

        cls.officer = make_user("Core HR Officer", "onehr_corehr_officer_test", cls.group_officer)
        cls.manager = make_user("Core HR Manager", "onehr_corehr_manager_test", cls.group_manager)
        cls.steward = make_user("Identifier Steward", "onehr_identifier_steward_test", cls.group_steward)
        cls.oh_officer = make_user("Occupational Health Officer", "onehr_oh_officer_test", cls.group_oh)

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "OneHR CoreHR Employee",
                "company_id": cls.company.id,
                "work_email": "corehr.employee@example.test",
                "work_phone": "+62123456789",
            }
        )
