
# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRBranchCommon


@tagged("post_install", "-at_install", "onehr_multicompany_branch")
class TestRoleBranchIntegration(OneHRBranchCommon):
    def test_13_role_branch_must_match_company_user_scope_and_dates(self):
        role = self.make_role("SCOPE-CHECK")
        with self.assertRaises(ValidationError):
            self.make_assignment(role, user=self.target_b, branch=self.branch_a)

        future = self.env["onehr.branch"].create(
            {
                "code": "FUTURE",
                "name": "Future Branch",
                "company_id": self.company.id,
                "valid_from": self.today + timedelta(days=10),
            }
        )
        self.target_user.write({"onehr_allowed_branch_ids": [(4, future.id)]})
        with self.assertRaises(ValidationError):
            self.make_assignment(role, branch=future, valid_from=self.today)

        self.company.write({"onehr_branch_enabled": False})
        with self.assertRaises(ValidationError):
            self.make_assignment(role, branch=self.branch_a, valid_from=self.today)
        self.company.write({"onehr_branch_enabled": True})

    def test_14_same_role_can_be_separate_by_branch_but_not_duplicate_same_branch(self):
        role = self.make_role("BRANCH-SEPARATE")
        first = self.make_assignment(role, branch=self.branch_a)
        first.with_user(self.security_manager_all).action_activate()

        second = self.make_assignment(role, branch=self.branch_b)
        second.with_user(self.security_manager_all).action_activate()
        self.assertEqual(second.state, "active")

        duplicate = self.make_assignment(role, branch=self.branch_a)
        with self.assertRaises(ValidationError):
            duplicate.with_user(self.security_manager_all).action_activate()

    def test_15_company_wide_role_scope_overlaps_every_branch(self):
        role = self.make_role("COMPANY-WIDE")
        branch_row = self.make_assignment(role, branch=self.branch_a)
        branch_row.with_user(self.security_manager_all).action_activate()

        company_row = self.make_assignment(role, branch=None)
        with self.assertRaises(ValidationError):
            company_row.with_user(self.security_manager_all).action_activate()

    def test_16_sod_peer_resolution_is_branch_aware(self):
        role_a = self.make_role("SOD-A")
        role_b = self.make_role("SOD-B")
        self.env["onehr.sod.matrix"].create(
            {
                "code": "BRANCH-SOD",
                "name": "Branch-aware SoD",
                "company_id": self.company.id,
                "role_a_id": role_a.id,
                "role_b_id": role_b.id,
                "enforcement": "deny",
            }
        )

        first = self.make_assignment(role_a, branch=self.branch_a)
        first.with_user(self.security_manager_all).action_activate()

        other_branch = self.make_assignment(role_b, branch=self.branch_b)
        other_branch.with_user(self.security_manager_all).action_activate()
        self.assertEqual(other_branch.state, "active")

        same_branch = self.make_assignment(role_b, user=self.target_user, branch=self.branch_a)
        same_branch.with_user(self.security_manager_all).action_activate()
        self.assertEqual(same_branch.state, "blocked")

    def test_17_branch_role_drives_managed_group_reconciliation(self):
        role = self.make_role("BRANCH-GROUP", group=self.functional_group_a)
        assignment = self.make_assignment(role, branch=self.branch_a)
        assignment.with_user(self.security_manager_all).action_activate()

        self.target_user.invalidate_recordset(["group_ids"])
        self.assertIn(self.functional_group_a, self.target_user.group_ids)
        self.assertIn(self.functional_group_a, self.target_user._onehr_desired_group_ids())

        assignment.with_user(self.security_manager_all).action_revoke()
        self.target_user.invalidate_recordset(["group_ids"])
        self.assertNotIn(self.functional_group_a, self.target_user.group_ids)

    def test_18_security_manager_role_visibility_is_narrowed_by_allowed_branch(self):
        role_a = self.make_role("VISIBLE-A")
        role_b = self.make_role("HIDDEN-B")
        row_a = self.make_assignment(role_a, branch=self.branch_a)
        row_b = self.make_assignment(role_b, branch=self.branch_b)

        visible_ids = self.env["onehr.user.role"].with_user(self.security_manager_a).search([]).ids
        self.assertIn(row_a.id, visible_ids)
        self.assertNotIn(row_b.id, visible_ids)

        all_ids = self.env["onehr.user.role"].with_user(self.security_manager_all).search([]).ids
        self.assertIn(row_a.id, all_ids)
        self.assertIn(row_b.id, all_ids)

