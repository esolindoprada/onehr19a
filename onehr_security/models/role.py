
from odoo import _, api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import open_records_action, require_security_manager


class OneHRRole(models.Model):
    """Business role catalogue mapped to canonical Odoo res.groups."""

    _name = "onehr.role"
    _description = "OneHR Business Role"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "sequence, code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)

    company_id = fields.Many2one(
        "res.company",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for a role definition reusable across companies.",
    )
    active = fields.Boolean(default=True, tracking=True)

    sensitivity = fields.Selection(
        [
            ("standard", "Standard"),
            ("controlled", "Controlled"),
            ("sensitive", "Sensitive"),
            ("restricted", "Restricted"),
        ],
        required=True,
        default="standard",
        tracking=True,
        help=(
            "Classification only. Actual field/model access remains enforced by "
            "the mapped Odoo groups and the owning domain addon's ACL/rules."
        ),
    )

    group_ids = fields.Many2many(
        "res.groups",
        "onehr_role_res_groups_rel",
        "role_id",
        "group_id",
        string="Mapped Odoo Groups",
        tracking=True,
        help="Canonical Odoo groups granted while this OneHR role is effective.",
    )

    assignment_ids = fields.One2many("onehr.user.role", "role_id", string="Role Assignments")
    sod_rule_a_ids = fields.One2many("onehr.sod.matrix", "role_a_id", string="SoD Rules A")
    sod_rule_b_ids = fields.One2many("onehr.sod.matrix", "role_b_id", string="SoD Rules B")

    assignment_count = fields.Integer(compute="_compute_counts", string="Assignments")
    active_user_count = fields.Integer(compute="_compute_counts", string="Effective Users")
    sod_rule_count = fields.Integer(compute="_compute_counts", string="SoD Rules")

    def _check_group_mapping_authority(self, values):
        """Prevent a Security Manager from turning role mapping into privilege escalation."""
        if "group_ids" not in values or self.env.uid == SUPERUSER_ID:
            return

        if not self.env.user.has_group("onehr_security.group_onehr_security_admin"):
            raise AccessError(_("Only OneHR Security Admin may change Odoo group mappings."))

    def _check_protected_group_mapping(self):
        """Governance groups are assigned directly, never through a business role."""
        protected = (
            self.env.ref("base.group_system")
            | self.env.ref("base.group_erp_manager")
            | self.env.ref("base.group_sanitize_override")
            | self.env.ref("base.group_no_one")
            | self.env.ref("base.group_portal")
            | self.env.ref("base.group_public")
            | self.env.ref("onehr_security.group_onehr_security_user")
            | self.env.ref("onehr_security.group_onehr_security_manager")
            | self.env.ref("onehr_security.group_onehr_security_admin")
            | self.env.ref("onehr_security.group_onehr_compliance_officer")
        )
        for record in self:
            if record.group_ids & protected:
                raise ValidationError(
                    _(
                        "Technical access-rights administration and OneHR security-governance "
                        "groups cannot be granted indirectly through a business role."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_group_mapping_authority(vals)
            vals["code"] = (vals.get("code") or "").strip().upper()

        records = super().create(vals_list)
        records._check_protected_group_mapping()
        Audit = self.env["onehr.audit.log"]
        for record in records:
            Audit._log_event(
                action="create",
                summary=_("OneHR role created: %s", record.display_name),
                severity="medium",
                record=record,
                company=record.company_id,
                role=record,
                after={
                    "code": record.code,
                    "group_ids": record.group_ids.ids,
                    "sensitivity": record.sensitivity,
                },
            )
        return records

    def write(self, vals):
        self._check_group_mapping_authority(vals)

        before = {
            record.id: {
                "code": record.code,
                "group_ids": record.group_ids.ids,
                "active": record.active,
                "sensitivity": record.sensitivity,
            }
            for record in self
        }

        if "code" in vals:
            vals = dict(vals)
            vals["code"] = (vals.get("code") or "").strip().upper()

        result = super().write(vals)
        if "group_ids" in vals:
            self._check_protected_group_mapping()

        if {"code", "name", "group_ids", "active", "sensitivity", "valid_from", "valid_to"} & set(vals):
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("OneHR role updated: %s", record.display_name),
                    severity="high" if "group_ids" in vals else "medium",
                    record=record,
                    company=record.company_id,
                    role=record,
                    changed_fields=set(vals),
                    before=before[record.id],
                    after={
                        "code": record.code,
                        "group_ids": record.group_ids.ids,
                        "active": record.active,
                        "sensitivity": record.sensitivity,
                    },
                )

        if {"group_ids", "active", "valid_from", "valid_to"} & set(vals):
            users = self.assignment_ids.mapped("user_id")
            if users:
                users._reconcile_onehr_groups(system=True)

        return result

    @api.constrains("code", "company_id")
    def _check_unique_code_scope(self):
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("code", "=ilike", record.code),
                ("company_id", "=", record.company_id.id if record.company_id else False),
            ]
            if self.with_context(active_test=False).search_count(domain, limit=1):
                raise ValidationError(_("Role code must be unique in its company/global scope."))

    def _compute_counts(self):
        Assignment = self.env["onehr.user.role"]
        Matrix = self.env["onehr.sod.matrix"]
        today = fields.Date.context_today(self)

        for record in self:
            record.assignment_count = Assignment.search_count([("role_id", "=", record.id)])
            if record.active and record.is_effective_on(today):
                record.active_user_count = Assignment.search_count(
                    [
                        ("role_id", "=", record.id),
                        ("state", "=", "active"),
                        ("valid_from", "<=", today),
                        "|",
                        ("valid_to", "=", False),
                        ("valid_to", ">=", today),
                    ]
                )
            else:
                record.active_user_count = 0
            record.sod_rule_count = Matrix.search_count(
                [
                    "|",
                    ("role_a_id", "=", record.id),
                    ("role_b_id", "=", record.id),
                ]
            )

    def action_open_assignments(self):
        self.ensure_one()
        return open_records_action(
            name=_("Assignments — %s", self.display_name),
            res_model="onehr.user.role",
            domain=[("role_id", "=", self.id)],
            context={"default_role_id": self.id},
        )

    def action_open_effective_users(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return open_records_action(
            name=_("Effective Users — %s", self.display_name),
            res_model="onehr.user.role",
            domain=[
                ("role_id", "=", self.id),
                ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", today),
            ],
        )

    def action_open_sod_rules(self):
        self.ensure_one()
        return open_records_action(
            name=_("SoD Rules — %s", self.display_name),
            res_model="onehr.sod.matrix",
            domain=["|", ("role_a_id", "=", self.id), ("role_b_id", "=", self.id)],
        )

    def action_reconcile_assigned_users(self):
        require_security_manager(self.env)
        users = self.assignment_ids.mapped("user_id")
        if users:
            users._reconcile_onehr_groups()
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        """Security-role definitions are governed history; archive them instead."""
        raise ValidationError(
            _("OneHR roles cannot be deleted. Archive the role to preserve security history.")
        )
