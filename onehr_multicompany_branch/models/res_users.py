
# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import open_records_action


class ResUsers(models.Model):
    _inherit = "res.users"

    onehr_allowed_branch_ids = fields.Many2many(
        "onehr.branch",
        "onehr_res_users_branch_rel",
        "user_id",
        "branch_id",
        string="Allowed OneHR Branches",
        help="Explicit operational branch scope. It never expands the user's Odoo allowed companies.",
    )
    onehr_default_branch_id = fields.Many2one(
        "onehr.branch",
        string="Default OneHR Branch",
        ondelete="restrict",
        help="Personal default used by branch-aware OneHR models when it is still authorized and effective.",
    )
    onehr_effective_branch_ids = fields.Many2many(
        "onehr.branch",
        compute="_compute_onehr_branch_summary",
        string="Effective Allowed Branches",
    )
    onehr_branch_count = fields.Integer(compute="_compute_onehr_branch_summary", string="Allowed Branches")
    onehr_effective_branch_count = fields.Integer(
        compute="_compute_onehr_branch_summary",
        string="Effective Branches",
    )

    @api.depends(
        "onehr_allowed_branch_ids",
        "onehr_allowed_branch_ids.active",
        "onehr_allowed_branch_ids.valid_from",
        "onehr_allowed_branch_ids.valid_to",
    )
    def _compute_onehr_branch_summary(self):
        today = fields.Date.context_today(self)
        for user in self:
            effective = user.onehr_allowed_branch_ids.filtered(
                lambda branch: (
                    branch.company_id.onehr_branch_enabled
                    and branch.active
                    and branch.is_effective_on(today)
                )
            )
            user.onehr_effective_branch_ids = effective
            user.onehr_branch_count = len(user.onehr_allowed_branch_ids)
            user.onehr_effective_branch_count = len(effective)

    @api.constrains("onehr_allowed_branch_ids", "onehr_default_branch_id", "company_ids")
    def _check_onehr_branch_scope(self):
        today = fields.Date.context_today(self)
        for user in self:
            invalid_company = user.onehr_allowed_branch_ids.filtered(
                lambda branch: branch.company_id not in user.company_ids
            )
            if invalid_company:
                raise ValidationError(
                    _("Allowed OneHR branches must stay inside the user's Odoo allowed companies.")
                )

            default = user.onehr_default_branch_id
            if default:
                if default not in user.onehr_allowed_branch_ids:
                    raise ValidationError(_("The default branch must be included in Allowed OneHR Branches."))
                if not default.company_id.onehr_branch_enabled:
                    raise ValidationError(_("OneHR Branch Scope must be enabled for the default branch company."))
                if not default.active or not default.is_effective_on(today):
                    raise ValidationError(_("The default branch must be active and effective today."))

    def write(self, vals):
        branch_fields = {"onehr_allowed_branch_ids", "onehr_default_branch_id"}
        branch_changes = branch_fields & set(vals)
        actor = self.env.user
        is_branch_admin = actor.has_group("onehr_multicompany_branch.group_onehr_branch_admin")
        is_security_admin = actor.has_group("onehr_security.group_onehr_security_admin")
        is_odoo_admin = actor.has_group("base.group_system") or self.env.uid == SUPERUSER_ID

        # The Branch Admin ACL adds res.users write only so branch scope can be
        # maintained. It must never become a generic user-administration grant.
        if is_branch_admin and not is_security_admin and not is_odoo_admin:
            if any(record != actor for record in self):
                disallowed = set(vals) - branch_fields
                if disallowed:
                    raise AccessError(
                        _("OneHR Branch Admin may change only branch-scope fields on other users.")
                    )

        if branch_changes and not is_odoo_admin:
            if is_branch_admin:
                # UI domains are convenience only. Server-side verification makes
                # sure Branch Admin cannot attach/detach a branch outside the
                # administrator's own Odoo allowed-company boundary through RPC.
                self._assert_branch_admin_change_within_actor_scope(vals)
            else:
                # Non-admin users never expand their own branch scope. The quick
                # selector writes only the default after explicit authorization.
                if not (
                    self.env.context.get("onehr_branch_controlled_self_default")
                    and self.ids == [actor.id]
                    and set(vals) == {"onehr_default_branch_id"}
                ):
                    raise AccessError(
                        _("Only OneHR Branch Admin may change allowed-branch scope. Use the branch quick selector for your own default branch.")
                    )

        before = {}
        if branch_changes and not self.env.context.get("onehr_branch_skip_user_audit"):
            for user in self:
                before[user.id] = {
                    "allowed_branch_ids": user.onehr_allowed_branch_ids.ids,
                    "default_branch_id": user.onehr_default_branch_id.id or False,
                }

        if "onehr_allowed_branch_ids" in vals:
            self._assert_no_effective_roles_removed_by_scope_change(vals["onehr_allowed_branch_ids"])

        result = super().write(vals)

        if branch_changes and not self.env.context.get("onehr_branch_skip_user_audit"):
            for user in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("OneHR user branch scope updated"),
                    severity="high",
                    record=user,
                    company=user.company_id,
                    changed_fields=branch_changes,
                    before=before[user.id],
                    after={
                        "allowed_branch_ids": user.onehr_allowed_branch_ids.ids,
                        "default_branch_id": user.onehr_default_branch_id.id or False,
                    },
                )
            self._reconcile_onehr_groups(system=True)

        return result

    def _assert_branch_admin_change_within_actor_scope(self, vals):
        """Validate branch IDs through the caller's normal onehr.branch rules.

        This deliberately avoids sudo/system-user lookup. If a branch is outside
        the Branch Admin's legal-company scope, the normal onehr.branch record
        rules hide it and this method rejects the write before res.users changes.
        """
        candidate_ids = set()
        default_id = vals.get("onehr_default_branch_id")
        if default_id:
            candidate_ids.add(default_id)

        for command in vals.get("onehr_allowed_branch_ids", []):
            operation = command[0]
            if operation == 6:  # Command.SET
                candidate_ids.update(command[2])
            elif operation in (3, 4):  # Command.UNLINK / Command.LINK
                candidate_ids.add(command[1])
            elif operation == 5:  # Command.CLEAR has no new branch identity.
                continue
            elif operation in (0, 1, 2):
                raise AccessError(_("Branch scope must link existing branch masters; inline create/update/delete is not allowed."))

        if not candidate_ids:
            return True

        visible_ids = set(
            self.env["onehr.branch"].search([("id", "in", list(candidate_ids))]).ids
        )
        if visible_ids != candidate_ids:
            raise AccessError(
                _("OneHR Branch Admin may manage only branches inside the administrator's allowed legal companies.")
            )
        return True

    def _assert_no_effective_roles_removed_by_scope_change(self, commands):
        """Prevent branch-scope removal from silently orphaning active authority."""
        today = fields.Date.context_today(self)
        for user in self:
            simulated = set(user.onehr_allowed_branch_ids.ids)
            for command in commands:
                operation = command[0]
                if operation == 6:  # Command.SET
                    simulated = set(command[2])
                elif operation == 4:  # Command.LINK
                    simulated.add(command[1])
                elif operation == 3:  # Command.UNLINK
                    simulated.discard(command[1])
                elif operation == 5:  # Command.CLEAR
                    simulated.clear()
                elif operation in (0, 1, 2):
                    raise AccessError(_("Branch scope must link existing branch masters; inline create/update/delete is not allowed."))

            removed = set(user.onehr_allowed_branch_ids.ids) - simulated
            if not removed:
                continue
            effective_roles = self.env["onehr.user.role"].with_user(SUPERUSER_ID).search_count(
                [
                    ("user_id", "=", user.id),
                    ("branch_id", "in", list(removed)),
                    ("state", "=", "active"),
                    ("valid_from", "<=", today),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", today),
                ],
                limit=1,
            )
            if effective_roles:
                raise ValidationError(
                    _("Revoke or end-date effective branch-scoped role assignments before removing that branch from the user.")
                )

    # ------------------------------------------------------------------
    # onehr_security extension contract
    # ------------------------------------------------------------------

    def _onehr_branch_scope_assignment_domain(self):
        self.ensure_one()
        allowed_ids = self.onehr_allowed_branch_ids.ids
        if allowed_ids:
            return ["|", ("branch_id", "=", False), ("branch_id", "in", allowed_ids)]
        return [("branch_id", "=", False)]

    def _onehr_desired_group_ids(self):
        """Keep global Odoo group membership only for effective authorized scope.

        The base security implementation intentionally reads all company-scoped
        assignments with the system user because res.groups membership is global.
        This branch extension keeps that narrow derivation but additionally filters
        branch-specific assignments by explicit allowed branches and branch
        effective dates. It never authorizes assignment creation or source access.
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
        allowed_ids = set(self.onehr_allowed_branch_ids.ids)
        assignments = assignments.filtered(
            lambda assignment: (
                not assignment.branch_id
                or (
                    assignment.branch_id.id in allowed_ids
                    and assignment.branch_id.company_id.onehr_branch_enabled
                    and assignment.branch_id.active
                    and assignment.branch_id.is_effective_on(today)
                )
            )
        )
        return assignments.mapped("role_id.group_ids")

    # ------------------------------------------------------------------
    # Enterprise actions
    # ------------------------------------------------------------------

    def action_open_onehr_allowed_branches(self):
        self.ensure_one()
        return open_records_action(
            name=_("Allowed Branches — %s", self.display_name),
            res_model="onehr.branch",
            domain=[("id", "in", self.onehr_allowed_branch_ids.ids)],
        )

    def action_open_onehr_branch_roles(self):
        self.ensure_one()
        return open_records_action(
            name=_("Branch Role Assignments — %s", self.display_name),
            res_model="onehr.user.role",
            domain=[("user_id", "=", self.id), ("branch_id", "!=", False)],
            context={"default_user_id": self.id, "default_company_id": self.company_id.id},
        )

