from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action
from .routing_helpers import is_workflow_manager


class OneHRApprovalDelegate(models.Model):
    _name = "onehr.approval.delegate"
    _description = "OneHR Approval Delegation"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "valid_from desc, id desc"

    delegator_user_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", index=True, tracking=True
    )
    delegate_user_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", index=True, tracking=True
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    scope_type = fields.Selection(
        [("role", "OneHR Role"), ("rule", "Approval Rule")],
        required=True,
        default="role",
        tracking=True,
    )
    role_id = fields.Many2one("onehr.role", ondelete="restrict", tracking=True)
    rule_id = fields.Many2one("onehr.approval.rule", ondelete="restrict", tracking=True)

    reason = fields.Text(required=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("revoked", "Revoked")],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    activated_at = fields.Datetime(readonly=True)
    activated_by_id = fields.Many2one("res.users", readonly=True)
    revoked_at = fields.Datetime(readonly=True)
    revoked_by_id = fields.Many2one("res.users", readonly=True)
    revocation_reason = fields.Text(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            delegator_id = values.get("delegator_user_id") or self.env.user.id
            if delegator_id != self.env.user.id and not is_workflow_manager(self.env):
                raise AccessError(_("Only Workflow Managers may create delegation for another user."))
            values["delegator_user_id"] = delegator_id
            values["state"] = "draft"
            prepared.append(values)
        return super().create(prepared)

    def write(self, vals):
        if any(record.delegator_user_id != self.env.user for record in self) and not is_workflow_manager(self.env):
            raise AccessError(_("You may only maintain your own approval delegations."))

        if "state" in vals and not self.env.context.get("onehr_delegate_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use controlled delegation workflow actions to change state."))

        protected = {
            "delegator_user_id",
            "delegate_user_id",
            "company_id",
            "scope_type",
            "role_id",
            "rule_id",
            "valid_from",
        }
        if protected & set(vals) and any(record.state != "draft" for record in self):
            raise AccessError(_("Activated/revoked delegation identity cannot be rewritten."))
        return super().write(vals)

    @api.constrains(
        "delegator_user_id",
        "delegate_user_id",
        "company_id",
        "scope_type",
        "role_id",
        "rule_id",
    )
    def _check_scope_and_users(self):
        for record in self:
            if record.delegator_user_id == record.delegate_user_id:
                raise ValidationError(_("An approver cannot delegate to the same user."))
            if record.company_id not in record.delegator_user_id.company_ids:
                raise ValidationError(_("Delegator is not allowed in the delegation company."))
            if record.company_id not in record.delegate_user_id.company_ids:
                raise ValidationError(_("Delegate is not allowed in the delegation company."))
            approver_group = self.env.ref("onehr_workflow_approval.group_onehr_approver")
            if approver_group not in record.delegator_user_id.group_ids:
                raise ValidationError(_("Delegator must hold the OneHR Approver application group."))
            if approver_group not in record.delegate_user_id.group_ids:
                raise ValidationError(_("Delegate must hold the OneHR Approver application group."))

            if record.scope_type == "role":
                if not record.role_id or record.rule_id:
                    raise ValidationError(_("Role scope requires exactly one OneHR Role."))
                if record.role_id.company_id and record.role_id.company_id != record.company_id:
                    raise ValidationError(_("Delegated role must be global or belong to the delegation company."))
            else:
                if not record.rule_id or record.role_id:
                    raise ValidationError(_("Rule scope requires exactly one Approval Rule."))
                if record.rule_id.company_id and record.rule_id.company_id != record.company_id:
                    raise ValidationError(_("Delegated rule must be global or belong to the delegation company."))

    @api.constrains(
        "delegator_user_id",
        "company_id",
        "scope_type",
        "role_id",
        "rule_id",
        "valid_from",
        "valid_to",
        "state",
    )
    def _check_active_overlap(self):
        for record in self.filtered(lambda item: item.state == "active"):
            domain = [
                ("id", "!=", record.id),
                ("delegator_user_id", "=", record.delegator_user_id.id),
                ("company_id", "=", record.company_id.id),
                ("scope_type", "=", record.scope_type),
                ("state", "=", "active"),
                ("valid_from", "<=", record.valid_to or fields.Date.to_date("9999-12-31")),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", record.valid_from),
            ]
            domain.append(
                ("role_id", "=", record.role_id.id)
                if record.scope_type == "role"
                else ("rule_id", "=", record.rule_id.id)
            )
            if self.search_count(domain, limit=1):
                raise ValidationError(
                    _("Overlapping active delegation for the same authority scope is not allowed.")
                )

    def action_activate(self):
        for record in self:
            if record.state == "active":
                continue
            if record.state == "revoked":
                raise UserError(_("A revoked delegation cannot be reactivated."))
            if record.delegator_user_id != self.env.user and not is_workflow_manager(self.env):
                raise AccessError(_("Only the delegator or Workflow Manager may activate delegation."))

            if record.scope_type == "role":
                # Narrow authority verification: the delegator cannot see other users'
                # role assignments, therefore verification is performed with metadata-only sudo.
                assignment = self.env["onehr.user.role"].sudo().search(
                    [
                        ("user_id", "=", record.delegator_user_id.id),
                        ("role_id", "=", record.role_id.id),
                        ("company_id", "=", record.company_id.id),
                        ("state", "=", "active"),
                        ("valid_from", "<=", record.valid_from),
                        "|",
                        ("valid_to", "=", False),
                        ("valid_to", ">=", record.valid_from),
                    ],
                    limit=1,
                )
                if not assignment:
                    raise UserError(
                        _("Delegator does not hold the delegated OneHR role on the delegation start date.")
                    )

            record.with_context(onehr_delegate_state_action=True).write(
                {
                    "state": "active",
                    "activated_at": fields.Datetime.now(),
                    "activated_by_id": self.env.user.id,
                }
            )
            self.env["onehr.audit.log"]._log_event(
                action="activate",
                summary=_(
                    "Approval authority delegated from %(source)s to %(target)s",
                    source=record.delegator_user_id.display_name,
                    target=record.delegate_user_id.display_name,
                ),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={
                    "workflow_event": "approval_delegate_activate",
                    "scope_type": record.scope_type,
                    "role_id": record.role_id.id,
                    "rule_id": record.rule_id.id,
                },
            )
        return True

    def action_revoke(self):
        for record in self.filtered(lambda item: item.state == "active"):
            if record.delegator_user_id != self.env.user and not is_workflow_manager(self.env):
                raise AccessError(_("Only the delegator or Workflow Manager may revoke delegation."))
            record.with_context(onehr_delegate_state_action=True).write(
                {
                    "state": "revoked",
                    "revoked_at": fields.Datetime.now(),
                    "revoked_by_id": self.env.user.id,
                    "revocation_reason": _("Revoked through controlled approval delegation action."),
                }
            )
            self.env["onehr.audit.log"]._log_event(
                action="revoke",
                summary=_("Approval delegation revoked"),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={"workflow_event": "approval_delegate_revoke"},
            )
        return True

    @api.model
    def effective_delegate_map(self, *, delegator_ids, step, as_of_date, company):
        """Return delegate -> delegator only for already-resolved base authorities."""
        if not step.allow_delegation or not delegator_ids:
            return {}

        as_of_date = fields.Date.to_date(as_of_date)
        # Routing-only sudo prevents broad delegation ACL grants to requesters.
        delegations = self.sudo().search(
            [
                ("delegator_user_id", "in", list(delegator_ids)),
                ("company_id", "=", company.id),
                ("state", "=", "active"),
                ("valid_from", "<=", as_of_date),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", as_of_date),
            ]
        )
        if step.approver_policy == "onehr_role" and step.role_id:
            delegations = delegations.filtered(
                lambda item: (
                    item.scope_type == "role" and item.role_id == step.role_id
                )
                or (
                    item.scope_type == "rule" and item.rule_id == step.rule_id
                )
            )
        else:
            delegations = delegations.filtered(
                lambda item: item.scope_type == "rule" and item.rule_id == step.rule_id
            )

        result = {}
        for delegation in delegations:
            if delegation.delegate_user_id.active and not delegation.delegate_user_id.share:
                result[delegation.delegate_user_id.id] = delegation.delegator_user_id.id
        return result

    def action_open_delegator(self):
        self.ensure_one()
        return open_record_action(
            name=self.delegator_user_id.display_name,
            res_model="res.users",
            res_id=self.delegator_user_id.id,
        )

    def action_open_delegate(self):
        self.ensure_one()
        return open_record_action(
            name=self.delegate_user_id.display_name,
            res_model="res.users",
            res_id=self.delegate_user_id.id,
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_delegations(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only draft approval delegations may be deleted."))
