# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRBranchCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Branch Other Company"})

        cls.branch_a = cls.env["onehr.branch"].create(
            {
                "code": "A",
                "name": "Branch A",
                "company_id": cls.company.id,
                "valid_from": cls.today - timedelta(days=30),
            }
        )
        cls.branch_b = cls.env["onehr.branch"].create(
            {
                "code": "B",
                "name": "Branch B",
                "company_id": cls.company.id,
                "valid_from": cls.today - timedelta(days=30),
            }
        )
        cls.other_branch = cls.env["onehr.branch"].create(
            {
                "code": "OTHER",
                "name": "Other Company Branch",
                "company_id": cls.other_company.id,
                "valid_from": cls.today - timedelta(days=30),
            }
        )

        cls.group_branch_user = cls.env.ref("onehr_multicompany_branch.group_onehr_branch_user")
        cls.group_branch_manager = cls.env.ref("onehr_multicompany_branch.group_onehr_branch_manager")
        cls.group_branch_admin = cls.env.ref("onehr_multicompany_branch.group_onehr_branch_admin")
        cls.group_central = cls.env.ref("onehr_multicompany_branch.group_onehr_central_office")
        cls.group_security_manager = cls.env.ref("onehr_security.group_onehr_security_manager")

        cls.functional_group_a = cls.env["res.groups"].create({"name": "OneHR Branch Functional A"})
        cls.functional_group_b = cls.env["res.groups"].create({"name": "OneHR Branch Functional B"})

        def make_user(name, login, groups, branches=None, companies=None):
            branches = branches or cls.env["onehr.branch"]
            companies = companies or cls.company
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": cls.company.id,
                    "company_ids": [Command.set(companies.ids)],
                    "group_ids": [Command.set(groups.ids)],
                    "onehr_allowed_branch_ids": [Command.set(branches.ids)],
                }
            )

        cls.branch_user = make_user(
            "OneHR Branch User",
            "onehr_branch_user_test",
            cls.group_branch_user,
            cls.branch_a,
        )
        cls.branch_manager = make_user(
            "OneHR Branch Manager",
            "onehr_branch_manager_test",
            cls.group_branch_manager,
            cls.branch_a,
        )
        cls.branch_admin = make_user(
            "OneHR Branch Admin",
            "onehr_branch_admin_test",
            cls.group_branch_admin,
            cls.branch_a,
        )
        cls.central = make_user(
            "OneHR Central Office",
            "onehr_central_test",
            cls.group_central,
            cls.branch_a | cls.branch_b,
        )
        cls.security_manager_a = make_user(
            "OneHR Security Manager A",
            "onehr_security_manager_a_test",
            cls.group_security_manager,
            cls.branch_a,
        )
        cls.security_manager_all = make_user(
            "OneHR Security Manager All",
            "onehr_security_manager_all_test",
            cls.group_security_manager,
            cls.branch_a | cls.branch_b,
        )
        cls.target_user = make_user(
            "OneHR Branch Target",
            "onehr_branch_target_test",
            cls.env.ref("base.group_user"),
            cls.branch_a | cls.branch_b,
        )
        cls.target_b = make_user(
            "OneHR Branch Target B",
            "onehr_branch_target_b_test",
            cls.env.ref("base.group_user"),
            cls.branch_b,
        )

    def make_role(self, code, group=None, company=None):
        role = self.env["onehr.role"].create(
            {
                "code": code,
                "name": code,
                "company_id": (company or self.company).id,
            }
        )
        if group:
            role.group_ids = [Command.set(group.ids)]
        return role

    def make_assignment(self, role, *, user=None, branch=None, company=None, **extra):
        vals = {
            "user_id": (user or self.target_user).id,
            "role_id": role.id,
            "company_id": (company or self.company).id,
            "branch_id": branch.id if branch else False,
        }
        vals.update(extra)
        return self.env["onehr.user.role"].create(vals)
