from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_assignment_manager, require_assignment_officer


APPROVED_STATES = {"approved", "active"}
LOCKED_STATES = {"proposed", "approved", "active", "ended", "cancelled"}


class OneHRAssignment(models.Model):
    """Effective-dated enterprise placement record.

    This model owns placement and movement history. Odoo ``hr.version`` remains
    the canonical store for native employment facts; activating a primary
    assignment synchronizes the approved placement into a version effective on
    the assignment date instead of creating a parallel employee master.
    """

    _name = "onehr.assignment"
    _description = "OneHR Employee Assignment"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "effective_from desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_assignment_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_assignment_evidence_controlled"

    name = fields.Char(
        string="Assignment No.", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True, tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="restrict", index=True,
        tracking=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    employee_name = fields.Char(
        string="Employee", related="employee_id.name", store=True,
        compute_sudo=True, readonly=True, index=True,
    )
    employee_number = fields.Char(
        string="Employee No.", related="employee_id.onehr_employee_number",
        store=True, compute_sudo=True, readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )

    assignment_type = fields.Selection(
        [("primary", "Primary"), ("secondary", "Secondary")],
        required=True, default="primary", index=True, tracking=True,
    )
    movement_type = fields.Selection(
        [
            ("initial", "Initial Placement"),
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
        required=True, default="initial", index=True, tracking=True,
    )
    position_id = fields.Many2one(
        "onehr.position", required=True, ondelete="restrict", index=True,
        tracking=True, check_company=True,
    )
    job_id = fields.Many2one(
        "hr.job", related="position_id.job_id", store=True, readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    department_id = fields.Many2one(
        "hr.department", related="position_id.department_id", store=True,
        readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    grade_id = fields.Many2one(
        "onehr.grade", related="position_id.grade_id", store=True, readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    work_location_id = fields.Many2one(
        "hr.work.location", related="position_id.work_location_id", store=True,
        readonly=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )

    manager_id = fields.Many2one(
        "hr.employee", string="Direct Manager", ondelete="restrict", index=True,
        tracking=True, check_company=True,
        groups="onehr_assignment.group_onehr_assignment_officer,onehr_assignment.group_onehr_assignment_manager",
    )
    manager_name = fields.Char(
        string="Direct Manager", related="manager_id.name", store=True,
        compute_sudo=True, readonly=True, index=True,
    )
    manager_user_id = fields.Many2one(
        "res.users", related="manager_id.user_id", store=True, readonly=True,
        index=True,
        help="Stored reporting-manager user used by least-privilege unit-manager record rules.",
    )

    effective_from = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    effective_to = fields.Date(index=True, tracking=True)
    fte = fields.Float(string="Assigned FTE", required=True, default=1.0, tracking=True)
    costing_required = fields.Boolean(
        string="Require Cost Allocation", default=False, tracking=True,
        help="When enabled, effective allocation lines must total exactly 100 percent.",
    )
    note = fields.Text(tracking=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("proposed", "Proposed"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("ended", "Ended"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        required=True, default="draft", index=True, tracking=True,
    )

    source_assignment_id = fields.Many2one(
        "onehr.assignment", string="Previous Assignment", ondelete="restrict",
        copy=False, index=True, readonly=True,
    )
    successor_assignment_ids = fields.One2many(
        "onehr.assignment", "source_assignment_id", string="Successor Assignments", readonly=True,
    )
    change_request_id = fields.Many2one(
        "onehr.assignment.change.request", ondelete="restrict", copy=False,
        index=True, readonly=True,
    )
    change_line_id = fields.Many2one(
        "onehr.assignment.change.line", ondelete="restrict", copy=False,
        index=True, readonly=True,
    )
    cost_allocation_ids = fields.One2many(
        "onehr.assignment.cost.allocation", "assignment_id", string="Cost Allocations",
    )

    approved_at = fields.Datetime(copy=False, readonly=True)
    approved_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    activated_at = fields.Datetime(copy=False, readonly=True)
    activated_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    ended_at = fields.Datetime(copy=False, readonly=True)
    ended_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")

    successor_count = fields.Integer(compute="_compute_successor_count")
    allocation_count = fields.Integer(compute="_compute_allocation_count")
    is_effective_today = fields.Boolean(compute="_compute_is_effective_today")

    _assignment_number_unique = models.Constraint(
        "unique(name)", "Assignment Number must be unique."
    )

    @api.model_create_multi
    def create(self, vals_list):
        state_context = self.env.context.get(self._STATE_CONTEXT)
        evidence_context = self.env.context.get(self._EVIDENCE_CONTEXT)
        evidence_fields = {
            "approved_at", "approved_by_id", "activated_at", "activated_by_id",
            "ended_at", "ended_by_id", "source_assignment_id", "change_request_id", "change_line_id",
        }
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft" and not state_context:
                raise AccessError(_("Assignments must be created in Draft and advanced through governed actions."))
            if evidence_fields & set(values) and not evidence_context:
                raise AccessError(_("Assignment evidence can be set only by governed business execution."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.assignment") or _("New")
            prepared.append(values)
        records = super().create(prepared)
        records._validate_assignment_integrity()
        return records

    def write(self, values):
        state_context = self.env.context.get(self._STATE_CONTEXT)
        evidence_context = self.env.context.get(self._EVIDENCE_CONTEXT)
        if "state" in values and not state_context:
            raise AccessError(_("Assignment state can change only through governed business actions."))

        evidence_fields = {
            "approved_at", "approved_by_id", "activated_at", "activated_by_id",
            "ended_at", "ended_by_id", "source_assignment_id", "change_request_id", "change_line_id",
        }
        if evidence_fields & set(values) and not evidence_context:
            raise AccessError(_("Assignment evidence can change only through governed business actions."))

        protected = {
            "company_id", "employee_id", "assignment_type", "movement_type",
            "position_id", "manager_id", "effective_from", "effective_to", "fte", "costing_required",
        }
        if protected & set(values) and any(record.state in LOCKED_STATES for record in self) and not state_context:
            raise AccessError(
                _("Submitted assignment facts are frozen. Create an effective-dated successor movement instead.")
            )

        result = super().write(values)
        if protected & set(values):
            self._validate_assignment_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_history(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only Draft assignment rows can be deleted; governed history is retained."))

    @api.constrains(
        "company_id", "employee_id", "assignment_type", "position_id", "manager_id",
        "effective_from", "effective_to", "fte", "state",
    )
    def _check_assignment_integrity(self):
        self._validate_assignment_integrity()

    def _validate_assignment_integrity(self):
        for record in self:
            if record.effective_to and record.effective_to < record.effective_from:
                raise ValidationError(_("Assignment End Date cannot be before Start Date."))
            if record.fte <= 0 or record.fte > 1.0:
                raise ValidationError(_("Assigned FTE must be greater than zero and not exceed 1.0."))
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Employee and Assignment must belong to the same company."))
            if record.position_id.company_id != record.company_id:
                raise ValidationError(_("Position and Assignment must belong to the same company."))
            if record.manager_id:
                if record.manager_id == record.employee_id:
                    raise ValidationError(_("An employee cannot be their own direct manager."))
                if record.manager_id.company_id != record.company_id:
                    raise ValidationError(_("Direct Manager must belong to the Assignment company."))

            if not record.position_id.active:
                raise ValidationError(_("The selected Position must be active."))
            if record.position_id.status in {"frozen", "closed"} and record.state in APPROVED_STATES:
                raise ValidationError(_("Approved/Active assignments cannot occupy a Frozen or Closed Position."))
            if record.position_id.valid_from and record.effective_from < record.position_id.valid_from:
                raise ValidationError(_("Assignment cannot start before the Position validity begins."))
            if record.position_id.valid_to and (
                not record.effective_to or record.effective_to > record.position_id.valid_to
            ):
                raise ValidationError(_("Assignment validity must be contained by Position validity."))

            if record.state in APPROVED_STATES:
                record._check_employee_overlap_rules()
                record._check_position_capacity()
                if record.costing_required:
                    record._validate_cost_allocation_coverage()
        return True

    def _overlap_domain(self, start_date=None, end_date=None):
        self.ensure_one()
        start = start_date or self.effective_from
        end = end_date or self.effective_to
        domain = [("id", "!=", self.id), ("state", "in", list(APPROVED_STATES))]
        if end:
            domain.append(("effective_from", "<=", end))
        domain += ["|", ("effective_to", "=", False), ("effective_to", ">=", start)]
        return domain

    def _check_employee_overlap_rules(self):
        self.ensure_one()
        Assignment = self.env["onehr.assignment"]
        overlap = Assignment.search(
            self._overlap_domain() + [
                ("employee_id", "=", self.employee_id.id),
                ("company_id", "=", self.company_id.id),
            ]
        )
        if self.assignment_type == "primary" and overlap.filtered(lambda row: row.assignment_type == "primary"):
            raise ValidationError(
                _("Only one Approved/Active primary assignment may overlap for an employee in a company.")
            )

        boundaries = {self.effective_from}
        boundaries.update(row.effective_from for row in overlap if row.effective_from)
        for row in overlap:
            if row.effective_to:
                next_day = row.effective_to + timedelta(days=1)
                if not self.effective_to or next_day <= self.effective_to:
                    boundaries.add(next_day)
        for date_value in sorted(boundaries):
            if date_value < self.effective_from or (self.effective_to and date_value > self.effective_to):
                continue
            rows = (overlap | self).filtered(lambda row: row._is_effective_on(date_value))
            total_fte = sum(rows.mapped("fte"))
            if total_fte > 1.000001:
                raise ValidationError(
                    _("Employee total FTE exceeds 1.0 on %(date)s (%(fte).2f).", date=date_value, fte=total_fte)
                )

    def _is_effective_on(self, date_value):
        self.ensure_one()
        return self.effective_from <= date_value and (not self.effective_to or self.effective_to >= date_value)

    def _position_capacity_for_date(self, date_value):
        self.ensure_one()
        Budget = self.env["onehr.position.budget"]
        budget = Budget.search(
            [
                ("position_id", "=", self.position_id.id),
                ("state", "=", "active"),
                ("valid_from", "<=", date_value),
                "|", ("valid_to", "=", False), ("valid_to", ">=", date_value),
            ],
            order="valid_from desc, id desc", limit=1,
        )
        if budget:
            return budget.authorized_headcount, budget.authorized_fte
        return self.position_id.authorized_headcount, self.position_id.authorized_fte

    def _check_position_capacity(self):
        self.ensure_one()
        Assignment = self.env["onehr.assignment"]
        overlap = Assignment.search(
            self._overlap_domain() + [
                ("position_id", "=", self.position_id.id),
                ("company_id", "=", self.company_id.id),
            ]
        )
        Budget = self.env["onehr.position.budget"]
        budget_domain = [
            ("position_id", "=", self.position_id.id),
            ("state", "=", "active"),
        ]
        if self.effective_to:
            budget_domain.append(("valid_from", "<=", self.effective_to))
        budget_domain += ["|", ("valid_to", "=", False), ("valid_to", ">=", self.effective_from)]
        budgets = Budget.search(budget_domain)

        boundaries = {self.effective_from}
        boundaries.update(row.effective_from for row in overlap if row.effective_from)
        boundaries.update(budget.valid_from for budget in budgets if budget.valid_from)
        # A budget ending can reduce allowed capacity while an assignment keeps
        # running. Validate the first day after every budget interval as well, so
        # a future fallback to the base Position capacity cannot silently create
        # an over-capacity assignment.
        for budget in budgets:
            if budget.valid_to:
                next_day = budget.valid_to + timedelta(days=1)
                if not self.effective_to or next_day <= self.effective_to:
                    boundaries.add(next_day)
        for date_value in sorted(boundaries):
            if date_value < self.effective_from or (self.effective_to and date_value > self.effective_to):
                continue
            rows = (overlap | self).filtered(lambda row: row._is_effective_on(date_value))
            headcount = len(rows)
            assigned_fte = sum(rows.mapped("fte"))
            allowed_hc, allowed_fte = self._position_capacity_for_date(date_value)
            if headcount > allowed_hc:
                raise ValidationError(
                    _("Position headcount capacity is exceeded on %(date)s: %(actual)s > %(allowed)s.",
                      date=date_value, actual=headcount, allowed=allowed_hc)
                )
            if assigned_fte > allowed_fte + 0.000001:
                raise ValidationError(
                    _("Position FTE capacity is exceeded on %(date)s: %(actual).2f > %(allowed).2f.",
                      date=date_value, actual=assigned_fte, allowed=allowed_fte)
                )

    def _validate_cost_allocation_coverage(self):
        """Implemented in costing.py; kept here as an explicit model contract."""
        return True

    @api.depends("successor_assignment_ids")
    def _compute_successor_count(self):
        for record in self:
            record.successor_count = len(record.successor_assignment_ids)

    @api.depends("cost_allocation_ids")
    def _compute_allocation_count(self):
        for record in self:
            record.allocation_count = len(record.cost_allocation_ids)

    def _compute_is_effective_today(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_effective_today = record._is_effective_on(today)

    def _approval_payload(self):
        self.ensure_one()
        return {
            "assignment": self.name,
            "employee": self.employee_name,
            "assignment_type": self.assignment_type,
            "movement_type": self.movement_type,
            "position": self.position_id.display_name,
            "manager": self.manager_name,
            "effective_from": fields.Date.to_string(self.effective_from),
            "effective_to": fields.Date.to_string(self.effective_to) if self.effective_to else False,
            "fte": self.fte,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = [self.manager_user_id.id] if self.manager_user_id else []
        values.update({
            "document_type": "onehr_assignment",
            "manager_user_ids": manager_ids,
            "extra": {
                "employee_id": self.employee_id.id,
                "position_id": self.position_id.id,
                "department_id": self.department_id.id,
                "grade_id": self.grade_id.id,
                "assignment_type": self.assignment_type,
                "movement_type": self.movement_type,
                "fte": self.fte,
            },
        })
        return values

    def action_submit_for_approval(self):
        self.ensure_one()
        require_assignment_officer(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft assignment can be proposed."))
        self._validate_assignment_integrity()
        if self.costing_required:
            self._validate_cost_allocation_coverage()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "proposed"})
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "proposed":
            return True
        vals = {"state": "approved" if decision == "approve" else "rejected"}
        if decision == "approve":
            vals.update({"approved_at": fields.Datetime.now(), "approved_by_id": self.env.user.id})
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write(vals)
        return True

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        if self.state in {"active", "ended"}:
            raise UserError(_("Approval cannot be cancelled after assignment execution/history activation."))
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        require_assignment_officer(self)
        if self.state != "rejected":
            raise UserError(_("Only a Rejected assignment can be reset to Draft."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "draft"})
        return True

    def _latest_approved_request(self):
        self.ensure_one()
        return self.env["onehr.approval.request"].search(
            [("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")],
            order="finalized_at desc, id desc", limit=1,
        )

    def _sync_primary_to_native_hr(self):
        self.ensure_one()
        if self.assignment_type != "primary":
            return False
        # Odoo 19 create_version() is the native effective-dating API. It can
        # return an existing same-date version, so write the placement facts to
        # the returned record explicitly.
        version = self.employee_id.create_version({"date_version": self.effective_from})
        version.write({
            "job_id": self.job_id.id,
            "department_id": self.department_id.id,
            "work_location_id": self.work_location_id.id or False,
            "onehr_grade_id": self.grade_id.id or False,
            "onehr_primary_position_id": self.position_id.id,
        })
        if self._is_effective_on(fields.Date.context_today(self)):
            self.employee_id.write({"parent_id": self.manager_id.id or False})
        return version

    def _activate_from_governed_execution(self):
        """Activate a due approved row after upstream authority has already been proven.

        Public UI calls remain authority-gated. This private method is also used
        by an approved batch movement and the scheduled effective-date runner.
        """
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("Only an Approved assignment can be activated."))
        today = fields.Date.context_today(self)
        if self.effective_from > today:
            raise UserError(_("A future-dated assignment remains Approved until its effective date."))
        if self.effective_to and self.effective_to < today:
            raise UserError(_("An already-expired assignment cannot be activated."))
        self._validate_assignment_integrity()
        if self.costing_required:
            self._validate_cost_allocation_coverage()
        self._sync_primary_to_native_hr()
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "active",
            "activated_at": fields.Datetime.now(),
            "activated_by_id": self.env.user.id,
        })
        request = self._latest_approved_request()
        if request:
            self.onehr_mark_approval_executed(request)
        return True

    def action_activate(self):
        self.ensure_one()
        require_assignment_manager(self)
        return self._activate_from_governed_execution()

    def _finish_assignment_history(self, end_date=None):
        self.ensure_one()
        target_end = end_date or fields.Date.context_today(self)
        if target_end < self.effective_from:
            raise ValidationError(_("Assignment end date cannot precede the assignment start date."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "effective_to": target_end,
            "state": "ended",
            "ended_at": fields.Datetime.now(),
            "ended_by_id": self.env.user.id,
        })
        return True

    def action_end_today(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "active":
            raise UserError(_("Only an Active assignment can be ended."))
        return self._finish_assignment_history(fields.Date.context_today(self))

    def action_cancel_draft(self):
        self.ensure_one()
        require_assignment_officer(self)
        if self.state not in {"draft", "rejected"}:
            raise UserError(_("Only Draft or Rejected assignments can be cancelled."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "cancelled"})
        return True

    def action_schedule_manager_activity(self):
        self.ensure_one()
        require_assignment_officer(self)
        user = self.manager_user_id or self.env.user
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Review assignment %s", self.name),
            note=_("Review the effective placement, reporting line and FTE allocation."),
        )
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    def action_open_position(self):
        self.ensure_one()
        return open_record_action(name=self.position_id.display_name, res_model="onehr.position", res_id=self.position_id.id)

    def action_open_cost_allocations(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_records_action(
            name=_("Cost Allocations — %s", self.name),
            res_model="onehr.assignment.cost.allocation",
            domain=[("assignment_id", "=", self.id)],
            context={"default_assignment_id": self.id},
        )

    def action_open_successors(self):
        self.ensure_one()
        require_assignment_officer(self)
        return open_records_action(
            name=_("Successor Assignments — %s", self.name),
            res_model="onehr.assignment",
            domain=[("source_assignment_id", "=", self.id)],
        )

    def action_open_change_request(self):
        self.ensure_one()
        if not self.change_request_id:
            raise UserError(_("This assignment was not generated by a movement request."))
        return open_record_action(
            name=self.change_request_id.display_name,
            res_model="onehr.assignment.change.request",
            res_id=self.change_request_id.id,
        )

    @api.model
    def _cron_apply_effective_assignments(self):
        today = fields.Date.context_today(self)
        due = self.search([
            ("state", "=", "approved"),
            ("effective_from", "<=", today),
            "|", ("effective_to", "=", False), ("effective_to", ">=", today),
        ])
        for assignment in due:
            # Cron executes as configured system user but keeps normal model
            # methods and record rules; no business sudo bypass is used here.
            assignment._activate_from_governed_execution()
        expired = self.search([
            ("state", "=", "active"), ("effective_to", "!=", False), ("effective_to", "<", today),
        ])
        for assignment in expired:
            assignment._finish_assignment_history(assignment.effective_to)
        return True
