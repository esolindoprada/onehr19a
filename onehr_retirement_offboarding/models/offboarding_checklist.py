from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action
from .security_helpers import require_offboarding_manager, require_task_owner


class OneHROffboardingChecklist(models.Model):
    """Generated clearance task and evidence.

    Core catalogue attributes are snapshotted at generation time. This preserves
    the exact duties/SLA applicable to a historical offboarding case.
    """

    _name = "onehr.offboarding.checklist"
    _description = "OneHR Offboarding Checklist Task"
    _inherit = ["onehr.mixin.audit"]
    _order = "due_date, sequence, id"

    offboarding_id = fields.Many2one(
        "onehr.offboarding", required=True, ondelete="cascade", index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="offboarding_id.company_id", store=True, index=True
    )
    employee_id = fields.Many2one(
        related="offboarding_id.employee_id", store=True, index=True
    )
    clearance_item_id = fields.Many2one(
        "onehr.clearance.item", required=True, ondelete="restrict", index=True
    )
    sequence = fields.Integer(default=10)
    item_code = fields.Char(required=True, readonly=True, index=True)
    title = fields.Char(required=True, readonly=True)
    category = fields.Selection(
        selection=lambda self: self.env["onehr.clearance.item"]._fields["category"].selection,
        required=True,
        readonly=True,
        index=True,
    )
    owner_role = fields.Selection(
        selection=lambda self: self.env["onehr.clearance.item"]._fields["owner_role"].selection,
        required=True,
        readonly=True,
        index=True,
    )
    mandatory = fields.Boolean(readonly=True)
    instructions = fields.Text(readonly=True)
    assigned_user_id = fields.Many2one(
        "res.users", ondelete="restrict", index=True, tracking=True
    )
    due_date = fields.Date(index=True, tracking=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("blocked", "Blocked"),
            ("done", "Done"),
            ("waived", "Waived"),
        ],
        default="pending",
        required=True,
        index=True,
        tracking=True,
    )
    started_at = fields.Datetime(readonly=True, copy=False)
    completed_at = fields.Datetime(readonly=True, copy=False)
    completed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    completion_note = fields.Text(tracking=True)
    block_reason = fields.Text(tracking=True)
    waiver_reason = fields.Text(copy=False, tracking=True)
    waived_at = fields.Datetime(readonly=True, copy=False)
    waived_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    asset_reference = fields.Char(tracking=True)
    return_status = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("pending", "Pending Return"),
            ("returned", "Returned"),
            ("lost", "Lost"),
            ("damaged", "Damaged"),
        ],
        default="not_applicable",
        required=True,
        tracking=True,
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_offboarding_checklist_attachment_rel",
        "checklist_id",
        "attachment_id",
        string="Evidence Attachments",
    )
    is_overdue = fields.Boolean(compute="_compute_is_overdue")

    _unique_case_item = models.Constraint(
        "UNIQUE(offboarding_id, clearance_item_id)",
        "A clearance item may be generated only once for an offboarding case.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_offboarding_generate_tasks"):
            raise AccessError(_("Checklist tasks may be created only through governed offboarding generation."))
        records = super().create(vals_list)
        return records

    def write(self, vals):
        protected = {"offboarding_id", "clearance_item_id", "item_code", "title", "category", "owner_role", "mandatory", "instructions"}
        if protected.intersection(vals) and not self.env.context.get("onehr_offboarding_internal_task_write"):
            raise ValidationError(_("Generated clearance snapshot fields are immutable."))
        if "state" in vals and not self.env.context.get("onehr_offboarding_task_state_action"):
            raise ValidationError(_("Use checklist workflow actions to change task state."))
        evidence_fields = {"started_at", "completed_at", "completed_by_id", "waived_at", "waived_by_id"}
        if evidence_fields.intersection(vals) and not self.env.context.get("onehr_offboarding_task_state_action"):
            raise ValidationError(_("Checklist timestamps and actor evidence may change only through workflow actions."))
        if "assigned_user_id" in vals and not self.env.context.get("onehr_offboarding_task_assignment_action"):
            if not (self.env.su or self.env.user.has_group("onehr_retirement_offboarding.group_onehr_offboarding_officer")):
                raise AccessError(_("Only an Offboarding Officer may reassign a clearance task."))
        if "due_date" in vals and not (self.env.su or self.env.user.has_group("onehr_retirement_offboarding.group_onehr_offboarding_officer")):
            raise AccessError(_("Only an Offboarding Officer may change a clearance due date."))
        if {"waiver_reason"}.intersection(vals) and self.filtered(lambda r: r.state == "waived") and not self.env.context.get("onehr_offboarding_task_state_action"):
            raise ValidationError(_("Waiver evidence is immutable while the task remains Waived. Reopen it before correction."))
        if self.filtered(lambda r: r.offboarding_id.state == "closed") and not self.env.context.get("onehr_offboarding_internal_task_write"):
            raise ValidationError(_("Closed offboarding evidence is immutable."))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda r: r.offboarding_id.state not in ("requested", "approval", "rejected", "cancelled")):
            raise ValidationError(_("Checklist evidence cannot be deleted after offboarding work has started."))
        require_offboarding_manager(self)
        return super().unlink()

    @api.depends("due_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.due_date and record.due_date < today and record.state not in ("done", "waived")
            )

    def _check_task_actor(self):
        require_task_owner(self)
        if self.env.su or self.env.user.has_group("onehr_retirement_offboarding.group_onehr_offboarding_officer"):
            return True
        for record in self:
            if record.assigned_user_id != self.env.user:
                raise AccessError(_("You may act only on clearance tasks assigned to you."))
        return True

    def action_assign_to_me(self):
        require_task_owner(self)
        for record in self:
            if record.state in ("done", "waived"):
                raise UserError(_("Completed or waived tasks cannot be self-assigned."))
            record.with_context(onehr_offboarding_task_assignment_action=True).write({"assigned_user_id": self.env.user.id})
        return True

    def action_start(self):
        self._check_task_actor()
        for record in self:
            if record.state not in ("pending", "blocked"):
                raise UserError(_("Only Pending or Blocked tasks can be started."))
            record.with_context(onehr_offboarding_task_state_action=True).write(
                {"state": "in_progress", "started_at": record.started_at or fields.Datetime.now(), "block_reason": False}
            )
        return True

    def action_complete(self):
        self._check_task_actor()
        for record in self:
            if record.state not in ("pending", "in_progress", "blocked"):
                raise UserError(_("This clearance task cannot be completed from its current state."))
            if record.category == "asset" and record.return_status == "pending":
                raise UserError(_("Set the asset return disposition before completing this task."))
            record.with_context(onehr_offboarding_task_state_action=True).write(
                {
                    "state": "done",
                    "completed_at": fields.Datetime.now(),
                    "completed_by_id": self.env.user.id,
                    "block_reason": False,
                }
            )
        return True

    def action_block(self):
        self._check_task_actor()
        for record in self:
            if not record.block_reason:
                raise UserError(_("Enter a Block Reason before blocking the task."))
            record.with_context(onehr_offboarding_task_state_action=True).write({"state": "blocked"})
        return True

    def action_waive(self):
        require_offboarding_manager(self)
        for record in self:
            if not record.waiver_reason:
                raise UserError(_("Enter a Waiver Reason before waiving a clearance task."))
            record.with_context(onehr_offboarding_task_state_action=True).write(
                {
                    "state": "waived",
                    "waived_at": fields.Datetime.now(),
                    "waived_by_id": self.env.user.id,
                    "completed_at": False,
                    "completed_by_id": False,
                }
            )
        return True

    def action_reopen(self):
        require_offboarding_manager(self)
        for record in self:
            if record.offboarding_id.state == "closed":
                raise UserError(_("A task in a Closed offboarding case cannot be reopened."))
            if record.state not in ("done", "waived"):
                raise UserError(_("Only Done or Waived tasks can be reopened."))
            record.with_context(onehr_offboarding_task_state_action=True).write(
                {
                    "state": "pending",
                    "completed_at": False,
                    "completed_by_id": False,
                    "waived_at": False,
                    "waived_by_id": False,
                }
            )
        return True

    def action_open_offboarding(self):
        self.ensure_one()
        return open_record_action(
            name=self.offboarding_id.display_name,
            res_model="onehr.offboarding",
            res_id=self.offboarding_id.id,
        )
