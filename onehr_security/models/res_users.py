from odoo import _, api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.fields import Command
from odoo.exceptions import AccessError

from .action_helpers import (
    open_records_action,
    require_security_manager,
)


class ResUsers(models.Model):
    _inherit = "res.users"

    onehr_role_assignment_ids = fields.One2many(
        "onehr.user.role",
        "user_id",
        string="OneHR Role Assignments",
    )
    onehr_effective_role_ids = fields.Many2many(
        "onehr.role",
        string="Effective OneHR Roles",
        compute="_compute_onehr_security_summary",
        search="_search_onehr_effective_role_ids",
    )
    onehr_role_assignment_count = fields.Integer(
        compute="_compute_onehr_security_summary",
        string="Role Assignments",
    )
    onehr_effective_role_count = fields.Integer(
        compute="_compute_onehr_security_summary",
        string="Effective Roles",
    )
    onehr_sod_conflict_count = fields.Integer(
        compute="_compute_onehr_security_summary",
        search="_search_onehr_sod_conflict_count",
        string="SoD Conflicts",
    )
    onehr_audit_event_count = fields.Integer(
        compute="_compute_onehr_security_summary",
        string="Audit Events",
    )
    onehr_last_access_reconciled_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_security.group_onehr_security_manager,onehr_security.group_onehr_security_admin",
    )
    onehr_security_note = fields.Text(
        string="OneHR Security Administration Note",
        groups="onehr_security.group_onehr_security_admin",
        help="Administrative security note. Do not store passwords, tokens or medical/discipline secrets here.",
    )

    @api.depends("onehr_role_assignment_ids.state", "onehr_role_assignment_ids.valid_from", "onehr_role_assignment_ids.valid_to")
    def _compute_onehr_security_summary(self):
        today = fields.Date.context_today(self)
        Conflict = self.env["onehr.sod.conflict.log"]
        Audit = self.env["onehr.audit.log"]

        for user in self:
            assignments = user.onehr_role_assignment_ids
            effective = assignments.filtered(
                lambda item: (
                    item.state == "active"
                    and item.valid_from <= today
                    and (not item.valid_to or item.valid_to >= today)
                    and item.role_id.active
                    and item.role_id.is_effective_on(today)
                )
            )
            user.onehr_effective_role_ids = effective.mapped("role_id")
            user.onehr_role_assignment_count = len(assignments)
            user.onehr_effective_role_count = len(user.onehr_effective_role_ids)
            user.onehr_sod_conflict_count = Conflict.search_count([("user_id", "=", user.id)])
            user.onehr_audit_event_count = Audit.search_count([("actor_user_id", "=", user.id)])


    @api.model
    def _search_onehr_effective_role_ids(self, operator, value):
        today = fields.Date.context_today(self)
        assignments = self.env["onehr.user.role"].search(
            [
                ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", today),
                ("role_id.active", "=", True),
                ("role_id.valid_from", "<=", today),
                "|",
                ("role_id.valid_to", "=", False),
                ("role_id.valid_to", ">=", today),
                ("role_id", operator, value),
            ]
        )
        return [("id", "in", assignments.mapped("user_id").ids)]

    @api.model
    def _search_onehr_sod_conflict_count(self, operator, value):
        if (operator, value) in {(">", 0), ("!=", 0)}:
            user_ids = self.env["onehr.sod.conflict.log"].search([]).mapped("user_id").ids
            return [("id", "in", user_ids)]
        if (operator, value) in {("=", 0), ("<=", 0)}:
            user_ids = self.env["onehr.sod.conflict.log"].search([]).mapped("user_id").ids
            return [("id", "not in", user_ids)]
        raise NotImplementedError("Search is supported only for zero/non-zero SoD conflict counts.")

    @api.model_create_multi
    def create(self, vals_list):
        """Allow OneHR Security Admin to provision a basic internal identity safely.

        A OneHR Security Admin may create the Odoo user identity in one of their
        own allowed companies, but may not inject raw Odoo groups during creation.
        Functional access must be granted afterwards through effective OneHR roles.
        Odoo technical administrators keep their native administration authority.
        """
        is_onehr_admin = self.env.user.has_group(
            "onehr_security.group_onehr_security_admin"
        )
        is_odoo_admin = self.env.user.has_group("base.group_system")

        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)

            if is_onehr_admin and not is_odoo_admin and self.env.uid != SUPERUSER_ID:
                # Odoo's standard new-user form can submit the ordinary
                # "User" role plus the standard default groups. Accept only
                # that canonical baseline; any extra raw group is rejected.
                requested_role = vals.get("role")
                if requested_role and requested_role != "group_user":
                    raise AccessError(
                        _(
                            "OneHR Security Admin may provision only a normal internal "
                            "user identity. Administrator role requires Odoo technical admin."
                        )
                    )

                safe_default_groups = self._default_groups()
                if "group_ids" in vals:
                    requested_group_ids = set(safe_default_groups.ids)

                    for command in vals["group_ids"]:
                        operation = command[0]

                        if operation == Command.SET:
                            requested_group_ids = set(command[2])
                        elif operation == Command.LINK:
                            requested_group_ids.add(command[1])
                        elif operation == Command.UNLINK:
                            requested_group_ids.discard(command[1])
                        elif operation == Command.CLEAR:
                            requested_group_ids.clear()
                        else:
                            raise AccessError(
                                _(
                                    "OneHR Security Admin cannot create/update/delete "
                                    "Odoo groups through user provisioning."
                                )
                            )

                    safe_ids = set(safe_default_groups.ids)
                    if (
                        self.env.ref("base.group_user").id not in requested_group_ids
                        or not requested_group_ids.issubset(safe_ids)
                    ):
                        raise AccessError(
                            _(
                                "OneHR Security Admin must provision functional access "
                                "through OneHR roles, not raw Odoo groups."
                            )
                        )

                    vals["group_ids"] = [Command.set(sorted(requested_group_ids))]

                company_id = vals.get("company_id") or self.env.company.id
                if company_id not in self.env.user.company_ids.ids:
                    raise AccessError(
                        _("You cannot provision a user into a company you are not allowed to manage.")
                    )

                # OneHR Security Admin provisions one legal-company identity here.
                # Broader Odoo multi-company administration remains a technical-admin task.
                vals["company_id"] = company_id
                vals["company_ids"] = [Command.set([company_id])]

            prepared.append(vals)

        users = super().create(prepared)

        if is_onehr_admin and not is_odoo_admin and self.env.uid != SUPERUSER_ID:
            for user in users:
                self.env["onehr.audit.log"]._log_event(
                    action="create",
                    summary=_("Odoo user identity provisioned through OneHR Security"),
                    severity="high",
                    record=user,
                    company=user.company_id,
                    after={
                        "user_id": user.id,
                        "login": user.login,
                        "company_id": user.company_id.id,
                        "active": user.active,
                    },
                )

        return users

    def write(self, vals):
        """Separate OneHR security administration from raw Odoo administration.

        - Security Manager can activate/deactivate an existing user and change the
          default company only inside the manager's already allowed companies.
        - Security Admin may administer identity/login fields, but raw Odoo group
          and multi-company entitlement changes still require Odoo technical admin.
        - Effective OneHR role reconciliation uses a private context flag and may
          update only the calculated OneHR-managed group membership.
        """
        is_manager = self.env.user.has_group(
            "onehr_security.group_onehr_security_manager"
        )
        is_onehr_admin = self.env.user.has_group(
            "onehr_security.group_onehr_security_admin"
        )
        is_odoo_admin = self.env.user.has_group("base.group_system")
        is_reconcile = self.env.context.get("onehr_security_reconcile")

        if self.env.uid != SUPERUSER_ID and not is_odoo_admin:
            if "group_ids" in vals and not is_reconcile:
                raise AccessError(
                    _(
                        "Raw Odoo group membership is not managed directly by OneHR "
                        "Security users. Use effective OneHR roles."
                    )
                )

            if "company_ids" in vals:
                raise AccessError(
                    _(
                        "Changing the Odoo allowed-company set requires Odoo technical "
                        "administration. OneHR Security may only select a permitted default company."
                    )
                )

            if "company_id" in vals and vals["company_id"] not in self.env.user.company_ids.ids:
                raise AccessError(
                    _("You cannot select a default company outside your own allowed companies.")
                )

            if is_manager and not is_onehr_admin and not is_reconcile and self != self.env.user:
                manager_allowed_fields = {
                    "active",
                    "company_id",
                    "onehr_role_assignment_ids",
                }
                disallowed = set(vals) - manager_allowed_fields
                if disallowed:
                    raise AccessError(
                        _(
                            "OneHR Security Manager may change only activation, permitted "
                            "default company, and OneHR role assignments for other users."
                        )
                    )

        audit_fields = {
            "active",
            "company_id",
            "company_ids",
            "login",
            "password",
            "new_password",
            "group_ids",
        } & set(vals)

        before = {}
        if audit_fields and not is_reconcile:
            for user in self:
                before[user.id] = {
                    "login": user.login,
                    "active": user.active,
                    "company_id": user.company_id.id,
                    "company_ids": user.company_ids.ids,
                    "group_ids": user.group_ids.ids,
                }

        result = super().write(vals)

        if audit_fields and not is_reconcile:
            for user in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("Security-sensitive Odoo user identity fields updated"),
                    severity="high",
                    record=user,
                    company=user.company_id,
                    changed_fields=audit_fields,
                    before=before[user.id],
                    after={
                        "login": user.login,
                        "active": user.active,
                        "company_id": user.company_id.id,
                        "company_ids": user.company_ids.ids,
                        "group_ids": user.group_ids.ids,
                    },
                    metadata={
                        "secret_value_logged": False,
                    },
                )

        return result

    def _onehr_branch_scope_assignment_domain(self):
        """Future branch addon may extend this domain; company remains top partition."""
        self.ensure_one()
        return []

    def _onehr_managed_group_ids(self):
        """Return the global set of groups whose direct membership OneHR owns.

        Odoo group membership is global, while OneHR role assignments can be
        company-scoped (and later branch-scoped). Therefore this derived-access
        calculation must see *all* OneHR role mappings, not only the companies
        visible to the manager who triggered the reconciliation.

        `with_user(SUPERUSER_ID)` is intentionally limited to this internal
        derivation. It does not authorize assignment creation/revocation and it
        does not expose other-company records to the caller.
        """
        return (
            self.env["onehr.role"]
            .with_user(SUPERUSER_ID)
            .with_context(active_test=False)
            .search([])
            .mapped("group_ids")
        )

    def _onehr_desired_group_ids(self):
        """Union every currently effective OneHR role entitlement for this user.

        Because `res.groups` is global, an active assignment in another allowed
        company/branch must keep the group even when a local assignment expires.
        The assignment workflow remains protected by normal ACL/rules; only this
        read-only derivation uses the system user to avoid cross-company loss.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)

        assignments = self.env["onehr.user.role"].with_user(SUPERUSER_ID).search(
            [
                ("user_id", "=", self.id),
                ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", today),
                ("role_id.active", "=", True),
                ("role_id.valid_from", "<=", today),
                "|",
                ("role_id.valid_to", "=", False),
                ("role_id.valid_to", ">=", today),
            ]
        )
        return assignments.mapped("role_id.group_ids")

    def _reconcile_onehr_groups(self, system=False):
        """Reconcile only the Odoo groups managed by OneHR role mappings.

        Manual/direct groups that are not mapped by any OneHR role are preserved.
        This method does not use sudo. Human-triggered provisioning must pass the
        OneHR Security Manager/Admin check; the daily cron runs as the root user.
        """
        if self.env.uid != SUPERUSER_ID and not system:
            require_security_manager(self.env)

        Audit = self.env["onehr.audit.log"]

        for user in self:
            managed = user._onehr_managed_group_ids()
            desired = user._onehr_desired_group_ids()
            preserved = user.group_ids - managed
            new_groups = preserved | desired

            before_ids = sorted(user.group_ids.ids)
            after_ids = sorted(new_groups.ids)

            if before_ids != after_ids:
                user.with_context(onehr_security_reconcile=True).write(
                    {
                        "group_ids": [Command.set(after_ids)],
                        "onehr_last_access_reconciled_at": fields.Datetime.now(),
                    }
                )
                Audit._log_event(
                    action="reconcile",
                    summary=_("OneHR effective access reconciled for %s", user.display_name),
                    severity="high",
                    record=user,
                    company=user.company_id,
                    changed_fields={"group_ids"},
                    before={"group_ids": before_ids},
                    after={"group_ids": after_ids},
                )
            else:
                # Keep operational evidence that a manual/system reconciliation ran,
                # but avoid a user write when no access changed.
                Audit._log_event(
                    action="reconcile",
                    summary=_("OneHR access reconciliation checked; no group change"),
                    severity="info",
                    record=user,
                    company=user.company_id,
                    before={"group_ids": before_ids},
                    after={"group_ids": after_ids},
                )

        return True

    def action_reconcile_onehr_access(self):
        require_security_manager(self.env)
        return self._reconcile_onehr_groups()

    def action_open_onehr_role_assignments(self):
        self.ensure_one()
        return open_records_action(
            name=_("OneHR Role Assignments — %s", self.display_name),
            res_model="onehr.user.role",
            domain=[("user_id", "=", self.id)],
            context={"default_user_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_onehr_sod_conflicts(self):
        self.ensure_one()
        return open_records_action(
            name=_("SoD Conflicts — %s", self.display_name),
            res_model="onehr.sod.conflict.log",
            domain=[("user_id", "=", self.id)],
        )

    def action_open_onehr_audit_events(self):
        self.ensure_one()
        return open_records_action(
            name=_("Security Audit — %s", self.display_name),
            res_model="onehr.audit.log",
            domain=[("actor_user_id", "=", self.id)],
            context={"create": False, "delete": False},
        )
