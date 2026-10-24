
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import (
    open_record_action,
    require_security_manager,
)


class OneHRUserRole(models.Model):
    """Effective user-to-business-role assignment.

    The base security addon owns company scope only. A future
    `onehr_multicompany_branch` addon may add branch_id and override the small
    branch extension hooks below without creating a reverse dependency.
    """

    _name = "onehr.user.role"
    _description = "OneHR Effective User Role"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "user_id, valid_from desc, id desc"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    role_id = fields.Many2one(
        "onehr.role",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("blocked", "Blocked by SoD"),
            ("revoked", "Revoked"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    effective_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("effective", "Effective"),
            ("expired", "Expired"),
            ("blocked", "Blocked"),
            ("revoked", "Revoked"),
        ],
        compute="_compute_effective_status",
        string="Effective Status",
    )

    assignment_reason = fields.Text()
    activated_at = fields.Datetime(readonly=True)
    activated_by_id = fields.Many2one("res.users", readonly=True)
    revoked_at = fields.Datetime(readonly=True)
    revoked_by_id = fields.Many2one("res.users", readonly=True)
    revocation_reason = fields.Text(readonly=True)

    conflict_count = fields.Integer(compute="_compute_conflict_count", string="SoD Conflicts")

    # ------------------------------------------------------------------
    # Branch extension contract
    # ------------------------------------------------------------------

    def _branch_scope_overlap_domain(self):
        """Future branch addon may append [('branch_id', '=', ...)]."""
        self.ensure_one()
        return []

    def _branch_scope_label(self):
        """Human-readable extension hook; company-only until branch addon exists."""
        self.ensure_one()
        return False

    # ------------------------------------------------------------------
    # Creation / integrity
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(
                    _("New role assignments must start in Draft and use the controlled activation action.")
                )
            vals["state"] = "draft"
            user = self.env["res.users"].browse(vals.get("user_id")).exists()
            if not user:
                raise ValidationError(_("A valid user is required for a OneHR role assignment."))
            vals.setdefault("company_id", user.company_id.id)
            prepared.append(vals)

        records = super().create(prepared)
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_(
                    "OneHR role assignment created: %(user)s / %(role)s",
                    user=record.user_id.display_name,
                    role=record.role_id.display_name,
                ),
                severity="medium",
                record=record,
                company=record.company_id,
                role=record.role_id,
                user_role=record,
                after={
                    "user_id": record.user_id.id,
                    "role_id": record.role_id.id,
                    "company_id": record.company_id.id,
                    "valid_from": record.valid_from,
                    "valid_to": record.valid_to,
                    "state": record.state,
                },
            )
        return records

    @api.constrains("user_id", "company_id", "role_id")
    def _check_scope_integrity(self):
        for record in self:
            if record.company_id not in record.user_id.company_ids:
                raise ValidationError(
                    _("The assignment company must be one of the user's allowed companies.")
                )
            if record.role_id.company_id and record.role_id.company_id != record.company_id:
                raise ValidationError(
                    _("A company-specific OneHR role can only be assigned inside that company.")
                )

    @api.constrains(
        "user_id",
        "role_id",
        "company_id",
        "valid_from",
        "valid_to",
        "state",
    )
    def _check_active_overlap(self):
        far_future = fields.Date.to_date("9999-12-31")
        for record in self.filtered(lambda item: item.state == "active"):
            domain = [
                ("id", "!=", record.id),
                ("user_id", "=", record.user_id.id),
                ("role_id", "=", record.role_id.id),
                ("company_id", "=", record.company_id.id),
                ("state", "=", "active"),
                ("valid_from", "<=", record.valid_to or far_future),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", record.valid_from),
            ] + record._branch_scope_overlap_domain()
            if self.search_count(domain, limit=1):
                raise ValidationError(
                    _("Active OneHR role assignments cannot overlap for the same user, role and scope.")
                )

    def write(self, vals):
        core_identity_fields = {"user_id", "role_id", "company_id", "valid_from"}
        if core_identity_fields & set(vals):
            if any(record.state in ("active", "blocked", "revoked") for record in self):
                raise AccessError(
                    _("Activated/blocked/revoked role assignment identity cannot be rewritten. Revoke and create a new assignment.")
                )

        if "state" in vals and not self.env.context.get("onehr_role_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use the controlled role-assignment workflow actions to change state."))

        before = {
            record.id: {
                "valid_to": record.valid_to,
                "state": record.state,
                "assignment_reason": record.assignment_reason,
            }
            for record in self
        }
        result = super().write(vals)

        auditable = {"valid_to", "assignment_reason"} & set(vals)
        if auditable:
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("OneHR role assignment updated"),
                    severity="medium",
                    record=record,
                    company=record.company_id,
                    role=record.role_id,
                    user_role=record,
                    changed_fields=auditable,
                    before=before[record.id],
                    after={
                        "valid_to": record.valid_to,
                        "state": record.state,
                        "assignment_reason": record.assignment_reason,
                    },
                )
            self.mapped("user_id")._reconcile_onehr_groups(system=True)

        return result

    # ------------------------------------------------------------------
    # Effective-state helpers
    # ------------------------------------------------------------------

    @api.depends("state", "valid_from", "valid_to")
    def _compute_effective_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.state == "revoked":
                record.effective_status = "revoked"
            elif record.state == "blocked":
                record.effective_status = "blocked"
            elif record.state == "draft":
                record.effective_status = "draft"
            elif record.valid_from > today:
                record.effective_status = "scheduled"
            elif record.valid_to and record.valid_to < today:
                record.effective_status = "expired"
            else:
                record.effective_status = "effective"

    def _is_effective_today(self):
        self.ensure_one()
        return self.state == "active" and self.is_effective_on(fields.Date.context_today(self))

    def _effective_peer_assignments(self, as_of_date=None):
        self.ensure_one()
        as_of_date = fields.Date.to_date(as_of_date or self.valid_from)
        return self.search(
            [
                ("id", "!=", self.id),
                ("user_id", "=", self.user_id.id),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "active"),
                ("valid_from", "<=", as_of_date),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", as_of_date),
            ] + self._branch_scope_overlap_domain()
        )

    def _applicable_sod_conflicts(self):
        """Return current/planned conflicts for this assignment."""
        self.ensure_one()
        as_of_date = self.valid_from
        peers = self._effective_peer_assignments(as_of_date)
        role_ids = set(peers.mapped("role_id").ids) | {self.role_id.id}

        matrices = self.env["onehr.sod.matrix"].search(
            [
                ("active", "=", True),
                ("valid_from", "<=", as_of_date),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", as_of_date),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return matrices.filtered(lambda rule: rule.conflicts_with_roles(role_ids))

    def _find_conflicting_assignment(self, matrix):
        self.ensure_one()
        other_role = matrix.role_b_id if self.role_id == matrix.role_a_id else matrix.role_a_id
        return self._effective_peer_assignments(self.valid_from).filtered(
            lambda item: item.role_id == other_role
        )[:1]

    def _compute_conflict_count(self):
        Conflict = self.env["onehr.sod.conflict.log"]
        for record in self:
            record.conflict_count = Conflict.search_count(
                [
                    "|",
                    ("user_role_id", "=", record.id),
                    ("conflicting_user_role_id", "=", record.id),
                ]
            )

    # ------------------------------------------------------------------
    # Controlled workflow
    # ------------------------------------------------------------------

    def action_activate(self):
        require_security_manager(self.env)

        for record in self:
            if record.state == "active":
                continue
            if record.state == "revoked":
                raise UserError(_("A revoked role assignment cannot be reactivated; create a new assignment."))

            if not record.role_id.active or not record.role_id.is_effective_on(record.valid_from):
                raise UserError(
                    _("The OneHR role must be active and effective on the assignment start date.")
                )

            conflicts = record._applicable_sod_conflicts()
            deny_conflicts = conflicts.filtered(lambda rule: rule.enforcement == "deny")

            for matrix in conflicts:
                other = record._find_conflicting_assignment(matrix)
                self.env["onehr.sod.conflict.log"]._record_conflict(
                    matrix=matrix,
                    user=record.user_id,
                    company=record.company_id,
                    user_role=record,
                    conflicting_user_role=other,
                    details=_(
                        "Role %(role)s conflicts with %(other)s under SoD rule %(rule)s.",
                        role=record.role_id.display_name,
                        other=(
                            other.role_id.display_name
                            if other
                            else _("[planned/effective role]")
                        ),
                        rule=matrix.display_name,
                    ),
                )

            if deny_conflicts:
                record.with_context(onehr_role_state_action=True).write({"state": "blocked"})
                self.env["onehr.audit.log"]._log_event(
                    action="activate",
                    summary=_("Role activation blocked by Segregation of Duties"),
                    severity="critical",
                    record=record,
                    company=record.company_id,
                    role=record.role_id,
                    user_role=record,
                    metadata={"deny_matrix_ids": deny_conflicts.ids},
                )
                continue

            record.with_context(onehr_role_state_action=True).write(
                {
                    "state": "active",
                    "activated_at": fields.Datetime.now(),
                    "activated_by_id": self.env.user.id,
                }
            )
            record.user_id._reconcile_onehr_groups(system=True)
            self.env["onehr.audit.log"]._log_event(
                action="activate",
                summary=_("OneHR role assignment activated"),
                severity="high",
                record=record,
                company=record.company_id,
                role=record.role_id,
                user_role=record,
                metadata={"warn_matrix_ids": conflicts.filtered(lambda rule: rule.enforcement == "warn").ids},
            )

        return True

    def action_recheck_sod(self):
        """Re-evaluate and materialize current/planned conflict evidence."""
        require_security_manager(self.env)

        for record in self:
            for matrix in record._applicable_sod_conflicts():
                other = record._find_conflicting_assignment(matrix)
                self.env["onehr.sod.conflict.log"]._record_conflict(
                    matrix=matrix,
                    user=record.user_id,
                    company=record.company_id,
                    user_role=record,
                    conflicting_user_role=other,
                    details=_(
                        "Manual SoD recheck: role %(role)s conflicts under rule %(rule)s.",
                        role=record.role_id.display_name,
                        rule=matrix.display_name,
                    ),
                )
        return True

    def action_revoke(self):
        require_security_manager(self.env)

        for record in self:
            if record.state == "revoked":
                continue
            record.with_context(onehr_role_state_action=True).write(
                {
                    "state": "revoked",
                    "revoked_at": fields.Datetime.now(),
                    "revoked_by_id": self.env.user.id,
                    "revocation_reason": _("Revoked through OneHR Security controlled action."),
                }
            )
            record.user_id._reconcile_onehr_groups(system=True)
            self.env["onehr.audit.log"]._log_event(
                action="revoke",
                summary=_("OneHR role assignment revoked"),
                severity="high",
                record=record,
                company=record.company_id,
                role=record.role_id,
                user_role=record,
            )
        return True

    def action_open_user(self):
        self.ensure_one()
        return open_record_action(
            name=self.user_id.display_name,
            res_model="res.users",
            res_id=self.user_id.id,
        )

    def action_open_role(self):
        self.ensure_one()
        return open_record_action(
            name=self.role_id.display_name,
            res_model="onehr.role",
            res_id=self.role_id.id,
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_assignments(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(
                _("Only draft role assignments may be deleted. Revoke activated history instead.")
            )

    @api.model
    def _cron_reconcile_current_access(self):
        """Daily enforcement for assignments that begin or expire by date."""
        users = self.search([("state", "=", "active")]).mapped("user_id")
        if users:
            users._reconcile_onehr_groups(system=True)
        return True
