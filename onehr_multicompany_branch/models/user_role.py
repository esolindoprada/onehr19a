# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class OneHRUserRole(models.Model):
    """Branch-aware extension of the security-owned effective role assignment."""

    _inherit = "onehr.user.role"

    branch_id = fields.Many2one(
        "onehr.branch",
        string="Branch Scope",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        help="Empty means company-wide role scope. A branch value narrows the role to that operational branch.",
    )

    @api.constrains("branch_id", "company_id", "user_id", "valid_from", "valid_to", "state")
    def _check_branch_scope_integrity(self):
        for record in self:
            record._validate_branch_scope_integrity()

    def _validate_branch_scope_integrity(self):
        self.ensure_one()
        branch = self.branch_id
        if not branch:
            return True
        if branch.company_id != self.company_id:
            raise ValidationError(_("Role assignment branch must belong to the assignment company."))
        if not self.company_id.onehr_branch_enabled:
            raise ValidationError(_("Enable OneHR Branch Scope for the company before assigning a branch-scoped role."))
        if branch not in self.user_id.onehr_allowed_branch_ids:
            raise ValidationError(_("Role assignment branch must be inside the user's explicit allowed-branch scope."))
        if not branch.active:
            raise ValidationError(_("An archived branch cannot receive a role assignment."))
        if self.valid_from < branch.valid_from:
            raise ValidationError(_("Role assignment cannot start before the branch becomes effective."))
        if branch.valid_to and (not self.valid_to or self.valid_to > branch.valid_to):
            raise ValidationError(_("Role assignment cannot remain effective beyond the branch effective period."))
        return True

    def _branch_scope_overlap_domain(self):
        """Prevent duplicate/subsumed role authority across company and branch scope.

        A company-wide assignment overlaps every branch-specific assignment for the
        same user/role/company. A branch-specific assignment overlaps another row
        for the same branch and any company-wide row.
        """
        self.ensure_one()
        if not self.branch_id:
            return []
        return ["|", ("branch_id", "=", False), ("branch_id", "=", self.branch_id.id)]

    def _branch_scope_label(self):
        self.ensure_one()
        return self.branch_id.display_name if self.branch_id else _("All Branches in Company")

    def write(self, vals):
        if "branch_id" in vals and any(record.state in ("active", "blocked", "revoked") for record in self):
            raise AccessError(
                _("Branch scope is part of role-assignment identity after activation. Revoke and create a new assignment instead.")
            )

        before = {record.id: record.branch_id.id or False for record in self}
        result = super().write(vals)

        if "branch_id" in vals:
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("OneHR role assignment branch scope updated"),
                    severity="high",
                    record=record,
                    company=record.company_id,
                    role=record.role_id,
                    user_role=record,
                    changed_fields={"branch_id"},
                    before={"branch_id": before[record.id]},
                    after={"branch_id": record.branch_id.id or False},
                )
        return result

    def action_activate(self):
        for record in self:
            record._validate_branch_scope_integrity()
            if record.branch_id and not record.branch_id.is_effective_on(record.valid_from):
                raise UserError(_("The branch must be effective on the role-assignment start date."))
        return super().action_activate()
