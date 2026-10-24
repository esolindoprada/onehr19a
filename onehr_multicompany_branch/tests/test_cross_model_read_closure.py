
# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRBranchCommon


@tagged("post_install", "-at_install", "onehr_multicompany_branch")
class TestCrossModelBranchReadClosure(OneHRBranchCommon):
    """Regression gates for relational branch fields exposed on foreign models.

    Odoo form/list/search rendering is a cross-model operation: reading a
    ``res.users`` or ``onehr.user.role`` row is not sufficient when the web
    client must also resolve the ``onehr.branch`` display names referenced by
    Many2one/Many2many fields.  These tests deliberately exercise both sides of
    that contract without granting mutation authority on the branch master.
    """

    USERS_BRANCH_FIELDS = (
        "onehr_allowed_branch_ids",
        "onehr_default_branch_id",
        "onehr_effective_branch_ids",
        "onehr_branch_count",
        "onehr_effective_branch_count",
    )
    ROLE_BRANCH_FIELDS = ("branch_id",)

    def _assert_relational_comodel_read_closure(self, actor, owner_record, field_names):
        """Assert owner-surface read plus generic relational comodel readability.

        The helper intentionally discovers each relational comodel from Odoo's
        field metadata instead of hard-coding ``onehr.branch``.  This makes the
        regression gate reusable for future relational fields added to the same
        approved Users / Role Assignment surfaces.
        """
        actor_owner = owner_record.with_user(actor)
        payload = actor_owner.read(list(field_names))[0]

        for field_name in field_names:
            field = actor_owner._fields[field_name]
            comodel_name = getattr(field, "comodel_name", None)
            if not comodel_name:
                continue

            raw_value = payload.get(field_name)
            if not raw_value:
                continue

            if field.type == "many2one":
                related_ids = [raw_value[0] if isinstance(raw_value, (tuple, list)) else raw_value]
            else:
                related_ids = list(raw_value)

            # The browser must be able to resolve relation labels.  Reading
            # display_name exercises both ACL and record-rule authority on the
            # comodel and reproduces the class of failure seen in Settings > Users.
            self.env[comodel_name].with_user(actor).browse(related_ids).read(["display_name"])

    def test_19_users_branch_surfaces_have_cross_model_read_closure(self):
        self.target_user.write({"onehr_default_branch_id": self.branch_a.id})

        for actor in (
            self.odoo_technical_admin,
            self.security_manager_all,
            self.security_admin_all,
        ):
            with self.subTest(actor=actor.login):
                self._assert_relational_comodel_read_closure(
                    actor,
                    self.target_user,
                    self.USERS_BRANCH_FIELDS,
                )

    def test_20_role_assignment_branch_surfaces_have_cross_model_read_closure(self):
        role = self.make_role("COMODEL-READ-CLOSURE")
        assignment = self.make_assignment(role, branch=self.branch_a)

        for actor in (self.security_manager_all, self.security_admin_all):
            with self.subTest(actor=actor.login):
                self._assert_relational_comodel_read_closure(
                    actor,
                    assignment,
                    self.ROLE_BRANCH_FIELDS,
                )

    def test_21_cross_model_read_closure_preserves_company_record_rule_boundary(self):
        for actor in (
            self.odoo_technical_admin,
            self.security_manager_all,
            self.security_admin_all,
        ):
            with self.subTest(actor=actor.login):
                visible_ids = self.env["onehr.branch"].with_user(actor).search([]).ids
                self.assertIn(self.branch_a.id, visible_ids)
                self.assertIn(self.branch_b.id, visible_ids)
                self.assertNotIn(self.other_branch.id, visible_ids)

                with self.assertRaises(AccessError):
                    self.other_branch.with_user(actor).read(["display_name"])

    def test_22_cross_model_read_grants_do_not_add_branch_mutation_authority(self):
        for actor in (
            self.odoo_technical_admin,
            self.security_manager_all,
            self.security_admin_all,
        ):
            with self.subTest(actor=actor.login):
                with self.assertRaises(AccessError):
                    self.branch_a.with_user(actor).write({"notes": "must not be writable"})

    def test_23_users_and_role_actions_resolve_branch_records_without_access_error(self):
        self.target_user.write({"onehr_default_branch_id": self.branch_a.id})
        role = self.make_role("COMODEL-ACTION-CLOSURE")
        assignment = self.make_assignment(role, branch=self.branch_a)

        # Settings / Users is a native Odoo Technical Administration surface.
        users_action = self.target_user.with_user(self.odoo_technical_admin).action_open_onehr_allowed_branches()
        self.assertEqual(users_action["res_model"], "onehr.branch")
        self.env["onehr.branch"].with_user(self.odoo_technical_admin).search(users_action["domain"]).read(
            ["display_name"]
        )

        # OneHR Security Manager/Admin consume branch comodels from both the
        # Users visibility tab and Role Assignment list/form/search surfaces.
        for actor in (self.security_manager_all, self.security_admin_all):
            with self.subTest(actor=actor.login):
                users_action = self.target_user.with_user(actor).action_open_onehr_allowed_branches()
                self.env["onehr.branch"].with_user(actor).search(users_action["domain"]).read(["display_name"])
                assignment.with_user(actor).read(["branch_id"])

    def test_24_native_users_list_runtime_dependency_closure_for_technical_admin(self):
        """Reproduce the native Settings > Users read path, not just branch labels.

        The upstream OneHR Security summary compute is intentionally exercised as
        shipped: role assignments, role catalog, SoD conflict evidence and audit
        evidence are all touched by the same compute method.  This test therefore
        closes the complete current dependency chain before another browser rerun.
        """
        role = self.make_role("USERS-LIST-RUNTIME-CLOSURE")
        assignment = self.make_assignment(role)
        assignment.with_user(self.security_manager_all).action_activate()

        fields_to_read = [
            "name",
            "login",
            "company_id",
            "onehr_effective_role_count",
            "onehr_sod_conflict_count",
            "onehr_default_branch_id",
            "onehr_effective_branch_count",
        ]
        rows = self.env["res.users"].with_user(self.odoo_technical_admin).search_read(
            [("id", "=", self.target_user.id)],
            fields=fields_to_read,
            limit=1,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.target_user.id)
        self.assertGreaterEqual(rows[0]["onehr_effective_role_count"], 1)

    def test_25_native_users_search_dependency_closure_for_technical_admin(self):
        """Exercise OneHR search helpers injected into the native Users search view."""
        role = self.make_role("USERS-SEARCH-RUNTIME-CLOSURE")
        assignment = self.make_assignment(role)
        assignment.with_user(self.security_manager_all).action_activate()

        Users = self.env["res.users"].with_user(self.odoo_technical_admin)
        role_matches = Users.search([("onehr_effective_role_ids", "in", role.ids)])
        self.assertIn(self.target_user, role_matches)

        # This invokes _search_onehr_sod_conflict_count and therefore proves that
        # the Technical Admin can execute the Users search contract without an
        # ACL failure on onehr.sod.conflict.log.
        Users.search([("onehr_sod_conflict_count", "=", 0)], limit=5)

    def test_26_technical_admin_has_read_closure_on_all_users_summary_dependencies(self):
        """Explicitly gate every current upstream model touched by Users summary compute."""
        for model_name in (
            "onehr.user.role",
            "onehr.role",
            "onehr.sod.conflict.log",
            "onehr.audit.log",
            "onehr.branch",
        ):
            with self.subTest(model=model_name):
                # search_count performs model read-access checking even if the
                # fixture contains no row for a particular evidence model.
                self.env[model_name].with_user(self.odoo_technical_admin).search_count([])

    def test_27_technical_admin_closure_acls_are_read_only(self):
        """The repair is a navigation/read contract, never mutation authority."""
        for xmlid in (
            "onehr_multicompany_branch.access_onehr_branch_odoo_technical_admin",
            "onehr_multicompany_branch.access_onehr_user_role_odoo_technical_admin",
            "onehr_multicompany_branch.access_onehr_role_odoo_technical_admin",
            "onehr_multicompany_branch.access_onehr_sod_conflict_odoo_technical_admin",
            "onehr_multicompany_branch.access_onehr_audit_odoo_technical_admin",
        ):
            with self.subTest(xmlid=xmlid):
                acl = self.env.ref(xmlid)
                self.assertTrue(acl.perm_read)
                self.assertFalse(acl.perm_write)
                self.assertFalse(acl.perm_create)
                self.assertFalse(acl.perm_unlink)

    def test_28_security_manager_admin_users_role_branch_surface_regression(self):
        """Keep the complete approved OneHR governance surfaces open after Attempt 2."""
        role = self.make_role("SECURITY-SURFACE-RUNTIME-CLOSURE")
        assignment = self.make_assignment(role, branch=self.branch_a)
        assignment.with_user(self.security_manager_all).action_activate()

        users_fields = [
            "onehr_role_assignment_ids",
            "onehr_effective_role_ids",
            "onehr_effective_role_count",
            "onehr_sod_conflict_count",
            "onehr_audit_event_count",
            "onehr_allowed_branch_ids",
            "onehr_default_branch_id",
            "onehr_effective_branch_ids",
            "onehr_effective_branch_count",
        ]
        role_fields = [
            "user_id",
            "role_id",
            "company_id",
            "branch_id",
            "valid_from",
            "valid_to",
            "effective_status",
            "conflict_count",
        ]
        for actor in (self.security_manager_all, self.security_admin_all):
            with self.subTest(actor=actor.login):
                self.target_user.with_user(actor).read(users_fields)
                assignment.with_user(actor).read(role_fields)
                self.env["onehr.branch"].with_user(actor).browse(self.branch_a.id).read(["display_name"])
