
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .routing_helpers import (
    APPROVER_GROUP,
    clean_ids,
    require_workflow_manager,
    structured_match,
    validate_structured_match,
)


RISK_LEVELS = [
    ("any", "Any"),
    ("low", "Low"),
    ("normal", "Normal"),
    ("high", "High"),
    ("critical", "Critical"),
]


class OneHRApprovalRule(models.Model):
    _name = "onehr.approval.rule"
    _description = "OneHR Approval Rule Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "priority desc, code, version desc"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    version = fields.Integer(required=True, default=1, tracking=True)

    company_id = fields.Many2one(
        "res.company",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for a global rule reusable by all allowed companies.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Source Model",
        required=True,
        # Odoo 19 explicitly rejects ondelete="restrict" for ir.model and the
        # other framework metadata models in IR_MODELS. Because Source Model is
        # required, "set null" would also be invalid; cascade is the compatible
        # policy and keeps the field mandatory without changing model ownership.
        ondelete="cascade",
        tracking=True,
    )
    source_model = fields.Char(related="model_id.model", store=True, index=True)
    document_type = fields.Char(
        index=True,
        tracking=True,
        help="Optional source-defined document type/key.",
    )
    branch_scope_key = fields.Char(
        index=True,
        tracking=True,
        help=(
            "Optional branch/site scope key. The future branch addon can supply "
            "the same key through the source approval context without a reverse dependency."
        ),
    )
    requester_role_id = fields.Many2one(
        "onehr.role",
        ondelete="restrict",
        tracking=True,
        help="Optional OneHR business role required on the requester.",
    )

    min_amount = fields.Float(tracking=True)
    max_amount = fields.Float(tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Threshold Currency",
        ondelete="restrict",
        tracking=True,
        help="The source contract must normalize amount to this currency before matching.",
    )
    risk_level = fields.Selection(RISK_LEVELS, required=True, default="any", tracking=True)
    context_match_json = fields.Json(
        string="Structured Context Match",
        default=dict,
        help=(
            "Safe exact-match criteria for department/position/grade/source-specific keys. "
            "Values are scalars or lists; executable expressions are forbidden."
        ),
    )

    priority = fields.Integer(default=100, index=True, tracking=True)
    minimum_distinct_approvers = fields.Integer(
        default=1,
        required=True,
        tracking=True,
        help="Minimum distinct authority identities required before final approval.",
    )
    auto_approve = fields.Boolean(
        tracking=True,
        help="Use only for explicitly governed low-risk matrix criteria.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )

    step_ids = fields.One2many(
        "onehr.approval.step",
        "rule_id",
        string="Approval Steps",
        copy=True,
    )
    step_count = fields.Integer(compute="_compute_counts", string="Steps")
    request_count = fields.Integer(compute="_compute_counts", string="Requests")

    @api.model_create_multi
    def create(self, vals_list):
        require_workflow_manager(self.env)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            values["code"] = (values.get("code") or "").strip().upper()
            values["state"] = "draft"
            prepared.append(values)
        return super().create(prepared)

    def write(self, vals):
        require_workflow_manager(self.env)

        if "state" in vals and not self.env.context.get("onehr_rule_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use controlled rule workflow actions to change state."))

        protected = {
            "code",
            "version",
            "company_id",
            "model_id",
            "document_type",
            "branch_scope_key",
            "requester_role_id",
            "min_amount",
            "max_amount",
            "currency_id",
            "risk_level",
            "context_match_json",
            "priority",
            "minimum_distinct_approvers",
            "auto_approve",
            "valid_from",
            "valid_to",
            "step_ids",
        }
        if protected & set(vals) and any(record.state != "draft" for record in self):
            raise AccessError(
                _(
                    "Activated/retired approval-rule versions are immutable. "
                    "Create a new version instead."
                )
            )

        if "code" in vals:
            vals = dict(vals)
            vals["code"] = (vals.get("code") or "").strip().upper()
        return super().write(vals)

    @api.constrains("code", "company_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [
                    ("id", "!=", record.id),
                    ("code", "=ilike", record.code),
                    ("company_id", "=", record.company_id.id if record.company_id else False),
                    ("version", "=", record.version),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Approval-rule code/version must be unique in its company/global scope.")
                )

    @api.constrains("requester_role_id", "company_id")
    def _check_requester_role_scope(self):
        for record in self:
            if (
                record.requester_role_id
                and record.requester_role_id.company_id
                and record.company_id
                and record.requester_role_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _("Requester role company must match the rule company or be global.")
                )

    @api.constrains("min_amount", "max_amount", "minimum_distinct_approvers", "auto_approve")
    def _check_thresholds(self):
        for record in self:
            if record.min_amount < 0 or record.max_amount < 0:
                raise ValidationError(_("Approval amount thresholds cannot be negative."))
            if record.max_amount and record.max_amount < record.min_amount:
                raise ValidationError(_("Maximum amount must be at least minimum amount."))
            if record.minimum_distinct_approvers < 0:
                raise ValidationError(_("Minimum distinct approvers cannot be negative."))
            if record.auto_approve and record.minimum_distinct_approvers:
                raise ValidationError(
                    _("Automatic approval rules must use zero minimum distinct human approvers.")
                )

    @api.constrains("context_match_json")
    def _check_structured_context(self):
        for record in self:
            validate_structured_match(record.context_match_json)

    @api.constrains("code", "company_id", "valid_from", "valid_to", "state")
    def _check_active_version_overlap(self):
        for record in self.filtered(lambda item: item.state == "active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("state", "=", "active")],
                _("Active versions of the same approval-rule code cannot overlap."),
            )

    def _compute_counts(self):
        Request = self.env["onehr.approval.request"]
        for record in self:
            record.step_count = len(record.step_ids)
            record.request_count = Request.search_count([("rule_id", "=", record.id)])

    def matches_context(self, context_values, as_of_date=None):
        self.ensure_one()
        context_values = context_values or {}
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))

        if self.state != "active" or not self.is_effective_on(as_of_date):
            return False

        company_id = context_values.get("company_id")
        if self.company_id and self.company_id.id != company_id:
            return False
        if self.document_type and self.document_type != context_values.get("document_type"):
            return False
        if self.branch_scope_key and self.branch_scope_key != context_values.get("branch_scope_key"):
            return False
        if self.requester_role_id:
            if self.requester_role_id.id not in clean_ids(context_values.get("requester_role_ids")):
                return False

        amount = float(context_values.get("amount") or 0.0)
        if self.min_amount and amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        if self.currency_id and context_values.get("currency_id") != self.currency_id.id:
            return False
        if self.risk_level != "any" and self.risk_level != context_values.get("risk_level"):
            return False

        return structured_match(self.context_match_json, context_values.get("extra"))

    def match_specificity(self):
        self.ensure_one()
        return sum(
            [
                bool(self.company_id),
                bool(self.document_type),
                bool(self.branch_scope_key),
                bool(self.requester_role_id),
                bool(self.min_amount or self.max_amount),
                bool(self.currency_id),
                self.risk_level != "any",
                len(self.context_match_json or {}),
            ]
        )

    @api.model
    def resolve_for_context(self, source_model, context_values, as_of_date=None):
        """Resolve one deterministic rule or stop on an ambiguous matrix."""
        context_values = dict(context_values or {})
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        candidates = self.search(
            [
                ("state", "=", "active"),
                ("source_model", "=", source_model),
                ("valid_from", "<=", as_of_date),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", as_of_date),
            ]
        ).filtered(lambda rule: rule.matches_context(context_values, as_of_date))

        if not candidates:
            raise UserError(
                _(
                    "No active approval rule matches source model %(model)s and the "
                    "supplied structured context.",
                    model=source_model,
                )
            )

        ranked = sorted(
            candidates,
            key=lambda rule: (rule.priority, rule.match_specificity(), rule.version, rule.id),
            reverse=True,
        )
        winner = ranked[0]
        if len(ranked) > 1:
            contender = ranked[1]
            if (
                contender.priority == winner.priority
                and contender.match_specificity() == winner.match_specificity()
            ):
                raise UserError(
                    _(
                        "Approval matrix is ambiguous between %(first)s and %(second)s. "
                        "Adjust priority or make one rule more specific.",
                        first=winner.display_name,
                        second=contender.display_name,
                    )
                )
        return winner

    def action_activate(self):
        require_workflow_manager(self.env)
        for record in self:
            if record.state == "active":
                continue
            if record.state == "retired":
                raise UserError(_("A retired rule version cannot be reactivated. Create a new version."))
            if record.auto_approve and record.step_ids:
                raise UserError(_("An automatic approval rule must not contain human approval steps."))
            if not record.auto_approve and not record.step_ids:
                raise UserError(_("A non-automatic approval rule requires at least one step."))
            record.with_context(onehr_rule_state_action=True).write({"state": "active"})
            self.env["onehr.audit.log"]._log_event(
                action="activate",
                summary=_("Approval rule activated: %s", record.display_name),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={"workflow_event": "rule_activate", "version": record.version},
            )
        return True

    def action_retire(self):
        require_workflow_manager(self.env)
        for record in self.filtered(lambda item: item.state == "active"):
            record.with_context(onehr_rule_state_action=True).write({"state": "retired"})
            self.env["onehr.audit.log"]._log_event(
                action="update",
                summary=_("Approval rule retired: %s", record.display_name),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={"workflow_event": "rule_retire", "version": record.version},
            )
        return True

    def action_create_new_version(self):
        require_workflow_manager(self.env)
        self.ensure_one()
        latest = self.with_context(active_test=False).search(
            [
                ("code", "=ilike", self.code),
                ("company_id", "=", self.company_id.id if self.company_id else False),
            ],
            order="version desc",
            limit=1,
        )
        next_version = (latest.version if latest else self.version) + 1
        new_rule = self.copy(
            {
                "version": next_version,
                "state": "draft",
                "valid_from": fields.Date.context_today(self),
                "valid_to": False,
                "step_ids": [],
            }
        )
        for source_step in self.step_ids.sorted(lambda item: (item.level, item.sequence, item.id)):
            source_step.copy(
                {
                    "rule_id": new_rule.id,
                    "valid_from": fields.Date.context_today(self),
                    "valid_to": False,
                }
            )
        return open_record_action(
            name=_("Approval Rule Version %s", next_version),
            res_model=self._name,
            res_id=new_rule.id,
        )

    def action_open_steps(self):
        self.ensure_one()
        return open_records_action(
            name=_("Approval Steps — %s", self.display_name),
            res_model="onehr.approval.step",
            domain=[("rule_id", "=", self.id)],
            context={"default_rule_id": self.id},
        )

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Approval Requests — %s", self.display_name),
            res_model="onehr.approval.request",
            domain=[("rule_id", "=", self.id)],
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_rule_versions(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only draft approval-rule versions may be deleted."))


class OneHRApprovalStep(models.Model):
    _name = "onehr.approval.step"
    _description = "OneHR Approval Step"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "rule_id, level, sequence, id"

    rule_id = fields.Many2one(
        "onehr.approval.rule",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(related="rule_id.company_id", store=True, index=True)
    level = fields.Integer(
        required=True,
        default=10,
        index=True,
        tracking=True,
        help="Steps sharing the same level execute in parallel.",
    )
    sequence = fields.Integer(default=10, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)

    approver_policy = fields.Selection(
        [
            ("specific_users", "Specific Users"),
            ("onehr_role", "OneHR Role"),
            ("odoo_group", "Odoo Group"),
            ("requester_manager", "Requester Manager Chain"),
            ("source_hook", "Source Integration Hook"),
        ],
        required=True,
        default="specific_users",
        tracking=True,
    )
    specific_user_ids = fields.Many2many(
        "res.users",
        "onehr_approval_step_specific_user_rel",
        "step_id",
        "user_id",
        string="Specific Approvers",
        tracking=True,
    )
    role_id = fields.Many2one("onehr.role", ondelete="restrict", tracking=True)
    group_id = fields.Many2one("res.groups", ondelete="restrict", tracking=True)
    manager_level = fields.Integer(default=1, tracking=True)
    resolver_key = fields.Char(
        tracking=True,
        help=(
            "For Source Integration Hook the source context provides "
            "approver_user_ids_by_key[resolver_key]."
        ),
    )

    decision_mode = fields.Selection(
        [("any", "Any One"), ("quorum", "Quorum"), ("all", "All")],
        required=True,
        default="any",
        tracking=True,
    )
    quorum_count = fields.Integer(default=1, tracking=True)
    block_self_approval = fields.Boolean(default=True, tracking=True)
    allow_delegation = fields.Boolean(default=True, tracking=True)

    sla_hours = fields.Integer(default=24, required=True, tracking=True)
    reminder_hours = fields.Integer(
        default=4,
        tracking=True,
        help="Hours before deadline when the step is considered due soon.",
    )
    escalation_user_ids = fields.Many2many(
        "res.users",
        "onehr_approval_step_escalation_user_rel",
        "step_id",
        "user_id",
        string="Escalation Users",
        tracking=True,
    )
    escalation_role_id = fields.Many2one("onehr.role", ondelete="restrict", tracking=True)
    instructions = fields.Html(translate=True)
    request_count = fields.Integer(compute="_compute_request_count", string="Requests")

    _unique_rule_level_sequence = models.Constraint(
        "UNIQUE(rule_id, level, sequence)",
        "Approval step sequence must be unique inside a rule level.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_workflow_manager(self.env)
        rule_ids = {values.get("rule_id") for values in vals_list if values.get("rule_id")}
        rules = self.env["onehr.approval.rule"].browse(rule_ids)
        if any(rule.state != "draft" for rule in rules):
            raise AccessError(_("Approval steps can only be added to draft rule versions."))
        return super().create(vals_list)

    def write(self, vals):
        require_workflow_manager(self.env)
        if any(record.rule_id.state != "draft" for record in self):
            raise AccessError(
                _("Steps of activated/retired rule versions are immutable. Create a new rule version.")
            )
        return super().write(vals)

    @api.constrains(
        "approver_policy",
        "specific_user_ids",
        "role_id",
        "group_id",
        "manager_level",
        "resolver_key",
        "decision_mode",
        "quorum_count",
        "sla_hours",
        "reminder_hours",
        "level",
    )
    def _check_configuration(self):
        for record in self:
            if record.level < 1:
                raise ValidationError(_("Approval step level must be a positive integer."))
            if record.approver_policy == "specific_users" and not record.specific_user_ids:
                raise ValidationError(_("Specific Users policy requires at least one approver."))
            if record.approver_policy == "onehr_role" and not record.role_id:
                raise ValidationError(_("OneHR Role policy requires a role."))
            if record.approver_policy == "odoo_group" and not record.group_id:
                raise ValidationError(_("Odoo Group policy requires a group."))
            if record.approver_policy == "requester_manager" and record.manager_level < 1:
                raise ValidationError(_("Manager level must be at least 1."))
            if record.approver_policy == "source_hook" and not record.resolver_key:
                raise ValidationError(_("Source Integration Hook policy requires a resolver key."))
            if record.quorum_count < 1:
                raise ValidationError(_("Quorum count must be at least 1."))
            if record.decision_mode == "any" and record.quorum_count != 1:
                raise ValidationError(_("Any One decision mode must use quorum count 1."))
            if record.sla_hours < 0 or record.reminder_hours < 0:
                raise ValidationError(_("SLA/reminder hours cannot be negative."))

    @api.constrains("role_id", "escalation_role_id", "rule_id")
    def _check_role_scope(self):
        for record in self:
            for role in (record.role_id, record.escalation_role_id):
                if (
                    role
                    and role.company_id
                    and record.rule_id.company_id
                    and role.company_id != record.rule_id.company_id
                ):
                    raise ValidationError(
                        _("Approval-step OneHR roles must match the rule company or be global.")
                    )

    @api.constrains("valid_from", "valid_to", "rule_id")
    def _check_validity_inside_rule(self):
        for record in self:
            if record.valid_from < record.rule_id.valid_from:
                raise ValidationError(_("Approval-step validity cannot start before its rule version."))
            if record.rule_id.valid_to and (
                not record.valid_to or record.valid_to > record.rule_id.valid_to
            ):
                raise ValidationError(_("Approval-step validity must be contained by its rule version."))

    def _compute_request_count(self):
        Request = self.env["onehr.approval.request"]
        for record in self:
            record.request_count = Request.search_count([("rule_id", "=", record.rule_id.id)])

    def _filter_internal_company_users(self, users, company):
        approver_group = self.env.ref(APPROVER_GROUP)
        eligible = users.filtered(
            lambda user: (
                user.active
                and not user.share
                and company in user.company_ids
                and approver_group in user.group_ids
            )
        )
        # Normalize possible sudo-derived resolver recordsets back to the caller
        # environment before further request processing. Only IDs cross the narrow
        # authority-resolution boundary.
        return self.env["res.users"].browse(eligible.ids)

    def resolve_base_approvers(self, request, context_values):
        """Resolve base authority identities; delegation is applied afterwards.

        OneHR role assignment enumeration uses narrow routing-only sudo because
        ordinary requesters may not enumerate other users' security assignments.
        The result is still filtered to the request company and never grants source
        business access.
        """
        self.ensure_one()
        company = request.company_id
        as_of_date = fields.Date.to_date(request.requested_at)

        if self.approver_policy == "specific_users":
            users = self.specific_user_ids
        elif self.approver_policy == "onehr_role":
            assignments = self.env["onehr.user.role"].sudo().search(
                [
                    ("role_id", "=", self.role_id.id),
                    ("company_id", "=", company.id),
                    ("state", "=", "active"),
                    ("valid_from", "<=", as_of_date),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", as_of_date),
                ]
            )
            users = assignments.mapped("user_id")
        elif self.approver_policy == "odoo_group":
            users = self.env["res.users"].search(
                [
                    ("active", "=", True),
                    ("share", "=", False),
                    ("group_ids", "in", self.group_id.id),
                    ("company_ids", "in", company.id),
                ]
            )
        elif self.approver_policy == "requester_manager":
            manager_ids = clean_ids(context_values.get("manager_user_ids"))
            selected = manager_ids[self.manager_level - 1] if len(manager_ids) >= self.manager_level else False
            users = self.env["res.users"].browse([selected] if selected else [])
        else:
            mapping = context_values.get("approver_user_ids_by_key") or {}
            users = self.env["res.users"].browse(clean_ids(mapping.get(self.resolver_key)))

        return self._filter_internal_company_users(users, company)

    def resolve_escalation_users(self, request):
        self.ensure_one()
        users = self.escalation_user_ids
        if self.escalation_role_id:
            as_of_date = fields.Date.to_date(request.requested_at)
            assignments = self.env["onehr.user.role"].sudo().search(
                [
                    ("role_id", "=", self.escalation_role_id.id),
                    ("company_id", "=", request.company_id.id),
                    ("state", "=", "active"),
                    ("valid_from", "<=", as_of_date),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", as_of_date),
                ]
            )
            users |= assignments.mapped("user_id")
        return self._filter_internal_company_users(users, request.company_id)

    def action_open_rule(self):
        self.ensure_one()
        return open_record_action(
            name=self.rule_id.display_name,
            res_model="onehr.approval.rule",
            res_id=self.rule_id.id,
        )

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Requests using %s", self.display_name),
            res_model="onehr.approval.request",
            domain=[("rule_id", "=", self.rule_id.id)],
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_rule_steps(self):
        if any(record.rule_id.state != "draft" for record in self):
            raise AccessError(_("Only steps belonging to draft rule versions may be deleted."))
