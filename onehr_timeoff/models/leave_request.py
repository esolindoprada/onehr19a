from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_timeoff_hr, require_timeoff_manager, require_timeoff_user


REQUEST_LOCKED_STATES = {"pending", "approved", "done", "cancelled"}


class OneHRLeaveRequest(models.Model):
    """Governed employee absence request with frozen entitlement evidence."""

    _name = "onehr.leave.request"
    _description = "OneHR Leave Request"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "date_from desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Leave Request No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
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
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_timeoff.group_onehr_timeoff_hr",
    )
    employee_name = fields.Char(
        string="Employee",
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_number = fields.Char(
        string="Employee No.",
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        groups="onehr_timeoff.group_onehr_timeoff_hr",
    )
    employee_user_id = fields.Many2one(
        "res.users", related="employee_id.user_id", store=True, readonly=True, index=True
    )
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_timeoff.group_onehr_timeoff_manager,onehr_timeoff.group_onehr_timeoff_hr",
    )
    department_name = fields.Char(
        string="Department",
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    manager_id = fields.Many2one(
        "hr.employee",
        related="employee_id.parent_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        groups="onehr_timeoff.group_onehr_timeoff_manager,onehr_timeoff.group_onehr_timeoff_hr",
    )
    manager_name = fields.Char(
        string="Direct Manager",
        related="employee_id.parent_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    manager_user_id = fields.Many2one(
        "res.users", related="employee_id.parent_id.user_id", store=True, readonly=True, index=True
    )

    leave_type_id = fields.Many2one(
        "onehr.leave.type",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
    )
    date_from = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    half_day = fields.Boolean(tracking=True)
    requested_days = fields.Float(compute="_compute_requested_days", store=True, readonly=True)
    reason = fields.Text(required=True, tracking=True)
    supporting_document = fields.Binary(attachment=True, copy=False)
    supporting_document_filename = fields.Char(copy=False)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )

    current_balance = fields.Float(compute="_compute_current_balance")
    balance_before = fields.Float(copy=False, readonly=True)
    balance_after = fields.Float(copy=False, readonly=True)
    allocation_usage_json = fields.Json(copy=False, readonly=True)
    allocation_ids = fields.Many2many(
        "onehr.leave.allocation",
        "onehr_leave_request_allocation_rel",
        "request_id",
        "allocation_id",
        string="Reserved Allocations",
        copy=False,
        readonly=True,
    )
    reservation_summary = fields.Char(compute="_compute_reservation_summary")

    team_conflict_count = fields.Integer(compute="_compute_team_conflicts")
    team_conflict_message = fields.Char(compute="_compute_team_conflicts")

    submitted_at = fields.Datetime(copy=False, readonly=True)
    submitted_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    approved_at = fields.Datetime(copy=False, readonly=True)
    approved_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    completed_at = fields.Datetime(copy=False, readonly=True)
    completed_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    cancelled_at = fields.Datetime(copy=False, readonly=True)
    cancelled_by_id = fields.Many2one("res.users", copy=False, readonly=True, ondelete="restrict")
    approval_lead_hours = fields.Float(compute="_compute_approval_lead_hours", store=True)

    _leave_request_number_unique = models.Constraint(
        "unique(name)", "Leave Request Number must be unique."
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_timeoff_user(self)
        prepared = []
        is_hr = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_hr")
        is_manager = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_manager")
        own_employee = self.env.user.employee_id

        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft":
                raise AccessError(_("Leave Requests must be created in Draft and advanced through governed actions."))

            requested_employee = self.env["hr.employee"].browse(values.get("employee_id")).exists()
            if not requested_employee:
                requested_employee = own_employee
            if not requested_employee:
                raise ValidationError(_("The current user is not linked to an employee; HR must create this request."))

            if not is_hr and requested_employee != own_employee:
                if not is_manager or requested_employee.parent_id.user_id != self.env.user:
                    raise AccessError(_("Managers may create leave requests only for their direct reports."))

            values["employee_id"] = requested_employee.id
            values["company_id"] = requested_employee.company_id.id
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.leave.request") or _("New")
            prepared.append(values)

        records = super().create(prepared)
        records._validate_request_integrity(submission=False)
        return records

    def _write_governed(self, values):
        """Private server-side writer for state/evidence transitions.

        Normal RPC ``write`` can never mutate state or approval/balance evidence,
        so a client cannot bypass workflow merely by forging context flags.
        """
        return super(OneHRLeaveRequest, self).write(values)

    def _check_employee_write_scope(self, values):
        if "employee_id" not in values and "company_id" not in values:
            return True
        is_hr = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_hr") or getattr(self.env, "su", False)
        target_employee = self.env["hr.employee"].browse(values.get("employee_id")).exists() if values.get("employee_id") else False
        for record in self:
            employee = target_employee or record.employee_id
            if values.get("company_id") and values["company_id"] != employee.company_id.id:
                raise AccessError(_("Leave Request company must follow the employee company."))
            if is_hr:
                continue
            own_employee = self.env.user.employee_id
            is_manager = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_manager")
            if employee != own_employee and not (is_manager and employee.parent_id.user_id == self.env.user):
                raise AccessError(_("You may change the employee only to yourself or, as a manager, to a direct report."))
        return True

    def write(self, values):
        evidence_fields = {
            "balance_before", "balance_after", "allocation_usage_json", "allocation_ids",
            "submitted_at", "submitted_by_id", "approved_at", "approved_by_id",
            "completed_at", "completed_by_id", "cancelled_at", "cancelled_by_id",
        }
        if "state" in values:
            raise AccessError(_("Leave Request state can change only through governed business actions."))
        if evidence_fields & set(values):
            raise AccessError(_("Leave execution/approval evidence can change only through governed actions."))

        self._check_employee_write_scope(values)
        protected = {
            "company_id", "employee_id", "leave_type_id", "date_from", "date_to",
            "half_day", "reason", "supporting_document", "supporting_document_filename",
        }
        if protected & set(values) and any(record.state in REQUEST_LOCKED_STATES for record in self):
            raise AccessError(_("Submitted/approved leave facts are frozen. Cancel and create a new request when correction is required."))

        result = super().write(values)
        if protected & set(values):
            self._validate_request_integrity(submission=False)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_draft_or_rejected_only(self):
        if any(record.state not in {"draft", "rejected"} for record in self):
            raise AccessError(_("Only Draft or Rejected requests may be deleted; governed leave history is retained."))

    @api.depends("employee_id", "date_from", "date_to", "half_day")
    def _compute_requested_days(self):
        for record in self:
            if not record.employee_id or not record.date_from or not record.date_to or record.date_to < record.date_from:
                record.requested_days = 0.0
                continue
            if record.half_day:
                record.requested_days = 0.5
                continue
            calendar = record.employee_id.resource_calendar_id
            if calendar:
                start_dt = datetime.combine(record.date_from, time.min).replace(tzinfo=pytz.UTC)
                end_dt = datetime.combine(record.date_to + timedelta(days=1), time.min).replace(tzinfo=pytz.UTC)
                hours = calendar.get_work_hours_count(start_dt, end_dt, compute_leaves=True)
                hours_per_day = calendar.hours_per_day or 8.0
                record.requested_days = round(hours / hours_per_day, 4) if hours_per_day else 0.0
            else:
                cursor = record.date_from
                workdays = 0.0
                while cursor <= record.date_to:
                    if cursor.weekday() < 5:
                        workdays += 1.0
                    cursor += timedelta(days=1)
                record.requested_days = workdays

    @api.depends("employee_id", "leave_type_id", "date_from")
    def _compute_current_balance(self):
        Allocation = self.env["onehr.leave.allocation"]
        for record in self:
            if record.employee_id and record.leave_type_id and record.date_from:
                record.current_balance = Allocation.balance_for_employee(
                    record.employee_id,
                    record.leave_type_id,
                    record.date_from,
                    include_future_reservations=True,
                )
            else:
                record.current_balance = 0.0

    @api.depends("allocation_usage_json")
    def _compute_reservation_summary(self):
        Allocation = self.env["onehr.leave.allocation"]
        for record in self:
            parts = []
            for item in record.allocation_usage_json or []:
                allocation = Allocation.browse(item.get("allocation_id")).exists()
                if allocation:
                    parts.append(_("%(allocation)s: %(days).2f days", allocation=allocation.name, days=float(item.get("days") or 0.0)))
            record.reservation_summary = "; ".join(parts) if parts else _("No entitlement reservation")

    @api.depends("date_from", "date_to", "department_id", "state", "leave_type_id")
    def _compute_team_conflicts(self):
        for record in self:
            if not record.date_from or not record.date_to or not record.department_id:
                record.team_conflict_count = 0
                record.team_conflict_message = False
                continue
            domain = [
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("department_id", "=", record.department_id.id),
                ("state", "in", ["pending", "approved", "done"]),
                ("date_from", "<=", record.date_to),
                ("date_to", ">=", record.date_from),
            ]
            count = self.search_count(domain)
            record.team_conflict_count = count
            limit = record.leave_type_id.max_team_absent if record.leave_type_id else 0
            if limit:
                record.team_conflict_message = _(
                    "%(count)s other team absence(s) overlap; policy limit is %(limit)s.",
                    count=count,
                    limit=limit,
                )
            elif count:
                record.team_conflict_message = _("%s other team absence(s) overlap this period.", count)
            else:
                record.team_conflict_message = _("No overlapping team absence found.")

    @api.depends("submitted_at", "approved_at")
    def _compute_approval_lead_hours(self):
        for record in self:
            if record.submitted_at and record.approved_at:
                record.approval_lead_hours = (record.approved_at - record.submitted_at).total_seconds() / 3600.0
            else:
                record.approval_lead_hours = 0.0

    @api.constrains("company_id", "employee_id", "leave_type_id", "date_from", "date_to", "half_day")
    def _check_request_integrity(self):
        self._validate_request_integrity(submission=False)

    def _validate_request_integrity(self, submission=False):
        today = fields.Date.context_today(self)
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_("Leave End Date cannot be before Start Date."))
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Employee and Leave Request must belong to the same company."))
            if record.leave_type_id.company_id != record.company_id:
                raise ValidationError(_("Leave Type and Leave Request must belong to the same company."))
            if record.half_day:
                if not record.leave_type_id.allow_half_day:
                    raise ValidationError(_("This Leave Type does not allow half-day requests."))
                if record.date_from != record.date_to:
                    raise ValidationError(_("Half-day leave must start and end on the same date."))
            if record.requested_days <= 0:
                raise ValidationError(_("The selected dates do not contain any working time for this employee."))

            if submission:
                if not record.leave_type_id.is_employee_eligible(record.employee_id, record.date_from):
                    raise ValidationError(_("Employee is not eligible for this Leave Type on the requested date."))
                notice = (record.date_from - today).days
                if notice < record.leave_type_id.minimum_notice_days:
                    raise ValidationError(
                        _("This Leave Type requires at least %(days)s day(s) advance notice.", days=record.leave_type_id.minimum_notice_days)
                    )
                if record.leave_type_id.max_consecutive_days and record.requested_days > record.leave_type_id.max_consecutive_days + 0.000001:
                    raise ValidationError(
                        _("Requested duration exceeds the policy maximum of %(days).2f days.", days=record.leave_type_id.max_consecutive_days)
                    )
                if record.leave_type_id.requires_attachment and not record.supporting_document:
                    raise ValidationError(_("A supporting document is required for this Leave Type."))
                record._check_employee_overlap()
                record._check_team_conflict_policy()
                record._check_entitlement_balance()
                record._onehr_timeoff_validate_attendance_hook()
        return True

    def _check_employee_overlap(self):
        self.ensure_one()
        overlap = self.search_count([
            ("id", "!=", self.id),
            ("employee_id", "=", self.employee_id.id),
            ("state", "in", ["pending", "approved", "done"]),
            ("date_from", "<=", self.date_to),
            ("date_to", ">=", self.date_from),
        ], limit=1)
        if overlap:
            raise ValidationError(_("The employee already has an overlapping submitted/approved leave request."))

    def _check_team_conflict_policy(self):
        self.ensure_one()
        leave_type = self.leave_type_id
        if not leave_type.max_team_absent or leave_type.team_conflict_mode == "ignore":
            return True
        # The request itself would become one more absence, hence count + 1.
        if self.team_conflict_count + 1 > leave_type.max_team_absent:
            if leave_type.team_conflict_mode == "block":
                raise ValidationError(
                    _("Team absence limit would be exceeded (%(actual)s > %(limit)s).", actual=self.team_conflict_count + 1, limit=leave_type.max_team_absent)
                )
            self.log_business_action(
                _("Team-calendar warning: this request would exceed the configured concurrent absence limit."),
            )
        return True

    def _check_entitlement_balance(self):
        self.ensure_one()
        leave_type = self.leave_type_id
        if not leave_type.allocation_required:
            return True
        balance = self.env["onehr.leave.allocation"].balance_for_employee(
            self.employee_id,
            leave_type,
            self.date_from,
            include_future_reservations=True,
        )
        remaining = balance - self.requested_days
        allowed_floor = -leave_type.negative_balance_limit if leave_type.allow_negative_balance else 0.0
        if remaining < allowed_floor - 0.000001:
            raise ValidationError(
                _(
                    "Insufficient leave balance. Available: %(balance).2f days; requested: %(requested).2f days.",
                    balance=balance,
                    requested=self.requested_days,
                )
            )
        return True

    def _onehr_timeoff_validate_attendance_hook(self):
        """Soft integration hook for Attendance/shift planning.

        ``onehr_attendance`` may extend this method when installed in a deployment,
        but Time Off intentionally has no reverse hard dependency on Attendance.
        """
        self.ensure_one()
        return True

    def onehr_timeoff_payroll_payload(self):
        """Stable downstream payload; payroll adapters remain the transaction owner."""
        self.ensure_one()
        return {
            "request_id": self.id,
            "request_no": self.name,
            "company_id": self.company_id.id,
            "employee_id": self.employee_id.id,
            "leave_type_code": self.leave_type_id.code,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "days": self.requested_days,
            "paid_leave": self.leave_type_id.paid_leave,
            "state": self.state,
        }

    def _approval_payload(self):
        self.ensure_one()
        return {
            "request_no": self.name,
            "employee": self.employee_name,
            "leave_type": self.leave_type_id.display_name,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "requested_days": self.requested_days,
            "paid_leave": self.leave_type_id.paid_leave,
            "reason": self.reason,
            "team_conflict_count": self.team_conflict_count,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = [self.manager_user_id.id] if self.manager_user_id else []
        values.update({
            "document_type": "onehr_timeoff",
            "manager_user_ids": manager_ids,
            "extra": {
                "employee_id": self.employee_id.id,
                "department_id": self.department_id.id,
                "leave_type_id": self.leave_type_id.id,
                "leave_category": self.leave_type_id.category,
                "requested_days": self.requested_days,
                "paid_leave": self.leave_type_id.paid_leave,
            },
        })
        return values

    def _reserve_entitlement(self):
        self.ensure_one()
        leave_type = self.leave_type_id
        balance_before = self.env["onehr.leave.allocation"].balance_for_employee(
            self.employee_id,
            leave_type,
            self.date_from,
            include_future_reservations=True,
        )
        if not leave_type.allocation_required:
            return [], balance_before, balance_before

        remaining = self.requested_days
        usage = []
        allocations = self.env["onehr.leave.allocation"].usable_allocations_for_request(
            self.employee_id, leave_type, self.date_from
        )
        for allocation in allocations:
            available = allocation.available_on(self.date_from, include_future_reservations=True)
            if available <= 0.000001:
                continue
            consumed = min(available, remaining)
            usage.append({"allocation_id": allocation.id, "days": round(consumed, 4)})
            remaining -= consumed
            if remaining <= 0.000001:
                break

        if remaining > 0.000001:
            existing_negative = max(-balance_before, 0.0)
            remaining_negative_capacity = max(leave_type.negative_balance_limit - existing_negative, 0.0)
            if not leave_type.allow_negative_balance or remaining > remaining_negative_capacity + 0.000001:
                raise ValidationError(_("Available entitlement changed before approval; the request can no longer be reserved."))
            usage.append({"allocation_id": 0, "days": round(remaining, 4), "negative": True})
            remaining = 0.0

        balance_after = balance_before - self.requested_days
        return usage, balance_before, balance_after

    def action_submit_for_approval(self):
        self.ensure_one()
        require_timeoff_user(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Leave Request can be submitted."))
        self._validate_request_integrity(submission=True)
        evidence = {
            "state": "pending",
            "submitted_at": fields.Datetime.now(),
            "submitted_by_id": self.env.user.id,
        }
        self._write_governed(evidence)

        if not self.leave_type_id.approval_required:
            usage, before, after = self._reserve_entitlement()
            self._write_governed({
                "state": "approved",
                "approved_at": fields.Datetime.now(),
                "approved_by_id": self.env.user.id,
                "allocation_usage_json": usage,
                "allocation_ids": [Command.set([item["allocation_id"] for item in usage if item.get("allocation_id")])],
                "balance_before": before,
                "balance_after": after,
            })
            self.log_business_action(_("Leave request auto-approved by active leave policy."))
            return True
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "pending":
            return True
        if decision == "approve":
            usage, before, after = self._reserve_entitlement()
            values = {
                "state": "approved",
                "approved_at": fields.Datetime.now(),
                "approved_by_id": self.env.user.id,
                "allocation_usage_json": usage,
                "allocation_ids": [Command.set([item["allocation_id"] for item in usage if item.get("allocation_id")])],
                "balance_before": before,
                "balance_after": after,
            }
        else:
            values = {"state": "rejected"}
        self._write_governed(values)
        return True

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        if self.state in {"approved", "done", "cancelled"}:
            raise UserError(_("Workflow approval cannot be cancelled after leave approval/execution."))
        return True

    def _latest_approved_request(self):
        self.ensure_one()
        return self.env["onehr.approval.request"].search([
            ("source_model", "=", self._name),
            ("source_res_id", "=", self.id),
            ("state", "=", "approved"),
        ], order="finalized_at desc, id desc", limit=1)

    def action_reset_to_draft(self):
        self.ensure_one()
        require_timeoff_user(self)
        if self.state != "rejected":
            raise UserError(_("Only a Rejected Leave Request can be reset to Draft."))
        self._write_governed({"state": "draft"})
        return True

    def action_mark_done(self):
        self.ensure_one()
        require_timeoff_hr(self)
        if self.state != "approved":
            raise UserError(_("Only an Approved Leave Request can be marked Done."))
        if self.date_to >= fields.Date.context_today(self):
            raise UserError(_("Leave can be marked Done only after its final date has passed."))
        self._complete_from_scheduler_or_hr()
        return True

    def _complete_from_scheduler_or_hr(self):
        self.ensure_one()
        if self.state != "approved":
            return False
        self._write_governed({
            "state": "done",
            "completed_at": fields.Datetime.now(),
            "completed_by_id": self.env.user.id,
        })
        approval = self._latest_approved_request()
        if approval:
            self.onehr_mark_approval_executed(approval)
        return True

    def action_cancel(self):
        self.ensure_one()
        require_timeoff_user(self)
        is_hr = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_hr")
        is_manager = self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_manager")
        if self.state in {"draft", "rejected"}:
            pass
        elif self.state == "approved" and (is_hr or is_manager):
            if self.date_from <= fields.Date.context_today(self) and not is_hr:
                raise UserError(_("Only Time Off HR can cancel leave that has already started."))
        else:
            raise UserError(_("This Leave Request cannot be cancelled in its current state."))
        self._write_governed({
            "state": "cancelled",
            "cancelled_at": fields.Datetime.now(),
            "cancelled_by_id": self.env.user.id,
        })
        self.log_business_action(_("Leave request cancelled; entitlement reservation is released while evidence is retained."))
        return True

    def action_schedule_manager_activity(self):
        self.ensure_one()
        require_timeoff_user(self)
        user = self.manager_user_id or self.env.user
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Review leave request %s", self.name),
            note=_("Review dates, balance, team-calendar conflict and supporting evidence."),
        )
        return True

    def action_open_employee(self):
        self.ensure_one()
        if not self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_manager"):
            raise AccessError(_("Time Off Manager authority is required to open private employee records."))
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    def action_open_leave_type(self):
        self.ensure_one()
        return open_record_action(name=self.leave_type_id.display_name, res_model="onehr.leave.type", res_id=self.leave_type_id.id)

    def action_open_reserved_allocations(self):
        self.ensure_one()
        allocation_ids = self.allocation_ids.ids
        return open_records_action(
            name=_("Reserved Allocations — %s", self.name),
            res_model="onehr.leave.allocation",
            domain=[("id", "in", allocation_ids)],
            view_mode="list,form",
        )

    def action_open_team_calendar(self):
        self.ensure_one()
        return open_records_action(
            name=_("Team Time Off — %s", self.department_name or self.company_id.name),
            res_model="onehr.leave.request",
            domain=[
                ("company_id", "=", self.company_id.id),
                ("department_id", "=", self.department_id.id),
                ("state", "in", ["pending", "approved", "done"]),
            ],
            view_mode="calendar,list,form",
        )

    def action_print_leave_request(self):
        self.ensure_one()
        return self.env.ref("onehr_timeoff.action_report_onehr_leave_request").report_action(self)

    @api.model
    def _cron_complete_due_requests(self):
        today = fields.Date.context_today(self)
        due = self.search([("state", "=", "approved"), ("date_to", "<", today)])
        for request in due:
            request._complete_from_scheduler_or_hr()
        return True
