from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .action_helpers import open_record_action, open_records_action
from .routing_helpers import clean_ids, is_workflow_manager, require_approver, require_workflow_manager


FINAL_STATES = {"approved", "rejected", "cancelled", "executed"}
TODO_ACTIVITY = "mail.mail_activity_data_todo"


class OneHRApprovalRequest(models.Model):
    _name = "onehr.approval.request"
    _description = "OneHR Approval Request"
    _inherit = ["onehr.mixin.audit"]
    _order = "requested_at desc, id desc"

    name = fields.Char(
        required=True,
        readonly=True,
        index=True,
        default=lambda self: _("New Approval"),
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    source_model = fields.Char(required=True, index=True, readonly=True)
    source_res_id = fields.Integer(required=True, index=True, readonly=True)
    source_display_name = fields.Char(readonly=True)
    source_payload_json = fields.Json(readonly=True)
    context_json = fields.Json(readonly=True)

    rule_id = fields.Many2one(
        "onehr.approval.rule", ondelete="restrict", index=True, readonly=True, tracking=True
    )
    rule_code = fields.Char(readonly=True, index=True)
    rule_version = fields.Integer(readonly=True)

    requested_by_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        index=True,
        readonly=True,
    )
    requested_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        index=True,
        readonly=True,
    )
    submitted_at = fields.Datetime(readonly=True, index=True)
    finalized_at = fields.Datetime(readonly=True, index=True)
    executed_at = fields.Datetime(readonly=True)
    final_decision = fields.Selection(
        [("approve", "Approved"), ("reject", "Rejected")],
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("executed", "Executed"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )

    current_level = fields.Integer(readonly=True, index=True)
    current_step_ids = fields.Many2many(
        "onehr.approval.step",
        "onehr_approval_request_current_step_rel",
        "request_id",
        "step_id",
        string="Current Parallel Steps",
        readonly=True,
    )
    current_approver_ids = fields.Many2many(
        "res.users",
        "onehr_approval_request_current_approver_rel",
        "request_id",
        "user_id",
        string="Current Eligible Approvers",
        readonly=True,
    )
    routing_snapshot_json = fields.Json(readonly=True)
    deadline_at = fields.Datetime(readonly=True, index=True)

    decision_ids = fields.One2many(
        "onehr.approval.decision", "request_id", string="Decision Evidence", readonly=True
    )
    escalation_log_ids = fields.One2many(
        "onehr.approval.escalation.log",
        "request_id",
        string="SLA / Escalation Evidence",
        readonly=True,
    )

    request_note = fields.Text(tracking=True)
    decision_comment = fields.Text(
        help="Comment used by the next Approve/Reject action; cleared after decision."
    )

    reassign_from_user_id = fields.Many2one(
        "res.users", string="Reassign From", help="Current base authority to be reassigned."
    )
    reassign_to_user_id = fields.Many2one(
        "res.users", string="Reassign To", help="Replacement approver selected by Workflow Manager."
    )
    reassign_reason = fields.Text()

    supersedes_request_id = fields.Many2one(
        "onehr.approval.request", ondelete="restrict", readonly=True, index=True
    )
    resubmitted_request_ids = fields.One2many(
        "onehr.approval.request",
        "supersedes_request_id",
        string="Resubmissions",
        readonly=True,
    )

    decision_count = fields.Integer(compute="_compute_counts")
    escalation_count = fields.Integer(compute="_compute_counts")
    resubmission_count = fields.Integer(compute="_compute_counts")
    sla_status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("on_time", "On Time"),
            ("due_soon", "Due Soon"),
            ("overdue", "Overdue"),
            ("completed", "Completed"),
        ],
        compute="_compute_sla_metrics",
    )
    aging_bucket = fields.Selection(
        [("lt_24", "< 24h"), ("d1_3", "1-3 days"), ("d4_7", "4-7 days"), ("gt_7", "> 7 days")],
        compute="_compute_sla_metrics",
    )
    cycle_hours = fields.Float(compute="_compute_sla_metrics")

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        manager = is_workflow_manager(self.env)

        for incoming in vals_list:
            values = dict(incoming)
            model_name = values.get("source_model")
            res_id = values.get("source_res_id")
            if not model_name or not res_id:
                raise ValidationError(_("Approval request requires a source model and record ID."))

            try:
                source_model = self.env[model_name]
            except KeyError as exc:
                raise ValidationError(_("Approval source model does not exist: %s", model_name)) from exc

            source = source_model.browse(res_id).exists()
            if not source:
                raise ValidationError(_("Approval source record does not exist."))
            source.check_access("read")

            # The source-side mixin is the normal creation path. A generic model
            # without that contract is allowed only for Workflow Manager tooling.
            if hasattr(source, "_approval_payload"):
                source.check_access("write")
            elif not manager:
                raise AccessError(
                    _(
                        "Generic manual approval requests for models without the OneHR "
                        "approvable contract require Workflow Manager access."
                    )
                )

            source_company = getattr(source, "company_id", False)
            company_id = source_company.id if source_company else values.get("company_id") or self.env.company.id
            if company_id not in self.env.user.company_ids.ids and not manager:
                raise AccessError(_("Approval request company is outside your allowed companies."))

            values.update(
                {
                    "company_id": company_id,
                    "source_display_name": source.display_name,
                    "requested_by_id": (
                        values.get("requested_by_id")
                        if manager and values.get("requested_by_id")
                        else self.env.user.id
                    ),
                    "requested_at": fields.Datetime.now(),
                    "state": "draft",
                    "name": self.env["ir.sequence"].next_by_code("onehr.approval.request")
                    or _("New Approval"),
                }
            )
            prepared.append(values)

        records = super().create(prepared)
        for record in records:
            record.message_subscribe(partner_ids=record.requested_by_id.partner_id.ids)
        return records

    def write(self, vals):
        engine_fields = {
            "company_id",
            "source_model",
            "source_res_id",
            "source_display_name",
            "source_payload_json",
            "context_json",
            "rule_id",
            "rule_code",
            "rule_version",
            "requested_by_id",
            "requested_at",
            "submitted_at",
            "finalized_at",
            "executed_at",
            "final_decision",
            "state",
            "current_level",
            "current_step_ids",
            "current_approver_ids",
            "routing_snapshot_json",
            "deadline_at",
            "supersedes_request_id",
        }
        if engine_fields & set(vals) and not self.env.context.get("onehr_approval_engine"):
            raise AccessError(_("Workflow engine fields may only be changed by controlled approval actions."))

        reassign_fields = {"reassign_from_user_id", "reassign_to_user_id", "reassign_reason"}
        if reassign_fields & set(vals) and not is_workflow_manager(self.env):
            raise AccessError(_("Only Workflow Managers may prepare a manual approval reassignment."))

        if "decision_comment" in vals and not self.env.context.get("onehr_clear_decision_comment"):
            for request in self.filtered(lambda item: item.state == "pending"):
                if self.env.user not in request.current_approver_ids and not is_workflow_manager(self.env):
                    raise AccessError(_("Only a current approver may enter a decision comment."))

        if "request_note" in vals:
            for request in self:
                if request.state in FINAL_STATES:
                    raise AccessError(_("Finalized approval request notes are immutable."))
                if request.requested_by_id != self.env.user and not is_workflow_manager(self.env):
                    raise AccessError(_("Only the requester or Workflow Manager may edit the request note."))

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_requests(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Submitted approval history cannot be deleted."))

    def _compute_counts(self):
        for record in self:
            record.decision_count = len(record.decision_ids)
            record.escalation_count = len(record.escalation_log_ids)
            record.resubmission_count = len(record.resubmitted_request_ids)

    def _compute_sla_metrics(self):
        now = fields.Datetime.now()
        for record in self:
            start = record.submitted_at or record.requested_at
            end = record.finalized_at or now
            delta = end - start if start else timedelta()
            hours = max(delta.total_seconds() / 3600.0, 0.0)
            record.cycle_hours = hours

            if hours < 24:
                record.aging_bucket = "lt_24"
            elif hours < 72:
                record.aging_bucket = "d1_3"
            elif hours < 168:
                record.aging_bucket = "d4_7"
            else:
                record.aging_bucket = "gt_7"

            if record.state in FINAL_STATES:
                record.sla_status = "completed"
            elif not record.deadline_at:
                record.sla_status = "not_started"
            elif record.deadline_at < now:
                record.sla_status = "overdue"
            elif record.deadline_at <= now + timedelta(hours=4):
                record.sla_status = "due_soon"
            else:
                record.sla_status = "on_time"

    def _get_source_record(self, access_mode="read"):
        self.ensure_one()
        try:
            source_model = self.env[self.source_model]
        except KeyError as exc:
            raise UserError(_("The approval source model is no longer available.")) from exc
        source = source_model.browse(self.source_res_id).exists()
        if not source:
            raise UserError(_("The approval source record is no longer available."))
        source.check_access(access_mode)
        return source

    def _source_contract_values(self):
        self.ensure_one()
        source = self._get_source_record("read")
        if hasattr(source, "_approval_payload") and hasattr(source, "_approval_rule_context"):
            source.check_access("write")
            payload = source._approval_payload()
            context_values = source._approval_rule_context()
            if not isinstance(payload, dict) or not isinstance(context_values, dict):
                raise ValidationError(
                    _("Source approval contract must return dictionaries for payload and context.")
                )
            return source, payload, context_values

        if not is_workflow_manager(self.env):
            raise AccessError(_("Source model does not implement the OneHR approvable contract."))
        return source, self.source_payload_json or {}, self.context_json or {}

    def _normalise_context(self, context_values):
        self.ensure_one()
        values = dict(context_values or {})
        values["company_id"] = self.company_id.id
        values.setdefault("document_type", self.source_model)
        values.setdefault("branch_scope_key", False)
        values.setdefault("amount", 0.0)
        values.setdefault("currency_id", self.company_id.currency_id.id)
        values.setdefault("risk_level", "normal")
        values.setdefault("extra", {})

        if not values.get("requester_role_ids"):
            as_of_date = fields.Date.to_date(self.requested_at)
            # Narrow routing metadata read: ordinary users must not enumerate all
            # security assignments, but the engine must resolve their own role context.
            assignments = self.env["onehr.user.role"].sudo().search(
                [
                    ("user_id", "=", self.requested_by_id.id),
                    ("company_id", "=", self.company_id.id),
                    ("state", "=", "active"),
                    ("valid_from", "<=", as_of_date),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", as_of_date),
                ]
            )
            values["requester_role_ids"] = assignments.mapped("role_id").ids

        values["requester_role_ids"] = clean_ids(values.get("requester_role_ids"))
        values["manager_user_ids"] = clean_ids(values.get("manager_user_ids"))
        mapping = values.get("approver_user_ids_by_key") or {}
        if not isinstance(mapping, dict):
            raise ValidationError(_("approver_user_ids_by_key must be a structured mapping."))
        values["approver_user_ids_by_key"] = {
            str(key): clean_ids(user_ids) for key, user_ids in mapping.items()
        }
        if not isinstance(values.get("extra"), dict):
            raise ValidationError(_("Approval extra context must be a structured JSON object."))
        return values

    def action_submit(self):
        for request in self:
            if request.state != "draft":
                raise UserError(_("Only a draft approval request may be submitted."))
            if request.requested_by_id != self.env.user and not is_workflow_manager(self.env):
                raise AccessError(_("Only the requester or Workflow Manager may submit this request."))

            source, payload, context_values = request._source_contract_values()
            context_values = request._normalise_context(context_values)
            rule = self.env["onehr.approval.rule"].resolve_for_context(
                request.source_model,
                context_values,
                fields.Date.to_date(request.requested_at),
            )

            request.with_context(onehr_approval_engine=True).write(
                {
                    "source_display_name": source.display_name,
                    "source_payload_json": payload,
                    "context_json": context_values,
                    "rule_id": rule.id,
                    "rule_code": rule.code,
                    "rule_version": rule.version,
                    "state": "submitted",
                    "submitted_at": fields.Datetime.now(),
                }
            )
            request.message_post(
                body=_(
                    "Approval request submitted under rule %(rule)s v%(version)s.",
                    rule=rule.code,
                    version=rule.version,
                )
            )

            if rule.auto_approve:
                # System decision evidence is created under narrow sudo; the rule
                # itself has already been resolved and validated in normal context.
                self.env["onehr.approval.decision"].sudo().with_context(
                    onehr_approval_engine=True
                ).create(
                    {
                        "request_id": request.id,
                        "decision": "approve",
                        "decision_source": "automatic",
                        "rationale": _("Automatically approved by governed matrix rule."),
                    }
                )
                request._finalize("approve")
                continue

            request._validate_distinct_eyes_capacity()
            request._enter_first_level()
        return True

    def _effective_steps(self):
        self.ensure_one()
        as_of_date = fields.Date.to_date(self.requested_at)
        return self.rule_id.step_ids.filtered(lambda step: step.is_effective_on(as_of_date))

    def _base_users_for_step(self, step):
        self.ensure_one()
        users = step.resolve_base_approvers(self, self.context_json or {})
        if step.block_self_approval:
            users -= self.requested_by_id
        return users

    def _validate_distinct_eyes_capacity(self):
        self.ensure_one()
        if not self.rule_id.minimum_distinct_approvers:
            return True
        possible_authorities = self.env["res.users"]
        for step in self._effective_steps():
            possible_authorities |= self._base_users_for_step(step)
        if len(possible_authorities) < self.rule_id.minimum_distinct_approvers:
            raise UserError(
                _(
                    "Approval route can provide only %(available)s distinct authority identities, "
                    "but the rule requires %(required)s.",
                    available=len(possible_authorities),
                    required=self.rule_id.minimum_distinct_approvers,
                )
            )
        return True

    def _enter_first_level(self):
        self.ensure_one()
        steps = self._effective_steps()
        if not steps:
            raise UserError(_("The matched approval rule has no effective steps."))
        return self._enter_level(min(steps.mapped("level")))

    def _enter_level(self, level):
        self.ensure_one()
        level_steps = self._effective_steps().filtered(lambda step: step.level == level)
        if not level_steps:
            raise UserError(_("No effective approval steps exist for level %s.", level))

        snapshot = {"level": level, "steps": {}}
        all_eligible = self.env["res.users"]
        deadlines = []
        now = fields.Datetime.now()

        for step in level_steps.sorted(lambda item: (item.sequence, item.id)):
            base_users = self._base_users_for_step(step)
            if not base_users:
                raise UserError(_("Approval step %s resolved no eligible approver.", step.display_name))
            if step.decision_mode == "quorum" and step.quorum_count > len(base_users):
                raise UserError(
                    _(
                        "Approval step %(step)s requires quorum %(quorum)s but only %(count)s "
                        "base approvers are available.",
                        step=step.display_name,
                        quorum=step.quorum_count,
                        count=len(base_users),
                    )
                )

            delegation_map = self.env["onehr.approval.delegate"].effective_delegate_map(
                delegator_ids=base_users.ids,
                step=step,
                as_of_date=fields.Date.to_date(self.requested_at),
                company=self.company_id,
            )
            eligible = base_users | self.env["res.users"].browse(list(delegation_map))
            deadline = now + timedelta(hours=step.sla_hours)
            deadlines.append(deadline)

            snapshot["steps"][str(step.id)] = {
                "base_user_ids": base_users.ids,
                "eligible_user_ids": eligible.ids,
                "delegation_map": {
                    str(delegate_id): delegator_id
                    for delegate_id, delegator_id in delegation_map.items()
                },
                "reassign_map": {},
                "escalation_user_ids": [],
                "deadline_at": fields.Datetime.to_string(deadline),
            }
            all_eligible |= eligible

        self.with_context(onehr_approval_engine=True).write(
            {
                "state": "pending",
                "current_level": level,
                "current_step_ids": [Command.set(level_steps.ids)],
                "current_approver_ids": [Command.set(all_eligible.ids)],
                "routing_snapshot_json": snapshot,
                "deadline_at": min(deadlines) if deadlines else False,
            }
        )
        self.message_subscribe(partner_ids=all_eligible.mapped("partner_id").ids)
        self._schedule_current_activities()
        self.message_post(
            body=_(
                "Approval routing entered level %(level)s with %(count)s parallel step(s).",
                level=level,
                count=len(level_steps),
            )
        )
        return True

    def _schedule_current_activities(self):
        self.ensure_one()
        if self.state != "pending":
            return True
        deadline = fields.Date.to_date(self.deadline_at) if self.deadline_at else fields.Date.context_today(self)
        summary = _("Approval required: %s", self.name)
        for user in self.current_approver_ids:
            existing = self.activity_search(
                [TODO_ACTIVITY],
                user_id=user.id,
                additional_domain=[("summary", "=", summary)],
            )
            if not existing:
                self.activity_schedule(
                    TODO_ACTIVITY,
                    user_id=user.id,
                    date_deadline=deadline,
                    summary=summary,
                    note=_("Review the current OneHR approval level and record your decision."),
                )
        return True

    def _snapshot_step(self, step):
        self.ensure_one()
        return (self.routing_snapshot_json or {}).get("steps", {}).get(str(step.id), {})

    def _decision_identity_for_user(self, step, user):
        self.ensure_one()
        snapshot = self._snapshot_step(step)
        eligible_ids = clean_ids(snapshot.get("eligible_user_ids"))
        if user.id not in eligible_ids:
            return False

        base_ids = clean_ids(snapshot.get("base_user_ids"))
        if user.id in base_ids:
            return {
                "authority_user_id": user.id,
                "decision_source": "human",
                "delegated_from_user_id": False,
                "delegation_id": False,
            }

        delegation_map = {
            int(delegate_id): int(delegator_id)
            for delegate_id, delegator_id in (snapshot.get("delegation_map") or {}).items()
        }
        if user.id in delegation_map:
            delegator_id = delegation_map[user.id]
            delegation = self.env["onehr.approval.delegate"].sudo().search(
                [
                    ("delegator_user_id", "=", delegator_id),
                    ("delegate_user_id", "=", user.id),
                    ("company_id", "=", self.company_id.id),
                    ("state", "=", "active"),
                ],
                limit=1,
            )
            return {
                "authority_user_id": delegator_id,
                "decision_source": "delegated",
                "delegated_from_user_id": delegator_id,
                "delegation_id": delegation.id,
            }

        reassign_map = {
            int(target_id): int(source_id)
            for target_id, source_id in (snapshot.get("reassign_map") or {}).items()
        }
        if user.id in reassign_map:
            return {
                "authority_user_id": reassign_map[user.id],
                "decision_source": "reassigned",
                "delegated_from_user_id": reassign_map[user.id],
                "delegation_id": False,
            }

        if user.id in clean_ids(snapshot.get("escalation_user_ids")):
            return {
                "authority_user_id": user.id,
                "decision_source": "escalated",
                "delegated_from_user_id": False,
                "delegation_id": False,
            }
        return False

    def _effective_decisions(self, step=None):
        self.ensure_one()
        decisions = self.decision_ids
        if step:
            decisions = decisions.filtered(lambda item: item.step_id == step)
        superseded_ids = set(decisions.filtered("supersedes_id").mapped("supersedes_id").ids)
        return decisions.filtered(lambda item: item.id not in superseded_ids)

    def _step_is_approved(self, step):
        self.ensure_one()
        decisions = self._effective_decisions(step)
        if decisions.filtered(lambda item: item.decision == "reject"):
            return False
        approved_ids = set(
            decisions.filtered(
                lambda item: item.decision == "approve" and item.authority_user_id
            ).mapped("authority_user_id").ids
        )
        base_ids = set(clean_ids(self._snapshot_step(step).get("base_user_ids")))
        if step.decision_mode == "any":
            return bool(approved_ids)
        if step.decision_mode == "quorum":
            return len(approved_ids) >= step.quorum_count
        return base_ids.issubset(approved_ids)

    def _step_has_reject(self, step):
        self.ensure_one()
        return bool(self._effective_decisions(step).filtered(lambda item: item.decision == "reject"))

    def _choose_current_step_for_user(self, user):
        self.ensure_one()
        for step in self.current_step_ids.sorted(lambda item: (item.sequence, item.id)):
            identity = self._decision_identity_for_user(step, user)
            if not identity:
                continue
            authority_id = identity["authority_user_id"]
            if not self._effective_decisions(step).filtered(
                lambda item: item.authority_user_id.id == authority_id
            ):
                return step
        return self.env["onehr.approval.step"]

    def action_approve(self):
        require_approver(self.env)
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Only pending approval requests can be approved."))
        step = self._choose_current_step_for_user(self.env.user)
        if not step:
            raise AccessError(_("You have no remaining eligible approval step on this request."))

        comment = self.decision_comment or False
        self.env["onehr.approval.decision"].with_context(onehr_approval_engine=True).create(
            {
                "request_id": self.id,
                "step_id": step.id,
                "decision": "approve",
                "rationale": comment,
            }
        )
        self.activity_feedback(
            [TODO_ACTIVITY],
            user_id=self.env.user.id,
            feedback=_("Approval decision recorded."),
        )
        self.with_context(onehr_clear_decision_comment=True).write({"decision_comment": False})
        self._evaluate_current_level()
        return True

    def action_reject(self):
        require_approver(self.env)
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Only pending approval requests can be rejected."))
        if not self.decision_comment:
            raise UserError(_("A rejection rationale is mandatory."))
        step = self._choose_current_step_for_user(self.env.user)
        if not step:
            raise AccessError(_("You have no remaining eligible approval step on this request."))

        comment = self.decision_comment
        self.env["onehr.approval.decision"].with_context(onehr_approval_engine=True).create(
            {
                "request_id": self.id,
                "step_id": step.id,
                "decision": "reject",
                "rationale": comment,
            }
        )
        self.activity_feedback(
            [TODO_ACTIVITY],
            user_id=self.env.user.id,
            feedback=_("Rejection decision recorded."),
        )
        self.with_context(onehr_clear_decision_comment=True).write({"decision_comment": False})
        self._evaluate_current_level()
        return True

    def _evaluate_current_level(self):
        self.ensure_one()
        if self.state != "pending":
            return True
        if any(self._step_has_reject(step) for step in self.current_step_ids):
            return self._finalize("reject")
        if not all(self._step_is_approved(step) for step in self.current_step_ids):
            return True

        future_levels = sorted(
            {
                step.level
                for step in self._effective_steps()
                if step.level > self.current_level
            }
        )
        if future_levels:
            # Close stale activities from a completed current level before the
            # next level is scheduled.
            self.activity_unlink([TODO_ACTIVITY])
            return self._enter_level(future_levels[0])

        distinct_authorities = set(
            self._effective_decisions()
            .filtered(lambda item: item.decision == "approve" and item.authority_user_id)
            .mapped("authority_user_id")
            .ids
        )
        if len(distinct_authorities) < self.rule_id.minimum_distinct_approvers:
            raise UserError(
                _(
                    "Final approval requires %(required)s distinct authority identities; "
                    "only %(actual)s have approved.",
                    required=self.rule_id.minimum_distinct_approvers,
                    actual=len(distinct_authorities),
                )
            )
        return self._finalize("approve")

    def _notify_source_finalization(self, decision):
        self.ensure_one()
        source = self._get_source_record("read")
        if hasattr(source, "_on_approval_finalized"):
            source._on_approval_finalized(decision, self)
        return True

    def _finalize(self, decision):
        self.ensure_one()
        if decision not in {"approve", "reject"}:
            raise ValidationError(_("Final approval decision must be approve or reject."))

        # Source hook runs in the same transaction. Any source-domain failure rolls
        # back finalization and evidence rather than leaving a split-brain state.
        self._notify_source_finalization(decision)
        target_state = "approved" if decision == "approve" else "rejected"
        self.with_context(onehr_approval_engine=True).write(
            {
                "state": target_state,
                "final_decision": decision,
                "finalized_at": fields.Datetime.now(),
                "current_step_ids": [Command.clear()],
                "current_approver_ids": [Command.clear()],
                "deadline_at": False,
            }
        )
        self.activity_unlink([TODO_ACTIVITY])
        self.message_post(body=_("Approval request finalized as %s.", target_state))
        self.env["onehr.audit.log"]._log_event(
            action="other",
            summary=_("Approval request finalized: %s", self.display_name),
            severity="high",
            record=self,
            company=self.company_id,
            metadata={
                "workflow_event": "approval_request_finalized",
                "final_decision": decision,
                "rule_code": self.rule_code,
                "rule_version": self.rule_version,
            },
        )
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.state in {"approved", "executed"}:
            raise UserError(_("Approved/executed approval evidence cannot be cancelled."))
        if self.state == "cancelled":
            return True
        if self.requested_by_id != self.env.user and not is_workflow_manager(self.env):
            raise AccessError(_("Only the requester or Workflow Manager may cancel this request."))

        source = self._get_source_record("read")
        if hasattr(source, "_approval_cancel_guard") and not source._approval_cancel_guard(self):
            raise UserError(_("Source transaction does not allow this approval request to be cancelled."))

        self.with_context(onehr_approval_engine=True).write(
            {
                "state": "cancelled",
                "current_step_ids": [Command.clear()],
                "current_approver_ids": [Command.clear()],
                "deadline_at": False,
                "finalized_at": fields.Datetime.now(),
            }
        )
        self.activity_unlink([TODO_ACTIVITY])
        self.message_post(body=_("Approval request cancelled."))
        return True

    def action_resubmit(self):
        self.ensure_one()
        if self.state not in {"rejected", "cancelled"}:
            raise UserError(_("Only rejected or cancelled requests may be resubmitted."))
        if self.requested_by_id != self.env.user and not is_workflow_manager(self.env):
            raise AccessError(_("Only the requester or Workflow Manager may resubmit."))

        new_request = self.create(
            {
                "company_id": self.company_id.id,
                "source_model": self.source_model,
                "source_res_id": self.source_res_id,
                "source_payload_json": self.source_payload_json,
                "context_json": self.context_json,
                "requested_by_id": self.requested_by_id.id,
                "request_note": self.request_note,
                "supersedes_request_id": self.id,
            }
        )
        new_request.action_submit()
        return open_record_action(
            name=new_request.display_name,
            res_model=self._name,
            res_id=new_request.id,
        )

    def action_send_reminder(self):
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Reminder is available only for pending approvals."))
        if (
            self.env.user not in self.current_approver_ids
            and self.requested_by_id != self.env.user
            and not is_workflow_manager(self.env)
        ):
            raise AccessError(_("You are not allowed to send a reminder for this request."))

        self._schedule_current_activities()
        for step in self.current_step_ids:
            self.env["onehr.approval.escalation.log"]._record_event(
                request_id=self.id,
                step_id=step.id,
                event_type="reminder",
                due_at=fields.Datetime.to_datetime(self._snapshot_step(step).get("deadline_at")),
                reason=_("Manual approval reminder."),
                automated=False,
                payload_json={"current_approver_ids": self.current_approver_ids.ids},
            )
        self.message_post(body=_("Approval reminder sent/scheduled for current approvers."))
        return True

    def action_reassign_current_authority(self):
        require_workflow_manager(self.env)
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Manual reassignment is available only on a pending request."))
        if not self.reassign_from_user_id or not self.reassign_to_user_id:
            raise UserError(_("Select both Reassign From and Reassign To users."))
        if not self.reassign_reason:
            raise UserError(_("A manual reassignment reason is mandatory."))
        if self.reassign_from_user_id == self.reassign_to_user_id:
            raise UserError(_("Reassignment source and target must be different users."))
        if self.company_id not in self.reassign_to_user_id.company_ids:
            raise UserError(_("Replacement approver is outside the request company."))
        approver_group = self.env.ref("onehr_workflow_approval.group_onehr_approver")
        if approver_group not in self.reassign_to_user_id.group_ids:
            raise UserError(_("Replacement user must hold the OneHR Approver application group."))

        snapshot = dict(self.routing_snapshot_json or {})
        steps_data = dict(snapshot.get("steps") or {})
        affected = False

        for step in self.current_step_ids:
            data = dict(steps_data.get(str(step.id)) or {})
            base_ids = clean_ids(data.get("base_user_ids"))
            if self.reassign_from_user_id.id not in base_ids:
                continue
            if self._effective_decisions(step).filtered(
                lambda item: item.authority_user_id == self.reassign_from_user_id
            ):
                raise UserError(_("Cannot reassign an authority that already has an effective decision."))

            eligible_ids = [
                user_id
                for user_id in clean_ids(data.get("eligible_user_ids"))
                if user_id != self.reassign_from_user_id.id
            ]
            if self.reassign_to_user_id.id not in eligible_ids:
                eligible_ids.append(self.reassign_to_user_id.id)
            reassign_map = dict(data.get("reassign_map") or {})
            reassign_map[str(self.reassign_to_user_id.id)] = self.reassign_from_user_id.id
            data["eligible_user_ids"] = eligible_ids
            data["reassign_map"] = reassign_map
            steps_data[str(step.id)] = data
            affected = True

            self.env["onehr.approval.escalation.log"]._record_event(
                request_id=self.id,
                step_id=step.id,
                event_type="reassign",
                from_user_id=self.reassign_from_user_id.id,
                to_user_id=self.reassign_to_user_id.id,
                due_at=fields.Datetime.to_datetime(data.get("deadline_at")),
                reason=self.reassign_reason,
                automated=False,
                payload_json={"authority_user_id": self.reassign_from_user_id.id},
            )

        if not affected:
            raise UserError(_("Selected Reassign From user is not a base authority in the current level."))

        snapshot["steps"] = steps_data
        all_eligible_ids = []
        for data in steps_data.values():
            all_eligible_ids.extend(clean_ids(data.get("eligible_user_ids")))
        all_eligible_ids = list(dict.fromkeys(all_eligible_ids))

        self.activity_unlink([TODO_ACTIVITY], user_id=self.reassign_from_user_id.id)
        self.with_context(onehr_approval_engine=True).write(
            {
                "routing_snapshot_json": snapshot,
                "current_approver_ids": [Command.set(all_eligible_ids)],
            }
        )
        self.message_subscribe(partner_ids=self.reassign_to_user_id.partner_id.ids)
        self._schedule_current_activities()
        self.message_post(
            body=_(
                "Approval authority manually reassigned from %(source)s to %(target)s.",
                source=self.reassign_from_user_id.display_name,
                target=self.reassign_to_user_id.display_name,
            )
        )
        self.write(
            {
                "reassign_from_user_id": False,
                "reassign_to_user_id": False,
                "reassign_reason": False,
            }
        )
        return True

    def _escalate_step_if_due(self, step, now):
        self.ensure_one()
        data = dict(self._snapshot_step(step))
        deadline = fields.Datetime.to_datetime(data.get("deadline_at"))
        if (
            not deadline
            or deadline > now
            or self._step_is_approved(step)
            or self._step_has_reject(step)
        ):
            return False

        existing = self.escalation_log_ids.filtered(
            lambda log: log.step_id == step and log.event_type in {"overdue", "escalation"}
        )
        if existing:
            return False

        escalation_users = step.resolve_escalation_users(self)
        if escalation_users:
            eligible_ids = clean_ids(data.get("eligible_user_ids"))
            for user_id in escalation_users.ids:
                if user_id not in eligible_ids:
                    eligible_ids.append(user_id)
            data["eligible_user_ids"] = eligible_ids
            data["escalation_user_ids"] = escalation_users.ids

            snapshot = dict(self.routing_snapshot_json or {})
            steps_data = dict(snapshot.get("steps") or {})
            steps_data[str(step.id)] = data
            snapshot["steps"] = steps_data
            all_ids = []
            for step_data in steps_data.values():
                all_ids.extend(clean_ids(step_data.get("eligible_user_ids")))
            all_ids = list(dict.fromkeys(all_ids))

            self.with_context(onehr_approval_engine=True).write(
                {
                    "routing_snapshot_json": snapshot,
                    "current_approver_ids": [Command.set(all_ids)],
                }
            )
            self.message_subscribe(partner_ids=escalation_users.mapped("partner_id").ids)
            for user in escalation_users:
                self.env["onehr.approval.escalation.log"]._record_event(
                    request_id=self.id,
                    step_id=step.id,
                    event_type="escalation",
                    to_user_id=user.id,
                    due_at=deadline,
                    reason=_("SLA deadline exceeded; escalation authority added."),
                    automated=True,
                    payload_json={"level": self.current_level},
                )
        else:
            self.env["onehr.approval.escalation.log"]._record_event(
                request_id=self.id,
                step_id=step.id,
                event_type="overdue",
                due_at=deadline,
                reason=_("SLA deadline exceeded; no configured escalation target."),
                automated=True,
                payload_json={"level": self.current_level},
            )

        self._schedule_current_activities()
        return True

    @api.model
    def _cron_process_sla(self):
        now = fields.Datetime.now()
        requests = self.search(
            [
                ("state", "=", "pending"),
                ("deadline_at", "!=", False),
                ("deadline_at", "<=", now),
            ]
        )
        for request in requests:
            for step in request.current_step_ids:
                request._escalate_step_if_due(step, now)
        return True

    def _mark_executed_from_source(self, source_record):
        """Private source callback; never a public approval-engine execute button."""
        self.ensure_one()
        source_record.ensure_one()
        if source_record._name != self.source_model or source_record.id != self.source_res_id:
            raise AccessError(_("Execution marker source does not match the approval request."))
        if self.state != "approved":
            raise UserError(_("Only an approved request can be marked executed."))
        self.with_context(onehr_approval_engine=True).write(
            {"state": "executed", "executed_at": fields.Datetime.now()}
        )
        self.message_post(body=_("Source transaction reported successful execution."))
        return True

    def action_open_source(self):
        self.ensure_one()
        source = self._get_source_record("read")
        return open_record_action(
            name=source.display_name, res_model=source._name, res_id=source.id
        )

    def action_open_decisions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Decision Evidence — %s", self.display_name),
            res_model="onehr.approval.decision",
            domain=[("request_id", "=", self.id)],
        )

    def action_open_escalations(self):
        self.ensure_one()
        return open_records_action(
            name=_("SLA / Escalation Evidence — %s", self.display_name),
            res_model="onehr.approval.escalation.log",
            domain=[("request_id", "=", self.id)],
        )

    def action_open_resubmissions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Resubmissions — %s", self.display_name),
            res_model="onehr.approval.request",
            domain=[("supersedes_request_id", "=", self.id)],
        )
