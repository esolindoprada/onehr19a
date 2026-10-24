
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import (
    require_assignment_manager,
    require_assignment_proposer,
)


class OneHRAssignmentChangeRequest(models.Model):
    """ED3 governed batch movement transaction.

    The Registry already owns persistent request/line models, so mass movement is
    implemented here rather than by inventing an unregistered transient wizard.
    """

    _name = "onehr.assignment.change.request"
    _description = "OneHR Assignment Change Request"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "effective_date desc, id desc"

    _STATE_CONTEXT = "onehr_assignment_change_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_assignment_change_evidence_controlled"

    name = fields.Char(
        string="Movement Request No.", required=True, readonly=True, copy=False,
        default=lambda self: _("New"), index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True, tracking=True,
    )
    movement_type = fields.Selection(
        [
            ("transfer", "Transfer"),
            ("rotation", "Rotation"),
            ("promotion", "Promotion"),
            ("demotion", "Demotion"),
            ("secondment", "Secondment"),
            ("temporary", "Temporary Assignment"),
            ("reorganization", "Reorganization"),
            ("return", "Return"),
            ("correction", "Governed Correction"),
        ],
        required=True, default="transfer", index=True, tracking=True,
    )
    effective_date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    reason = fields.Text(required=True, tracking=True)
    requested_by_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        readonly=True, ondelete="restrict", index=True,
    )
    submitted_at = fields.Datetime(readonly=True, copy=False)
    approved_at = fields.Datetime(readonly=True, copy=False)
    executed_at = fields.Datetime(readonly=True, copy=False)
    executed_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("proposed", "Proposed"),
            ("approved", "Approved"),
            ("executed", "Executed"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        required=True, default="draft", index=True, tracking=True,
    )
    line_ids = fields.One2many(
        "onehr.assignment.change.line", "request_id", string="Movement Lines", copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count")
    generated_assignment_count = fields.Integer(compute="_compute_generated_assignment_count")

    _change_request_number_unique = models.Constraint(
        "unique(name)", "Movement Request Number must be unique."
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_assignment_proposer(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Movement Requests must be created in Draft."))
            for evidence_field in ("submitted_at", "approved_at", "executed_at", "executed_by_id"):
                if evidence_field in values and not self.env.context.get(self._EVIDENCE_CONTEXT):
                    raise AccessError(_("Movement execution evidence can be set only by governed actions."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.assignment.change.request") or _("New")
            values["requested_by_id"] = self.env.user.id
            prepared.append(values)
        return super().create(prepared)

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Movement Request state can change only through governed actions."))
        evidence_fields = {"requested_by_id", "submitted_at", "approved_at", "executed_at", "executed_by_id"}
        if evidence_fields & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Movement Request evidence can change only through governed actions."))
        editable = {"company_id", "movement_type", "effective_date", "reason", "line_ids"}
        if editable & set(values) and any(record.state not in {"draft", "rejected"} for record in self):
            raise AccessError(_("Approved/submitted movement requests are frozen."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_request(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only Draft movement requests can be deleted."))

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    def _compute_generated_assignment_count(self):
        Assignment = self.env["onehr.assignment"]
        for record in self:
            record.generated_assignment_count = Assignment.search_count([("change_request_id", "=", record.id)])

    def _validate_request(self):
        for request in self:
            if not request.line_ids:
                raise ValidationError(_("A movement request must contain at least one line."))
            if len(request.line_ids.mapped("source_assignment_id")) != len(request.line_ids):
                raise ValidationError(_("Each source assignment may appear only once in a movement request."))
            request.line_ids._validate_line_integrity()
        return True

    def _approval_payload(self):
        self.ensure_one()
        return {
            "movement_request": self.name,
            "movement_type": self.movement_type,
            "effective_date": fields.Date.to_string(self.effective_date),
            "reason": self.reason,
            "line_count": len(self.line_ids),
            "employees": self.line_ids.mapped("employee_name"),
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = list(set(self.line_ids.mapped("source_assignment_id.manager_user_id").ids))
        values.update({
            "document_type": "onehr_assignment_change",
            "manager_user_ids": manager_ids,
            "extra": {
                "movement_type": self.movement_type,
                "effective_date": fields.Date.to_string(self.effective_date),
                "line_count": len(self.line_ids),
                "source_department_ids": list(set(self.line_ids.mapped("source_assignment_id.department_id").ids)),
                "target_position_ids": list(set(self.line_ids.mapped("target_position_id").ids)),
            },
        })
        return values

    def action_submit_for_approval(self):
        self.ensure_one()
        require_assignment_proposer(self)
        if self.state not in {"draft", "rejected"}:
            raise UserError(_("Only Draft or Rejected movement requests can be proposed."))
        if self.requested_by_id != self.env.user and not self.env.user.has_group(
            "onehr_assignment.group_onehr_assignment_officer"
        ):
            raise AccessError(_("A proposer may submit only their own movement request."))
        self._validate_request()
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "proposed", "submitted_at": fields.Datetime.now()
        })
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "proposed":
            return True
        vals = {"state": "approved" if decision == "approve" else "rejected"}
        if decision == "approve":
            vals["approved_at"] = fields.Datetime.now()
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write(vals)
        return True

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        if self.state == "executed":
            raise UserError(_("Executed movement approval cannot be cancelled."))
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        require_assignment_proposer(self)
        if self.state != "rejected":
            raise UserError(_("Only a Rejected movement request can be reset to Draft."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "draft"})
        return True

    def action_cancel(self):
        self.ensure_one()
        require_assignment_proposer(self)
        if self.state not in {"draft", "rejected"}:
            raise UserError(_("Only Draft or Rejected movement requests can be cancelled."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "cancelled"})
        return True

    def action_execute(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "approved":
            raise UserError(_("Only an Approved movement request can be executed."))
        self._validate_request()
        for line in self.line_ids.sorted(lambda row: (row.sequence, row.id)):
            line._execute_line()
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "executed",
            "executed_at": fields.Datetime.now(),
            "executed_by_id": self.env.user.id,
        })
        approval = self.env["onehr.approval.request"].search(
            [("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")],
            order="finalized_at desc, id desc", limit=1,
        )
        if approval:
            self.onehr_mark_approval_executed(approval)
        return self.action_open_generated_assignments()

    def action_schedule_line_reviews(self):
        self.ensure_one()
        require_assignment_proposer(self)
        manager_users = self.line_ids.mapped("source_assignment_id.manager_user_id")
        if not manager_users:
            manager_users = self.env.user
        for user in manager_users:
            self.activity_schedule(
                "mail.mail_activity_data_todo", user_id=user.id,
                summary=_("Review movement request %s", self.name),
                note=_("Review source/target placement, FTE, effective date and reporting-line impact."),
            )
        return True

    def action_open_generated_assignments(self):
        self.ensure_one()
        return open_records_action(
            name=_("Generated Assignments — %s", self.name),
            res_model="onehr.assignment",
            domain=[("change_request_id", "=", self.id)],
        )


class OneHRAssignmentChangeLine(models.Model):
    _name = "onehr.assignment.change.line"
    _description = "OneHR Assignment Change Line"
    _inherit = ["onehr.mixin.audit"]
    _order = "request_id, sequence, id"

    _INTERNAL_CONTEXT = "onehr_assignment_change_line_controlled"

    request_id = fields.Many2one(
        "onehr.assignment.change.request", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(related="request_id.company_id", store=True, readonly=True, index=True)
    sequence = fields.Integer(default=10)
    source_assignment_id = fields.Many2one(
        "onehr.assignment", required=True, ondelete="restrict", index=True, tracking=True,
        domain="[('state', '=', 'active'), ('company_id', '=', company_id)]",
    )
    employee_id = fields.Many2one(
        related="source_assignment_id.employee_id", store=True, readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    employee_name = fields.Char(related="source_assignment_id.employee_name", store=True, readonly=True, index=True)
    source_position_id = fields.Many2one(related="source_assignment_id.position_id", store=True, readonly=True)
    source_manager_name = fields.Char(related="source_assignment_id.manager_name", store=True, readonly=True)
    target_position_id = fields.Many2one(
        "onehr.position", required=True, ondelete="restrict", check_company=True, index=True, tracking=True,
    )
    target_manager_id = fields.Many2one(
        "hr.employee", ondelete="restrict", check_company=True, tracking=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
        help="Leave empty to retain the current direct manager.",
    )
    target_assignment_type = fields.Selection(
        [("primary", "Primary"), ("secondary", "Secondary")], tracking=True,
        help="Leave empty to retain the source assignment type.",
    )
    target_fte = fields.Float(
        string="Target FTE", tracking=True,
        help="Leave zero to retain the source assignment FTE.",
    )
    target_effective_to = fields.Date(tracking=True)
    copy_cost_allocations = fields.Boolean(default=True, tracking=True)
    note = fields.Char(tracking=True)
    generated_assignment_id = fields.Many2one(
        "onehr.assignment", ondelete="restrict", copy=False, readonly=True, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_assignment_proposer(self)
        if not self.env.context.get(self._INTERNAL_CONTEXT) and any(
            incoming.get("generated_assignment_id") for incoming in vals_list
        ):
            raise AccessError(_("Generated Assignment evidence is set only by movement execution."))
        records = super().create(vals_list)
        records._validate_line_integrity()
        return records

    def write(self, values):
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            require_assignment_proposer(self)
            if "generated_assignment_id" in values:
                raise AccessError(_("Generated Assignment evidence is set only by movement execution."))
            if any(line.request_id.state not in {"draft", "rejected"} for line in self):
                raise AccessError(_("Movement lines are frozen after request submission."))
            if any(line.generated_assignment_id for line in self):
                raise AccessError(_("Executed movement evidence cannot be rewritten."))
        result = super().write(values)
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            self._validate_line_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_draft_lines_only(self):
        require_assignment_proposer(self)
        if any(line.request_id.state not in {"draft", "rejected"} for line in self):
            raise AccessError(_("Movement lines cannot be deleted after submission."))

    @api.constrains(
        "request_id", "source_assignment_id", "target_position_id", "target_manager_id",
        "target_assignment_type", "target_fte", "target_effective_to",
    )
    def _check_line_integrity(self):
        self._validate_line_integrity()

    def _validate_line_integrity(self):
        for line in self:
            source = line.source_assignment_id
            request = line.request_id
            if source.company_id != request.company_id:
                raise ValidationError(_("Source Assignment must belong to the movement-request company."))
            if line.target_position_id.company_id != request.company_id:
                raise ValidationError(_("Target Position must belong to the movement-request company."))
            if request.effective_date <= source.effective_from:
                raise ValidationError(_("Movement Effective Date must be after the source Assignment start date."))
            if source.effective_to and request.effective_date > source.effective_to:
                raise ValidationError(_("Movement Effective Date must fall within the source Assignment validity."))
            if line.target_effective_to and line.target_effective_to < request.effective_date:
                raise ValidationError(_("Target Assignment End Date cannot precede movement Effective Date."))
            target_fte = line.target_fte or source.fte
            if target_fte <= 0 or target_fte > 1.0:
                raise ValidationError(_("Target FTE must be greater than zero and not exceed 1.0."))
            target_manager = line.target_manager_id or source.manager_id
            if target_manager and target_manager.company_id != request.company_id:
                raise ValidationError(_("Target Direct Manager must belong to the movement-request company."))
            if target_manager == source.employee_id:
                raise ValidationError(_("An employee cannot be their own direct manager."))

            if not self.env.user.has_group("onehr_assignment.group_onehr_assignment_officer"):
                if source.manager_user_id != self.env.user:
                    raise AccessError(_("Unit Managers may propose movement only for employees they directly supervise."))
        return True

    def _copy_effective_costing(self, target_assignment):
        self.ensure_one()
        source = self.source_assignment_id
        if not self.copy_cost_allocations or not source.costing_required:
            return True
        effective_date = self.request_id.effective_date
        source_lines = source.cost_allocation_ids.filtered(
            lambda line: line.valid_from <= effective_date and (not line.valid_to or line.valid_to >= effective_date)
        )
        for allocation in source_lines:
            allocation.copy({
                "assignment_id": target_assignment.id,
                "valid_from": effective_date,
                "valid_to": self.target_effective_to,
            })
        return True

    def _execute_line(self):
        self.ensure_one()
        if self.generated_assignment_id:
            return self.generated_assignment_id
        source = self.source_assignment_id
        request = self.request_id
        if source.state != "active":
            raise UserError(_("Source Assignment %s must be Active when the movement is executed.", source.name))

        effective_date = request.effective_date
        source_end = effective_date - timedelta(days=1)
        source.with_context(**{source._STATE_CONTEXT: True}).write({"effective_to": source_end})

        target = self.env["onehr.assignment"].with_context(
            **{source._EVIDENCE_CONTEXT: True}
        ).create({
            "company_id": request.company_id.id,
            "employee_id": source.employee_id.id,
            "assignment_type": self.target_assignment_type or source.assignment_type,
            "movement_type": request.movement_type,
            "position_id": self.target_position_id.id,
            "manager_id": (self.target_manager_id or source.manager_id).id or False,
            "effective_from": effective_date,
            "effective_to": self.target_effective_to,
            "fte": self.target_fte or source.fte,
            "costing_required": source.costing_required,
            "note": self.note or request.reason,
            "source_assignment_id": source.id,
            "change_request_id": request.id,
            "change_line_id": self.id,
        })
        self._copy_effective_costing(target)
        source._trim_cost_allocations_to_assignment_end(source_end)
        target._validate_assignment_integrity()
        target.with_context(**{target._STATE_CONTEXT: True, target._EVIDENCE_CONTEXT: True}).write({
            "state": "approved",
            "approved_at": request.approved_at or fields.Datetime.now(),
            "approved_by_id": self.env.user.id,
        })

        today = fields.Date.context_today(self)
        if effective_date <= today:
            target._activate_from_governed_execution()
            source._finish_assignment_history(source_end)

        self.with_context(**{self._INTERNAL_CONTEXT: True}).write({"generated_assignment_id": target.id})
        return target

    def action_open_source_assignment(self):
        self.ensure_one()
        return open_record_action(
            name=self.source_assignment_id.display_name,
            res_model="onehr.assignment", res_id=self.source_assignment_id.id,
        )

    def action_open_generated_assignment(self):
        self.ensure_one()
        if not self.generated_assignment_id:
            raise UserError(_("This line has not generated its successor Assignment yet."))
        return open_record_action(
            name=self.generated_assignment_id.display_name,
            res_model="onehr.assignment", res_id=self.generated_assignment_id.id,
        )
