
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRSecurityCommon


@tagged("post_install", "-at_install", "onehr_security")
class TestSecurityRulesAndLifecycle(OneHRSecurityCommon):
    def test_09_company_rule_and_self_scope(self):
        role_company_1 = self._role("C1", company=self.company)
        role_company_2 = self._role("C2", company=self.other_company)

        visible_role_ids = self.env["onehr.role"].with_user(self.manager).search([]).ids
        self.assertIn(role_company_1.id, visible_role_ids)
        self.assertNotIn(role_company_2.id, visible_role_ids)

        own_assignment = self._assignment(role_company_1, user=self.security_user)
        other_assignment = self._assignment(role_company_1, user=self.target_user)

        visible_assignment_ids = self.env["onehr.user.role"].with_user(self.security_user).search([]).ids
        self.assertIn(own_assignment.id, visible_assignment_ids)
        self.assertNotIn(other_assignment.id, visible_assignment_ids)

        with self.assertRaises(AccessError):
            self.env["onehr.audit.log"].with_user(self.security_user).search([])

    def test_10_direct_active_creation_and_overlap_are_blocked(self):
        role = self._role("OVERLAP")

        with self.assertRaises(AccessError):
            self.env["onehr.user.role"].with_user(self.manager).create(
                {
                    "user_id": self.target_user.id,
                    "role_id": role.id,
                    "company_id": self.company.id,
                    "state": "active",
                }
            )

        today = fields.Date.today()
        first = self._assignment(
            role,
            valid_from=today,
            valid_to=today + timedelta(days=10),
        )
        first.with_user(self.manager).action_activate()

        second = self._assignment(
            role,
            valid_from=today + timedelta(days=5),
            valid_to=today + timedelta(days=20),
        )
        with self.assertRaises(ValidationError):
            second.with_user(self.manager).action_activate()

    def test_11_effective_date_expiry_removes_managed_group(self):
        role = self._role("DATED", group=self.functional_group_a)
        today = fields.Date.today()
        assignment = self._assignment(
            role,
            valid_from=today - timedelta(days=10),
            valid_to=today + timedelta(days=10),
        )
        assignment.with_user(self.manager).action_activate()
        self.target_user.invalidate_recordset(["group_ids"])
        self.assertIn(self.functional_group_a, self.target_user.group_ids)

        assignment.with_user(self.manager).write({"valid_to": today - timedelta(days=1)})
        self.target_user.invalidate_recordset(["group_ids"])
        self.assertNotIn(self.functional_group_a, self.target_user.group_ids)
        self.assertIn(self.manual_group, self.target_user.group_ids)

        future = self._assignment(
            role,
            user=self.security_user,
            valid_from=today + timedelta(days=5),
        )
        future.with_user(self.manager).action_activate()
        self.security_user.invalidate_recordset(["group_ids"])
        self.assertNotIn(self.functional_group_a, self.security_user.group_ids)

    def test_12_raw_user_group_edit_is_denied_to_manager_but_role_action_works(self):
        role = self._role("CONTROLLED", group=self.functional_group_a)

        with self.assertRaises(AccessError):
            self.target_user.with_user(self.manager).write(
                {"group_ids": [Command.link(self.functional_group_b.id)]}
            )

        assignment = self._assignment(role)
        assignment.with_user(self.manager).action_activate()
        self.target_user.invalidate_recordset(["group_ids"])
        self.assertIn(self.functional_group_a, self.target_user.group_ids)

        with self.assertRaises(AccessError):
            self.target_user.with_user(self.admin).write(
                {"group_ids": [Command.link(self.functional_group_b.id)]}
            )

        admin_user_model = self.env["res.users"].with_user(self.admin)
        safe_default_groups = admin_user_model._default_groups()

        provisioned = admin_user_model.with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Provisioned by OneHR Security Admin",
                "login": "onehr_security_provisioned_test",
                "company_id": self.company.id,
                "role": "group_user",
                "group_ids": [Command.set(safe_default_groups.ids)],
            }
        )
        self.assertEqual(provisioned.company_id, self.company)
        self.assertIn(self.company, provisioned.company_ids)
        self.assertNotIn(self.functional_group_b, provisioned.group_ids)
