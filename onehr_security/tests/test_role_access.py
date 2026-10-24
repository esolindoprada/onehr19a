
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRSecurityCommon


@tagged("post_install", "-at_install", "onehr_security")
class TestRoleAndEffectiveAccess(OneHRSecurityCommon):
    def test_01_registry_models_and_native_ownership(self):
        for model_name in (
            "onehr.role",
            "onehr.user.role",
            "onehr.sod.matrix",
            "onehr.sod.conflict.log",
            "onehr.audit.log",
            "res.users",
        ):
            self.assertIn(model_name, self.env)

        self.assertIn("onehr_role_assignment_ids", self.env["res.users"]._fields)
        self.assertIn("group_ids", self.env["res.users"]._fields)
        self.assertIn("privilege_id", self.env["res.groups"]._fields)

        # Branch is owned by the later branch addon, not security.
        self.assertNotIn("onehr.branch", self.env)

    def test_02_role_scope_effective_date_and_unique_code(self):
        today = fields.Date.today()
        role = self._role("HRBP", company=self.company)
        self.assertTrue(role.is_effective_on(today))

        with self.assertRaises(ValidationError):
            self._role("hrbp", company=self.company)

        # Same business code can exist in another legal company scope.
        other = self._role("HRBP", company=self.other_company)
        self.assertNotEqual(role.id, other.id)

        with self.assertRaises((AccessError, ValidationError)):
            role.with_user(self.admin).unlink()

        with self.assertRaises(ValidationError):
            self.env["onehr.role"].create(
                {
                    "code": "BAD-DATE",
                    "name": "Bad Date",
                    "valid_from": today,
                    "valid_to": today - timedelta(days=1),
                }
            )

    def test_03_group_mapping_is_admin_only_and_protected(self):
        role = self._role("RECRUITER")

        with self.assertRaises(AccessError):
            role.with_user(self.manager).write(
                {"group_ids": [Command.link(self.functional_group_a.id)]}
            )

        role.with_user(self.admin).write(
            {"group_ids": [Command.link(self.functional_group_a.id)]}
        )
        self.assertIn(self.functional_group_a, role.group_ids)

        with self.assertRaises(ValidationError):
            role.with_user(self.admin).write(
                {"group_ids": [Command.link(self.env.ref("base.group_system").id)]}
            )

    def test_04_activation_reconciliation_preserves_non_onehr_groups(self):
        role = self._role("FUNCTION-A", group=self.functional_group_a)
        assignment = self._assignment(role)

        assignment.with_user(self.manager).action_activate()
        self.target_user.invalidate_recordset(["group_ids"])

        self.assertEqual(assignment.state, "active")
        self.assertIn(self.functional_group_a, self.target_user.group_ids)
        self.assertIn(self.manual_group, self.target_user.group_ids)

        assignment.with_user(self.manager).action_revoke()
        self.target_user.invalidate_recordset(["group_ids"])

        self.assertEqual(assignment.state, "revoked")
        self.assertNotIn(self.functional_group_a, self.target_user.group_ids)
        self.assertIn(self.manual_group, self.target_user.group_ids)

        # Cross-company preservation: the same global Odoo group must remain
        # when another effective OneHR role assignment still requires it.
        multi_user = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "OneHR Multi Company Target",
                "login": "onehr_security_multi_company_target",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id, self.other_company.id])],
            }
        )
        admin_all = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "OneHR Multi Company Security Admin",
                "login": "onehr_security_multi_company_admin",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id, self.other_company.id])],
                "group_ids": [Command.set(self.group_security_admin.ids)],
            }
        )

        local_role = self._role("LOCAL-SAME-GROUP", group=self.functional_group_a, company=self.company)
        other_role = self._role("OTHER-SAME-GROUP", group=self.functional_group_a, company=self.other_company)

        local_assignment = self._assignment(local_role, user=multi_user, company=self.company)
        other_assignment = self._assignment(other_role, user=multi_user, company=self.other_company)

        local_assignment.with_user(admin_all).action_activate()
        other_assignment.with_user(admin_all).action_activate()
        multi_user.invalidate_recordset(["group_ids"])
        self.assertIn(self.functional_group_a, multi_user.group_ids)

        local_assignment.with_user(self.manager).action_revoke()
        multi_user.invalidate_recordset(["group_ids"])
        self.assertIn(
            self.functional_group_a,
            multi_user.group_ids,
            "An effective role in another company must preserve the global Odoo group.",
        )
