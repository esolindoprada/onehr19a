
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRSecurityCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Security Other Company"})

        cls.group_security_user = cls.env.ref("onehr_security.group_onehr_security_user")
        cls.group_security_manager = cls.env.ref("onehr_security.group_onehr_security_manager")
        cls.group_security_admin = cls.env.ref("onehr_security.group_onehr_security_admin")
        cls.group_compliance = cls.env.ref("onehr_security.group_onehr_compliance_officer")

        cls.functional_group_a = cls.env["res.groups"].create({"name": "OneHR Test Functional A"})
        cls.functional_group_b = cls.env["res.groups"].create({"name": "OneHR Test Functional B"})
        cls.manual_group = cls.env["res.groups"].create({"name": "OneHR Test Manual Preservation"})

        def make_user(name, login, groups, companies=None):
            companies = companies or cls.company
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": cls.company.id,
                    "company_ids": [Command.set(companies.ids)],
                    "group_ids": [Command.set(groups.ids)],
                }
            )

        cls.security_user = make_user(
            "OneHR Security User",
            "onehr_security_user_test",
            cls.group_security_user,
        )
        cls.manager = make_user(
            "OneHR Security Manager",
            "onehr_security_manager_test",
            cls.group_security_manager,
        )
        cls.admin = make_user(
            "OneHR Security Admin",
            "onehr_security_admin_test",
            cls.group_security_admin,
        )
        cls.compliance = make_user(
            "OneHR Compliance",
            "onehr_compliance_test",
            cls.group_compliance,
        )
        cls.target_user = make_user(
            "OneHR Target User",
            "onehr_security_target_test",
            cls.env.ref("base.group_user") | cls.manual_group,
        )

    def _role(self, code, group=None, company=None, **extra):
        vals = {
            "code": code,
            "name": code,
            "company_id": company.id if company else False,
        }
        vals.update(extra)
        role = self.env["onehr.role"].create(vals)
        if group:
            role.group_ids = [Command.set(group.ids)]
        return role

    def _assignment(self, role, user=None, company=None, **extra):
        vals = {
            "user_id": (user or self.target_user).id,
            "role_id": role.id,
            "company_id": (company or self.company).id,
        }
        vals.update(extra)
        return self.env["onehr.user.role"].create(vals)
