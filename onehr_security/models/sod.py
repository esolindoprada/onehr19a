
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import (
    open_record_action,
    open_records_action,
    require_security_admin_or_compliance,
)


class OneHRSodMatrix(models.Model):
    _name = "onehr.sod.matrix"
    _description = "OneHR Segregation of Duties Matrix"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "severity desc, code"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for a global SoD rule.",
    )
    active = fields.Boolean(default=True, tracking=True)

    role_a_id = fields.Many2one("onehr.role", required=True, ondelete="restrict", index=True, tracking=True)
    role_b_id = fields.Many2one("onehr.role", required=True, ondelete="restrict", index=True, tracking=True)

    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        required=True,
        default="high",
        index=True,
        tracking=True,
    )
    enforcement = fields.Selection(
        [("warn", "Warn"), ("deny", "Deny")],
        required=True,
        default="deny",
        index=True,
        tracking=True,
    )
    mitigation_guidance = fields.Text(translate=True)
    conflict_count = fields.Integer(compute="_compute_conflict_count", string="Detected Conflicts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["code"] = (vals.get("code") or "").strip().upper()

        records = super().create(vals_list)
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_("SoD policy created: %s", record.display_name),
                severity="high",
                record=record,
                company=record.company_id,
                after={
                    "code": record.code,
                    "role_a_id": record.role_a_id.id,
                    "role_b_id": record.role_b_id.id,
                    "severity": record.severity,
                    "enforcement": record.enforcement,
                    "active": record.active,
                    "valid_from": record.valid_from,
                    "valid_to": record.valid_to,
                },
            )
        return records

    def write(self, vals):
        before = {
            record.id: {
                "code": record.code,
                "role_a_id": record.role_a_id.id,
                "role_b_id": record.role_b_id.id,
                "severity": record.severity,
                "enforcement": record.enforcement,
                "active": record.active,
                "valid_from": record.valid_from,
                "valid_to": record.valid_to,
            }
            for record in self
        }

        if "code" in vals:
            vals = dict(vals)
            vals["code"] = (vals.get("code") or "").strip().upper()

        result = super().write(vals)

        auditable = {
            "code",
            "name",
            "company_id",
            "role_a_id",
            "role_b_id",
            "severity",
            "enforcement",
            "mitigation_guidance",
            "active",
            "valid_from",
            "valid_to",
        } & set(vals)

        if auditable:
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("SoD policy updated: %s", record.display_name),
                    severity="high",
                    record=record,
                    company=record.company_id,
                    changed_fields=auditable,
                    before=before[record.id],
                    after={
                        "code": record.code,
                        "role_a_id": record.role_a_id.id,
                        "role_b_id": record.role_b_id.id,
                        "severity": record.severity,
                        "enforcement": record.enforcement,
                        "active": record.active,
                        "valid_from": record.valid_from,
                        "valid_to": record.valid_to,
                    },
                )

        return result

    @api.constrains("role_a_id", "role_b_id")
    def _check_distinct_roles(self):
        for record in self:
            if record.role_a_id == record.role_b_id:
                raise ValidationError(_("A SoD rule must compare two different roles."))

    @api.constrains(
        "role_a_id",
        "role_b_id",
        "company_id",
        "valid_from",
        "valid_to",
        "active",
    )
    def _check_no_symmetric_overlap(self):
        """Reject A/B and B/A duplicates for the same effective scope."""
        far_future = fields.Date.to_date("9999-12-31")
        for record in self.filtered("active"):
            pair_domain = [
                ("id", "!=", record.id),
                ("active", "=", True),
                ("company_id", "=", record.company_id.id if record.company_id else False),
                ("valid_from", "<=", record.valid_to or far_future),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", record.valid_from),
                "|",
                "&",
                ("role_a_id", "=", record.role_a_id.id),
                ("role_b_id", "=", record.role_b_id.id),
                "&",
                ("role_a_id", "=", record.role_b_id.id),
                ("role_b_id", "=", record.role_a_id.id),
            ]
            if self.search_count(pair_domain, limit=1):
                raise ValidationError(_("An overlapping SoD rule already exists for this role pair and scope."))

    def applies_to_company(self, company):
        self.ensure_one()
        return not self.company_id or self.company_id == company

    def conflicts_with_roles(self, role_ids):
        self.ensure_one()
        role_ids = set(role_ids)
        return self.role_a_id.id in role_ids and self.role_b_id.id in role_ids

    def _compute_conflict_count(self):
        Log = self.env["onehr.sod.conflict.log"]
        for record in self:
            record.conflict_count = Log.search_count([("matrix_id", "=", record.id)])

    def action_open_conflicts(self):
        self.ensure_one()
        return open_records_action(
            name=_("SoD Conflicts — %s", self.display_name),
            res_model="onehr.sod.conflict.log",
            domain=[("matrix_id", "=", self.id)],
            context={"default_matrix_id": self.id},
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        """SoD policies are security evidence; archive them instead of deleting."""
        raise ValidationError(
            _("SoD matrix rules cannot be deleted. Archive the rule to preserve policy history.")
        )

    def action_scan_effective_assignments(self):
        """Materialize current conflicts for compliance review without changing access."""
        today = fields.Date.context_today(self)
        for rule in self:
            assignments = self.env["onehr.user.role"].search(
                [
                    ("state", "=", "active"),
                    ("valid_from", "<=", today),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", today),
                    ("role_id", "in", [rule.role_a_id.id, rule.role_b_id.id]),
                ]
            )
            for user in assignments.mapped("user_id"):
                user_assignments = assignments.filtered(lambda item: item.user_id == user)
                role_ids = user_assignments.mapped("role_id").ids
                if rule.conflicts_with_roles(role_ids):
                    assignment_a = user_assignments.filtered(lambda item: item.role_id == rule.role_a_id)[:1]
                    assignment_b = user_assignments.filtered(lambda item: item.role_id == rule.role_b_id)[:1]
                    self.env["onehr.sod.conflict.log"]._record_conflict(
                        matrix=rule,
                        user=user,
                        company=rule.company_id or user.company_id,
                        user_role=assignment_a or assignment_b,
                        conflicting_user_role=assignment_b or assignment_a,
                        details=_("Current effective role combination matches this SoD rule."),
                    )
        return True


class OneHRSodConflictLog(models.Model):
    """ED3 immutable evidence of conflict detection and human resolution."""

    _name = "onehr.sod.conflict.log"
    _description = "OneHR SoD Conflict Evidence"
    _inherit = ["onehr.mixin.audit"]
    _order = "detected_at desc, id desc"

    detected_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="restrict", index=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True, readonly=True)
    matrix_id = fields.Many2one("onehr.sod.matrix", required=True, ondelete="restrict", index=True, readonly=True)
    user_role_id = fields.Many2one("onehr.user.role", ondelete="set null", readonly=True)
    conflicting_user_role_id = fields.Many2one("onehr.user.role", ondelete="set null", readonly=True)

    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        required=True,
        readonly=True,
    )
    enforcement = fields.Selection(
        [("warn", "Warn"), ("deny", "Deny")],
        required=True,
        readonly=True,
    )
    details = fields.Text(readonly=True)
    mitigation_guidance = fields.Text(readonly=True)

    state = fields.Selection(
        [
            ("open", "Open"),
            ("accepted", "Risk Accepted"),
            ("mitigated", "Mitigated"),
            ("resolved", "Resolved"),
        ],
        required=True,
        default="open",
        index=True,
        tracking=True,
    )

    resolution_comment = fields.Text(
        string="Resolution Comment",
        help="Human compliance note captured before the decision is finalized.",
    )
    resolved_at = fields.Datetime(readonly=True)
    resolved_by_id = fields.Many2one("res.users", readonly=True)
    resolution_note = fields.Text(readonly=True)

    @api.model
    def _record_conflict(
        self,
        *,
        matrix,
        user,
        company,
        user_role=None,
        conflicting_user_role=None,
        details=None,
    ):
        """Create evidence once per unresolved matrix/user/scope conflict."""
        existing = self.search(
            [
                ("matrix_id", "=", matrix.id),
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("state", "=", "open"),
            ],
            limit=1,
        )
        if existing:
            return existing

        # Narrow evidence-only sudo. `_record_conflict` is private and is
        # called only after a concrete SoD detection in authorized business flow.
        record = self.sudo().create(
            {
                "detected_at": fields.Datetime.now(),
                "user_id": user.id,
                "company_id": company.id,
                "matrix_id": matrix.id,
                "user_role_id": user_role.id if user_role else False,
                "conflicting_user_role_id": conflicting_user_role.id if conflicting_user_role else False,
                "severity": matrix.severity,
                "enforcement": matrix.enforcement,
                "details": details,
                "mitigation_guidance": matrix.mitigation_guidance,
            }
        )
        self.env["onehr.audit.log"]._log_event(
            action="sod_detect",
            summary=_("SoD conflict detected for %s", user.display_name),
            severity="critical" if matrix.severity == "critical" else "high",
            record=record,
            company=company,
            role=user_role.role_id if user_role else False,
            user_role=user_role,
            metadata={
                "matrix_id": matrix.id,
                "enforcement": matrix.enforcement,
                "conflicting_user_role_id": conflicting_user_role.id if conflicting_user_role else False,
            },
        )
        return record

    def _resolve(self, state, note):
        require_security_admin_or_compliance(self.env)

        if state not in {"accepted", "mitigated", "resolved"}:
            raise ValidationError(_("Unsupported SoD resolution state."))

        for record in self:
            if record.state != "open":
                raise UserError(_("A finalized SoD decision cannot be rewritten."))

            record.with_context(onehr_sod_resolution=True).write(
                {
                    "state": state,
                    "resolved_at": fields.Datetime.now(),
                    "resolved_by_id": self.env.user.id,
                    "resolution_note": record.resolution_comment or note or _("Resolved through OneHR compliance action."),
                }
            )
            self.env["onehr.audit.log"]._log_event(
                action="sod_resolve",
                summary=_("SoD conflict resolution recorded"),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={
                    "resolution_state": state,
                    "resolution_note": record.resolution_comment or note,
                },
            )
        return True

    def action_accept_risk(self):
        return self._resolve("accepted", _("Risk accepted by authorized compliance user."))

    def action_mark_mitigated(self):
        return self._resolve("mitigated", _("Mitigation completed and evidenced."))

    def action_resolve(self):
        return self._resolve("resolved", _("Conflict reviewed and resolved."))

    def write(self, vals):
        if not self.env.context.get("onehr_sod_resolution"):
            protected = {
                "detected_at", "user_id", "company_id", "matrix_id",
                "user_role_id", "conflicting_user_role_id", "severity",
                "enforcement", "details", "mitigation_guidance", "state",
                "resolved_at", "resolved_by_id", "resolution_note",
            }
            if protected & set(vals):
                raise AccessError(_("SoD conflict evidence is immutable outside controlled resolution actions."))

        for record in self:
            if (
                record.state != "open"
                and set(vals)
                & {
                    "state",
                    "resolution_comment",
                    "resolved_at",
                    "resolved_by_id",
                    "resolution_note",
                }
            ):
                raise AccessError(_("A finalized SoD decision cannot be rewritten."))

        if "resolution_comment" in vals:
            require_security_admin_or_compliance(self.env)

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("SoD conflict evidence cannot be deleted."))

    def action_open_user(self):
        self.ensure_one()
        return open_record_action(
            name=self.user_id.display_name,
            res_model="res.users",
            res_id=self.user_id.id,
        )

    def action_open_matrix(self):
        self.ensure_one()
        return open_record_action(
            name=self.matrix_id.display_name,
            res_model="onehr.sod.matrix",
            res_id=self.matrix_id.id,
        )
