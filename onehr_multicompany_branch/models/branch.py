
# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action, require_branch_admin


class OneHRBranch(models.Model):
    """Operational subdivision inside one legal Odoo company.

    `res.company` remains the legal and top security partition.  A branch adds a
    narrower operational scope only where the business fact genuinely belongs to
    a branch.  Effective dates are retained even when a branch is archived so
    historical role/security evidence remains explainable.
    """

    _name = "onehr.branch"
    _description = "OneHR Operational Branch"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "company_id, code, name, id"
    _parent_name = "parent_id"
    _parent_store = True
    _check_company_auto = True

    _code_company_unique = models.Constraint(
        "unique(company_id, code)",
        "Branch code must be unique inside the legal company.",
    )

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    branch_type = fields.Selection(
        [
            ("head_office", "Head Office"),
            ("operational", "Operational Branch"),
            ("shared_service", "Shared Service"),
            ("virtual", "Virtual / Administrative"),
        ],
        required=True,
        default="operational",
        index=True,
        tracking=True,
    )
    parent_id = fields.Many2one(
        "onehr.branch",
        string="Parent Branch",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
    )
    child_ids = fields.One2many("onehr.branch", "parent_id", string="Child Branches")
    parent_path = fields.Char(index=True)
    manager_user_id = fields.Many2one(
        "res.users",
        string="Branch Manager User",
        ondelete="restrict",
        tracking=True,
        help="Optional operational owner. This field does not grant security access by itself.",
    )
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(
        help="Operational note only. Do not store passwords, medical data, or unrelated sensitive HR content."
    )

    lifecycle_status = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("effective", "Effective"),
            ("expired", "Expired"),
            ("inactive", "Inactive"),
        ],
        compute="_compute_lifecycle_status",
        string="Lifecycle Status",
    )
    child_count = fields.Integer(compute="_compute_child_count", string="Child Branches")
    allowed_user_count = fields.Integer(
        compute="_compute_sensitive_counts",
        string="Allowed Users",
        groups="onehr_multicompany_branch.group_onehr_branch_admin,onehr_multicompany_branch.group_onehr_central_office",
    )
    default_user_count = fields.Integer(
        compute="_compute_sensitive_counts",
        string="Default Users",
        groups="onehr_multicompany_branch.group_onehr_branch_admin,onehr_multicompany_branch.group_onehr_central_office",
    )
    role_assignment_count = fields.Integer(
        compute="_compute_sensitive_counts",
        string="Role Assignments",
        groups="onehr_multicompany_branch.group_onehr_branch_admin,onehr_multicompany_branch.group_onehr_central_office,onehr_security.group_onehr_security_manager,onehr_security.group_onehr_security_admin",
    )
    is_my_default = fields.Boolean(compute="_compute_my_branch_flags")
    is_allowed_for_me = fields.Boolean(compute="_compute_my_branch_flags")

    # ------------------------------------------------------------------
    # Normalization and display
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        require_branch_admin(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code"):
                vals["code"] = vals["code"].strip().upper()
            prepared.append(vals)

        records = super().create(prepared)
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_("OneHR branch created: %s", record.display_name),
                severity="high",
                record=record,
                company=record.company_id,
                after=record._audit_snapshot(),
            )
            record.log_business_action(_("Branch master created through controlled OneHR branch administration."))
        return records

    def write(self, vals):
        if not self.env.context.get("onehr_branch_controlled_action"):
            require_branch_admin(self.env)

        vals = dict(vals)
        if vals.get("code"):
            vals["code"] = vals["code"].strip().upper()

        if {"company_id", "valid_from"} & set(vals):
            for record in self:
                if record._has_business_references():
                    raise AccessError(
                        _(
                            "Company and Valid From cannot be rewritten after a branch is referenced. "
                            "Close the effective period and create a successor branch definition if required."
                        )
                    )

        before = {record.id: record._audit_snapshot() for record in self}
        result = super().write(vals)

        auditable = {
            "code",
            "name",
            "company_id",
            "branch_type",
            "parent_id",
            "manager_user_id",
            "active",
            "valid_from",
            "valid_to",
            "notes",
        } & set(vals)
        if auditable and not self.env.context.get("onehr_branch_skip_audit"):
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("OneHR branch master updated"),
                    severity="high" if auditable & {"company_id", "active", "valid_from", "valid_to"} else "medium",
                    record=record,
                    company=record.company_id,
                    changed_fields=auditable,
                    before=before[record.id],
                    after=record._audit_snapshot(),
                )
        return result

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}" if record.code else record.name

    # ------------------------------------------------------------------
    # Lifecycle and integrity
    # ------------------------------------------------------------------

    @api.depends("active", "valid_from", "valid_to")
    def _compute_lifecycle_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if not record.active:
                record.lifecycle_status = "inactive"
            elif record.valid_from > today:
                record.lifecycle_status = "scheduled"
            elif record.valid_to and record.valid_to < today:
                record.lifecycle_status = "expired"
            else:
                record.lifecycle_status = "effective"

    @api.depends("child_ids")
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    def _compute_sensitive_counts(self):
        """Counts follow the caller's normal ACL/rules; no sudo-based information leak."""
        User = self.env["res.users"]
        UserRole = self.env["onehr.user.role"]
        for record in self:
            record.allowed_user_count = User.search_count([("onehr_allowed_branch_ids", "in", record.id)])
            record.default_user_count = User.search_count([("onehr_default_branch_id", "=", record.id)])
            record.role_assignment_count = UserRole.search_count([("branch_id", "=", record.id)])

    @api.depends_context("uid")
    def _compute_my_branch_flags(self):
        user = self.env.user
        allowed_ids = set(user.onehr_allowed_branch_ids.ids)
        default_id = user.onehr_default_branch_id.id
        for record in self:
            record.is_allowed_for_me = record.id in allowed_ids
            record.is_my_default = record.id == default_id

    @api.constrains("parent_id", "company_id")
    def _check_parent_company_and_cycle(self):
        if self._has_cycle():
            raise ValidationError(_("A branch hierarchy cannot contain a cycle."))
        for record in self:
            if record.parent_id and record.parent_id.company_id != record.company_id:
                raise ValidationError(_("Parent and child branches must belong to the same legal company."))

    @api.constrains("manager_user_id", "company_id")
    def _check_manager_company(self):
        for record in self:
            if record.manager_user_id and record.company_id not in record.manager_user_id.company_ids:
                raise ValidationError(_("The branch manager must be allowed to operate in the branch company."))

    @api.constrains("parent_id", "valid_from", "valid_to", "active")
    def _check_hierarchy_effective_coverage(self):
        for record in self:
            parent = record.parent_id
            if parent:
                if record.valid_from < parent.valid_from:
                    raise ValidationError(_("A child branch cannot start before its parent branch."))
                if parent.valid_to and (not record.valid_to or record.valid_to > parent.valid_to):
                    raise ValidationError(_("A child branch cannot remain effective beyond its parent branch."))
                if record.active and not parent.active:
                    raise ValidationError(_("An active child branch cannot have an inactive parent branch."))

            for child in record.child_ids:
                if child.valid_from < record.valid_from:
                    raise ValidationError(_("Parent branch dates must continue to cover every child branch."))
                if record.valid_to and (not child.valid_to or child.valid_to > record.valid_to):
                    raise ValidationError(_("Parent branch dates must continue to cover every child branch."))
                if child.active and not record.active:
                    raise ValidationError(_("A parent branch with active children cannot be archived."))

    @api.constrains("active", "valid_to")
    def _check_referenced_branch_closure(self):
        today = fields.Date.context_today(self)
        for record in self:
            closing_now = (not record.active) or (record.valid_to and record.valid_to < today)
            if closing_now:
                record._assert_no_current_default_or_effective_role()

    @api.ondelete(at_uninstall=False)
    def _unlink_protect_branch_history(self):
        raise AccessError(_("Branch masters are historical configuration. Archive or end-date the branch instead of deleting it."))

    def _has_business_references(self):
        self.ensure_one()
        User = self.env["res.users"].with_user(SUPERUSER_ID)
        UserRole = self.env["onehr.user.role"].with_user(SUPERUSER_ID)
        return bool(
            User.search_count(
                ["|", ("onehr_allowed_branch_ids", "in", self.id), ("onehr_default_branch_id", "=", self.id)],
                limit=1,
            )
            or UserRole.search_count([("branch_id", "=", self.id)], limit=1)
            or self.child_ids
        )

    def _assert_no_current_default_or_effective_role(self):
        self.ensure_one()
        User = self.env["res.users"].with_user(SUPERUSER_ID)
        UserRole = self.env["onehr.user.role"].with_user(SUPERUSER_ID)
        if User.search_count([("onehr_default_branch_id", "=", self.id)], limit=1):
            raise ValidationError(_("Clear every user's default-branch preference before closing this branch."))

        today = fields.Date.context_today(self)
        domain = [
            ("branch_id", "=", self.id),
            ("state", "=", "active"),
            ("valid_from", "<=", today),
            "|",
            ("valid_to", "=", False),
            ("valid_to", ">=", today),
        ]
        if UserRole.search_count(domain, limit=1):
            raise ValidationError(_("Revoke or end-date effective branch-scoped role assignments before closing this branch."))

    def _audit_snapshot(self):
        self.ensure_one()
        return {
            "code": self.code,
            "name": self.name,
            "company_id": self.company_id.id,
            "branch_type": self.branch_type,
            "parent_id": self.parent_id.id or False,
            "manager_user_id": self.manager_user_id.id or False,
            "active": self.active,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }

    # ------------------------------------------------------------------
    # Controlled enterprise actions
    # ------------------------------------------------------------------

    def action_activate(self):
        require_branch_admin(self.env)
        for record in self:
            if record.active:
                continue
            if record.valid_to and record.valid_to < fields.Date.context_today(self):
                raise UserError(_("An expired branch cannot be activated without first correcting its approved effective period."))
            record.with_context(onehr_branch_controlled_action=True).write({"active": True})
            record.log_business_action(_("Branch activated."))
        return True

    def action_archive(self):
        require_branch_admin(self.env)
        for record in self:
            if not record.active:
                continue
            record._assert_no_current_default_or_effective_role()
            if record.child_ids.filtered("active"):
                raise ValidationError(_("Archive active child branches before archiving their parent."))
            record.with_context(onehr_branch_controlled_action=True).write({"active": False})
            record.log_business_action(_("Branch archived through controlled action."))
        return True

    def action_set_as_my_default(self):
        """Controlled quick selector for the current user's already-authorized scope.

        Persistence uses the system user only after exact self-service authorization
        has been proven.  It writes one field on the current user and does not alter
        allowed companies, allowed branches, Odoo groups, or another user's data.
        """
        self.ensure_one()
        user = self.env.user
        today = fields.Date.context_today(self)
        if self.company_id not in user.company_ids:
            raise AccessError(_("This branch is outside your allowed legal companies."))
        if not self.company_id.onehr_branch_enabled:
            raise UserError(_("OneHR Branch Scope is disabled for this legal company."))
        if self not in user.onehr_allowed_branch_ids:
            raise AccessError(_("This branch is not in your explicit allowed-branch scope."))
        if not self.active or not self.is_effective_on(today):
            raise UserError(_("Only an active, effective branch can be selected as your default."))

        self.env["res.users"].with_user(SUPERUSER_ID).browse(user.id).with_context(
            onehr_branch_controlled_self_default=True,
            onehr_branch_skip_user_audit=True,
        ).write({"onehr_default_branch_id": self.id})

        self.env["onehr.audit.log"]._log_event(
            action="update",
            summary=_("User changed OneHR default branch"),
            severity="medium",
            record=user,
            company=self.company_id,
            changed_fields={"onehr_default_branch_id"},
            after={"onehr_default_branch_id": self.id},
            metadata={"controlled_self_service": True},
        )
        return True

    def action_open_branch(self):
        self.ensure_one()
        return open_record_action(name=self.display_name, res_model="onehr.branch", res_id=self.id)

    def action_open_child_branches(self):
        self.ensure_one()
        return open_records_action(
            name=_("Child Branches — %s", self.display_name),
            res_model="onehr.branch",
            domain=[("parent_id", "=", self.id)],
            context={"default_parent_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_allowed_users(self):
        self.ensure_one()
        return open_records_action(
            name=_("Allowed Users — %s", self.display_name),
            res_model="res.users",
            domain=[("onehr_allowed_branch_ids", "in", self.id)],
        )

    def action_open_default_users(self):
        self.ensure_one()
        return open_records_action(
            name=_("Default Users — %s", self.display_name),
            res_model="res.users",
            domain=[("onehr_default_branch_id", "=", self.id)],
        )

    def action_open_role_assignments(self):
        self.ensure_one()
        return open_records_action(
            name=_("Role Assignments — %s", self.display_name),
            res_model="onehr.user.role",
            domain=[("branch_id", "=", self.id)],
            context={"default_branch_id": self.id, "default_company_id": self.company_id.id},
        )

