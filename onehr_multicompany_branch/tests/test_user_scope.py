# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRBranchCommon


@tagged("post_install", "-at_install", "onehr_multicompany_branch")
class TestUserBranchScope(OneHRBranchCommon):
    def test_07_allowed_and_default_branch_company_integrity(self):
        with self.assertRaises(ValidationError):
            self.branch_user.with_user(self.branch_admin).write(
                {"onehr_allowed_branch_ids": [Command.link(self.other_branch.id)]}
            )

        with self.assertRaises(ValidationError):
            self.branch_user.with_user(self.branch_admin).write(
                {"onehr_default_branch_id": self.branch_b.id}
            )

        self.company.write({"onehr_branch_enabled": False})
        with self.assertRaises(ValidationError):
            self.branch_user.with_user(self.branch_admin).write(
                {"onehr_default_branch_id": self.branch_a.id}
            )
        self.company.write({"onehr_branch_enabled": True})

    def test_08_controlled_quick_selector_changes_only_own_default(self):
        self.branch_b.with_user(self.central).action_set_as_my_default()
        self.central.invalidate_recordset(["onehr_default_branch_id"])
        self.assertEqual(self.central.onehr_default_branch_id, self.branch_b)

        with self.assertRaises(AccessError):
            self.other_branch.with_user(self.central).action_set_as_my_default()

    def test_09_branch_admin_acl_cannot_become_generic_user_admin(self):
        self.target_user.with_user(self.branch_admin).write(
            {"onehr_allowed_branch_ids": [Command.set([self.branch_a.id])]}
        )
        self.target_user.invalidate_recordset(["onehr_allowed_branch_ids"])
        self.assertEqual(self.target_user.onehr_allowed_branch_ids, self.branch_a)

        with self.assertRaises(AccessError):
            self.target_user.with_user(self.branch_admin).write({"name": "Unauthorized Rename"})

        # Even when the target user is multi-company, Branch Admin cannot smuggle
        # a branch from a legal company outside the administrator's own scope.
        self.target_user.write(
            {"company_ids": [Command.set([self.company.id, self.other_company.id])]}
        )
        with self.assertRaises(AccessError):
            self.target_user.with_user(self.branch_admin).write(
                {"onehr_allowed_branch_ids": [Command.link(self.other_branch.id)]}
            )

    def test_10_branch_user_record_rule_isolates_unallowed_branches(self):
        visible_ids = self.env["onehr.branch"].with_user(self.branch_user).search([]).ids
        self.assertIn(self.branch_a.id, visible_ids)
        self.assertNotIn(self.branch_b.id, visible_ids)
        self.assertNotIn(self.other_branch.id, visible_ids)

        admin_ids = self.env["onehr.branch"].with_user(self.branch_admin).search([]).ids
        self.assertIn(self.branch_a.id, admin_ids)
        self.assertIn(self.branch_b.id, admin_ids)
        self.assertNotIn(self.other_branch.id, admin_ids)

    def test_11_central_office_visibility_is_explicit_not_company_wide(self):
        visible_ids = self.env["onehr.branch"].with_user(self.central).search([]).ids
        self.assertIn(self.branch_a.id, visible_ids)
        self.assertIn(self.branch_b.id, visible_ids)
        self.assertNotIn(self.other_branch.id, visible_ids)

        self.central.with_user(self.env.user).write(
            {"onehr_allowed_branch_ids": [Command.set([self.branch_a.id])]}
        )
        visible_ids = self.env["onehr.branch"].with_user(self.central).search([]).ids
        self.assertEqual(set(visible_ids), {self.branch_a.id})

    def test_12_effective_role_blocks_branch_scope_removal(self):
        role = self.make_role("SCOPE-REMOVAL")
        assignment = self.make_assignment(role, branch=self.branch_a)
        assignment.with_user(self.security_manager_all).action_activate()

        with self.assertRaises(ValidationError):
            self.target_user.with_user(self.branch_admin).write(
                {"onehr_allowed_branch_ids": [Command.set([self.branch_b.id])]}
            )
