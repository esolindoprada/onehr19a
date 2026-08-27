from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action


def _float_hour_to_time(hour_value):
    """Convert a decimal business hour to a Python time without float drift."""
    total_minutes = int(round(float(hour_value or 0.0) * 60.0))
    total_minutes = max(0, min(total_minutes, 24 * 60))
    if total_minutes == 24 * 60:
        return time(0, 0), 1
    return time(total_minutes // 60, total_minutes % 60), 0


def _local_business_datetime_to_utc(day, hour_value, tz_name, extra_day=0):
    local_time, hour_day_offset = _float_hour_to_time(hour_value)
    local_day = day + timedelta(days=extra_day + hour_day_offset)
    timezone = pytz.timezone(tz_name or "UTC")
    local_dt = timezone.localize(datetime.combine(local_day, local_time))
    return local_dt.astimezone(pytz.utc).replace(tzinfo=None)


def _reference_selection(env, model_name, label):
    return [(model_name, label)] if model_name in env else []


class OneHRShift(models.Model):
    """Effective-dated shift definition.

    ``resource.calendar`` remains the canonical Odoo work-calendar structure. The
    OneHR shift adds operational boundaries, grace/rounding/geofence rules and
    enterprise scope used to reconcile actual punches against an expected shift.
    """

    _name = "onehr.shift"
    _description = "OneHR Shift"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "company_id, code, valid_from desc, id desc"

    _STATE_CONTEXT = "onehr_shift_state_controlled"

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True, tracking=True,
    )
    resource_calendar_id = fields.Many2one(
        "resource.calendar", string="Work Calendar", required=True,
        ondelete="restrict", check_company=True, tracking=True,
        help="Canonical Odoo work calendar used by this shift.",
    )
    work_location_id = fields.Many2one(
        "hr.work.location", ondelete="restrict", check_company=True,
        index=True, tracking=True,
        help="Optional location scope. Empty means the shift is not location-specific.",
    )
    position_id = fields.Many2one(
        "onehr.position", ondelete="restrict", check_company=True,
        index=True, tracking=True,
        help="Optional position scope. A scoped shift is preferred over a generic shift.",
    )
    branch_ref = fields.Reference(
        selection="_selection_branch_reference", string="Branch Scope", tracking=True,
        help="Optional branch reference without creating a hard dependency on the branch addon.",
    )
    priority = fields.Integer(default=10, tracking=True)
    timezone = fields.Selection(
        selection=lambda self: [(tz, tz) for tz in pytz.common_timezones],
        required=True, default=lambda self: self.env.company.resource_calendar_id.tz or "UTC",
        tracking=True,
    )

    start_hour = fields.Float(string="Planned Start", required=True, default=8.0, tracking=True)
    end_hour = fields.Float(string="Planned End", required=True, default=17.0, tracking=True)
    spans_next_day = fields.Boolean(string="Ends Next Day", default=False, tracking=True)
    late_grace_minutes = fields.Integer(default=5, tracking=True)
    early_leave_grace_minutes = fields.Integer(default=5, tracking=True)
    rounding_minutes = fields.Selection(
        [("1", "1 minute"), ("5", "5 minutes"), ("10", "10 minutes"),
         ("15", "15 minutes"), ("30", "30 minutes")],
        required=True, default="1", tracking=True,
    )
    geofence_radius_m = fields.Integer(
        string="Geofence Radius (m)", default=0, tracking=True,
        help="Zero disables geofence evaluation. Location coordinates come from the OneHR work location.",
    )

    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=False)
    sunday = fields.Boolean(default=False)

    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        required=True, default="draft", index=True, tracking=True,
    )
    schedule_ids = fields.One2many("onehr.shift.assignment", "shift_id", string="Direct Schedules")
    attendance_ids = fields.One2many("hr.attendance", "onehr_shift_id", string="Attendance History", readonly=True)
    schedule_count = fields.Integer(compute="_compute_counts")
    attendance_count = fields.Integer(compute="_compute_counts")

    @api.model
    def _selection_branch_reference(self):
        return _reference_selection(self.env, "onehr.branch", _("OneHR Branch"))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values["code"] = (values.get("code") or "").strip().upper()
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Shifts must be created in Draft and activated through the governed action."))
        records = super().create(vals_list)
        records._validate_shift_integrity()
        return records

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Shift state can change only through governed business actions."))
        if "code" in values:
            values = dict(values, code=(values.get("code") or "").strip().upper())
        protected = {
            "code", "company_id", "resource_calendar_id", "work_location_id", "position_id",
            "branch_ref", "timezone", "start_hour", "end_hour", "spans_next_day",
            "valid_from", "valid_to",
        }
        if protected & set(values) and any(record.state == "retired" for record in self):
            raise AccessError(_("Retired shift history is immutable. Create a new effective-dated shift row."))
        result = super().write(values)
        if protected & set(values):
            self._validate_shift_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_shift(self):
        if any(record.state != "draft" or record.attendance_count or record.schedule_count for record in self):
            raise AccessError(_("Only an unused Draft shift may be deleted; operational history is retained."))

    @api.constrains(
        "code", "company_id", "valid_from", "valid_to", "state", "start_hour", "end_hour",
        "spans_next_day", "late_grace_minutes", "early_leave_grace_minutes", "geofence_radius_m",
        "resource_calendar_id", "work_location_id", "position_id", "branch_ref",
    )
    def _check_shift_integrity(self):
        self._validate_shift_integrity()

    def _validate_shift_integrity(self):
        for record in self:
            if not record.code:
                raise ValidationError(_("Shift Code is required."))
            if record.start_hour < 0 or record.start_hour >= 24 or record.end_hour < 0 or record.end_hour > 24:
                raise ValidationError(_("Planned start/end must be valid decimal hours between 00:00 and 24:00."))
            if not record.spans_next_day and record.end_hour <= record.start_hour:
                raise ValidationError(_("Same-day shifts must end after they start. Enable 'Ends Next Day' for night shifts."))
            if record.spans_next_day and record.end_hour == record.start_hour:
                raise ValidationError(_("A night shift cannot have identical start and end times."))
            if min(record.late_grace_minutes, record.early_leave_grace_minutes, record.geofence_radius_m) < 0:
                raise ValidationError(_("Grace periods and geofence radius cannot be negative."))
            if record.resource_calendar_id.company_id and record.resource_calendar_id.company_id != record.company_id:
                raise ValidationError(_("The Work Calendar must belong to the Shift company or be global."))
            for scoped in (record.work_location_id, record.position_id):
                if scoped and scoped.company_id and scoped.company_id != record.company_id:
                    raise ValidationError(_("Shift location/position scope must belong to the Shift company."))
            if record.branch_ref and hasattr(record.branch_ref, "company_id") and record.branch_ref.company_id != record.company_id:
                raise ValidationError(_("The optional branch scope must belong to the Shift company."))
            overlap_domain = [
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("code", "=ilike", record.code),
                ("state", "=", "active"),
                "|", ("valid_to", "=", False), ("valid_to", ">=", record.valid_from),
            ]
            if record.valid_to:
                overlap_domain.append(("valid_from", "<=", record.valid_to))
            if record.state == "active" and self.with_context(active_test=False).search_count(overlap_domain, limit=1):
                raise ValidationError(_("Active effective periods for the same Shift Code cannot overlap."))

    def _works_on(self, day):
        self.ensure_one()
        field_name = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[day.weekday()]
        return bool(self[field_name])

    def _planned_interval_utc(self, day):
        """Return expected [start, stop] in naive UTC for an employee-local business day."""
        self.ensure_one()
        if not self._works_on(day):
            return False, False
        start = _local_business_datetime_to_utc(day, self.start_hour, self.timezone)
        end = _local_business_datetime_to_utc(day, self.end_hour, self.timezone, 1 if self.spans_next_day else 0)
        return start, end

    @api.model
    def resolve_for_employee_date(self, employee, day):
        """Resolve the most specific active Shift when no explicit schedule exists.

        The resolver deliberately keeps ``onehr_assignment`` soft. If that addon is
        installed, its effective primary assignment supplies position/work-location
        context. Otherwise the employee's native work location is used. Branch-scoped
        shifts require an explicit Shift Schedule until the branch owner exposes a
        stable employee/assignment branch contract.
        """
        day = fields.Date.to_date(day)
        if not employee or not day:
            return self.browse()

        position = self.env["onehr.position"]
        work_location = employee.work_location_id if "work_location_id" in employee._fields else self.env["hr.work.location"]

        if "onehr.assignment" in self.env:
            assignment = self.env["onehr.assignment"].search([
                ("employee_id", "=", employee.id),
                ("company_id", "=", employee.company_id.id),
                ("assignment_type", "=", "primary"),
                ("state", "in", ["approved", "active"]),
                ("effective_from", "<=", day),
                "|", ("effective_to", "=", False), ("effective_to", ">=", day),
            ], order="effective_from desc, id desc", limit=1)
            if assignment:
                position = assignment.position_id
                work_location = assignment.work_location_id or work_location

        candidates = self.search([
            ("company_id", "=", employee.company_id.id),
            ("state", "=", "active"),
            ("valid_from", "<=", day),
            "|", ("valid_to", "=", False), ("valid_to", ">=", day),
        ], order="priority desc, id")

        ranked = []
        for shift in candidates:
            if shift.branch_ref or not shift._works_on(day):
                continue
            if shift.position_id and shift.position_id != position:
                continue
            if shift.work_location_id and shift.work_location_id != work_location:
                continue
            specificity = (4 if shift.position_id else 0) + (2 if shift.work_location_id else 0)
            ranked.append((specificity, shift.priority, -shift.id, shift))
        if not ranked:
            return self.browse()
        ranked.sort(key=lambda item: item[:3], reverse=True)
        return ranked[0][3]

    def _compute_counts(self):
        Schedule = self.env["onehr.shift.assignment"]
        Attendance = self.env["hr.attendance"]
        for record in self:
            record.schedule_count = Schedule.search_count([("shift_id", "=", record.id)])
            record.attendance_count = Attendance.search_count([("onehr_shift_id", "=", record.id)])

    def action_activate(self):
        self._require_manager()
        self._validate_shift_integrity()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        self.log_business_action(_("Shift activated"))
        return True

    def action_retire(self):
        self._require_manager()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "retired"})
        self.log_business_action(_("Shift retired"))
        return True

    def action_preview_today(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start, stop = self._planned_interval_utc(today)
        if not start:
            message = _("%s is not a work day for this shift.", today)
        else:
            message = _("Planned interval for %s: %s → %s UTC.", today, fields.Datetime.to_string(start), fields.Datetime.to_string(stop))
        return display_notification(message, title=self.display_name)

    def action_open_calendar(self):
        self.ensure_one()
        return open_record_action(self.resource_calendar_id.display_name, "resource.calendar", self.resource_calendar_id.id)

    def action_open_schedules(self):
        self.ensure_one()
        return open_records_action(
            _("Schedules — %s", self.display_name), "onehr.shift.assignment",
            [("shift_id", "=", self.id)], {"default_shift_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_attendances(self):
        self.ensure_one()
        return open_records_action(
            _("Attendance — %s", self.display_name), "hr.attendance", [("onehr_shift_id", "=", self.id)],
            {"search_default_onehr_shift_id": self.id}, "list,calendar,pivot,graph,form",
        )

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))


class OneHRShiftPattern(models.Model):
    """Reusable ED2 rotation pattern without inventing an unregistered pattern-line model."""

    _name = "onehr.shift.pattern"
    _description = "OneHR Shift Rotation Pattern Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "company_id, code, version desc"

    _STATE_CONTEXT = "onehr_shift_pattern_state_controlled"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    version = fields.Integer(required=True, default=1, index=True, tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="restrict", index=True, tracking=True)
    shift_ids = fields.Many2many("onehr.shift", string="Allowed Shifts", relation="onehr_shift_pattern_shift_rel", column1="pattern_id", column2="shift_id", tracking=True)
    anchor_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    cycle_codes = fields.Char(
        required=True, default="OFF", tracking=True,
        help="Comma-separated cycle tokens using Allowed Shift codes; OFF means a non-working cycle day. Example: D,D,OFF,OFF,N,N,OFF.",
    )
    cycle_length_days = fields.Integer(compute="_compute_cycle_length", store=True)
    state = fields.Selection([("draft", "Draft"), ("active", "Active"), ("retired", "Retired")], required=True, default="draft", index=True, tracking=True)
    schedule_ids = fields.One2many("onehr.shift.assignment", "pattern_id", string="Pattern Schedules")
    schedule_count = fields.Integer(compute="_compute_schedule_count")

    _pattern_version_unique = models.Constraint(
        "unique(company_id, code, version)", "Shift Pattern Code and Version must be unique per company."
    )

    @api.depends("cycle_codes")
    def _compute_cycle_length(self):
        for record in self:
            record.cycle_length_days = len(record._cycle_tokens())

    def _cycle_tokens(self):
        self.ensure_one()
        return [token.strip().upper() for token in (self.cycle_codes or "").split(",") if token.strip()]

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values["code"] = (values.get("code") or "").strip().upper()
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Shift Patterns must start in Draft."))
        records = super().create(vals_list)
        records._validate_pattern()
        return records

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Pattern state can change only through governed actions."))
        if "code" in values:
            values = dict(values, code=(values.get("code") or "").strip().upper())
        if any(record.state == "retired" for record in self) and ({"code", "version", "shift_ids", "cycle_codes", "anchor_date", "valid_from", "valid_to"} & set(values)):
            raise AccessError(_("Retired pattern versions are immutable. Create a new version."))
        result = super().write(values)
        if {"code", "version", "shift_ids", "cycle_codes", "anchor_date", "valid_from", "valid_to"} & set(values):
            self._validate_pattern()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_pattern_history(self):
        if any(record.state != "draft" or record.schedule_count for record in self):
            raise AccessError(_("Only an unused Draft pattern version may be deleted."))

    @api.constrains("shift_ids", "cycle_codes", "company_id", "valid_from", "valid_to")
    def _check_pattern(self):
        self._validate_pattern()

    def _validate_pattern(self):
        for record in self:
            tokens = record._cycle_tokens()
            if not tokens:
                raise ValidationError(_("A Shift Pattern must contain at least one cycle token."))
            codes = {shift.code.upper() for shift in record.shift_ids}
            unknown = sorted({token for token in tokens if token != "OFF" and token not in codes})
            if unknown:
                raise ValidationError(_("Unknown Shift Pattern token(s): %s", ", ".join(unknown)))
            if any(shift.company_id != record.company_id for shift in record.shift_ids):
                raise ValidationError(_("All pattern shifts must belong to the pattern company."))

    def _shift_for_date(self, day, cycle_offset=0):
        self.ensure_one()
        tokens = self._cycle_tokens()
        if not tokens:
            return self.env["onehr.shift"]
        index = ((day - self.anchor_date).days + int(cycle_offset or 0)) % len(tokens)
        token = tokens[index]
        if token == "OFF":
            return self.env["onehr.shift"]
        candidates = self.shift_ids.filtered(
            lambda shift: shift.code.upper() == token
            and shift.state == "active"
            and shift.valid_from <= day
            and (not shift.valid_to or shift.valid_to >= day)
        )
        return candidates[:1]

    def _compute_schedule_count(self):
        Schedule = self.env["onehr.shift.assignment"]
        for record in self:
            record.schedule_count = Schedule.search_count([("pattern_id", "=", record.id)])

    def action_validate_cycle(self):
        self._validate_pattern()
        return display_notification(_("Pattern cycle is structurally valid."), title=self.display_name, notification_type="success")

    def action_activate(self):
        self._require_manager()
        self._validate_pattern()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        return True

    def action_retire(self):
        self._require_manager()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "retired"})
        return True

    def action_create_new_version(self):
        self._require_manager()
        self.ensure_one()
        new = self.copy({
            "version": self.version + 1,
            "valid_from": fields.Date.context_today(self),
            "valid_to": False,
            "state": "draft",
        })
        return open_record_action(new.display_name, "onehr.shift.pattern", new.id)

    def action_open_schedules(self):
        self.ensure_one()
        return open_records_action(_("Pattern Schedules"), "onehr.shift.assignment", [("pattern_id", "=", self.id)])

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))


class OneHRShiftAssignment(models.Model):
    """Effective employee/assignment shift schedule with optional OneHR Assignment reference."""

    _name = "onehr.shift.assignment"
    _description = "OneHR Employee Shift Schedule"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "valid_from desc, id desc"

    _STATE_CONTEXT = "onehr_shift_assignment_state_controlled"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="restrict", index=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", check_company=True, index=True, tracking=True)
    assignment_ref = fields.Reference(
        selection="_selection_assignment_reference", string="Enterprise Assignment", tracking=True,
        help="Optional soft reference to onehr.assignment when that addon is installed.",
    )
    shift_id = fields.Many2one("onehr.shift", ondelete="restrict", check_company=True, index=True, tracking=True)
    pattern_id = fields.Many2one("onehr.shift.pattern", ondelete="restrict", check_company=True, index=True, tracking=True)
    cycle_offset = fields.Integer(default=0, tracking=True)
    state = fields.Selection(
        [("planned", "Planned"), ("active", "Active"), ("ended", "Ended"), ("cancelled", "Cancelled")],
        required=True, default="planned", index=True, tracking=True,
    )
    current_shift_id = fields.Many2one("onehr.shift", compute="_compute_current_shift", string="Today's Shift")
    exception_ids = fields.One2many("onehr.attendance.exception", "shift_assignment_id", string="Exceptions", readonly=True)
    attendance_ids = fields.One2many("hr.attendance", "onehr_shift_assignment_id", string="Attendance", readonly=True)
    exception_count = fields.Integer(compute="_compute_counts")
    attendance_count = fields.Integer(compute="_compute_counts")

    @api.model
    def _selection_assignment_reference(self):
        return _reference_selection(self.env, "onehr.assignment", _("OneHR Assignment"))

    @api.depends("employee_id", "shift_id", "pattern_id", "valid_from")
    def _compute_name(self):
        for record in self:
            schedule = record.shift_id.display_name or record.pattern_id.display_name or _("Unassigned")
            record.name = _("%s — %s — %s", record.employee_id.name or _("Employee"), schedule, record.valid_from or "")

    @api.depends("shift_id", "pattern_id", "cycle_offset", "valid_from", "valid_to", "state")
    def _compute_current_shift(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.current_shift_id = record._shift_for_date(today)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", "planned") != "planned" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Shift schedules must be created as Planned."))
        records = super().create(vals_list)
        records._validate_schedule_integrity()
        return records

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Schedule state can change only through governed actions."))
        protected = {"company_id", "employee_id", "assignment_ref", "shift_id", "pattern_id", "cycle_offset", "valid_from", "valid_to"}
        if protected & set(values) and any(record.state in {"ended", "cancelled"} for record in self):
            raise AccessError(_("Ended/cancelled schedule history is immutable."))
        result = super().write(values)
        if protected & set(values):
            self._validate_schedule_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_schedule_history(self):
        if any(record.state != "planned" or record.attendance_count or record.exception_count for record in self):
            raise AccessError(_("Only an unused Planned schedule may be deleted."))

    @api.constrains("employee_id", "company_id", "assignment_ref", "shift_id", "pattern_id", "valid_from", "valid_to", "state")
    def _check_schedule_integrity(self):
        self._validate_schedule_integrity()

    def _validate_schedule_integrity(self):
        for record in self:
            if bool(record.shift_id) == bool(record.pattern_id):
                raise ValidationError(_("Choose exactly one Direct Shift or Rotation Pattern."))
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Employee and Shift Schedule must belong to the same company."))
            schedule_owner = record.shift_id or record.pattern_id
            if schedule_owner.company_id != record.company_id:
                raise ValidationError(_("Shift/Pattern and Shift Schedule must belong to the same company."))
            if record.assignment_ref:
                assignment = record.assignment_ref
                if getattr(assignment, "company_id", False) != record.company_id or getattr(assignment, "employee_id", False) != record.employee_id:
                    raise ValidationError(_("Enterprise Assignment reference must belong to the same employee and company."))
                a_from = getattr(assignment, "effective_from", False)
                a_to = getattr(assignment, "effective_to", False)
                if (a_from and record.valid_from < a_from) or (a_to and (not record.valid_to or record.valid_to > a_to)):
                    raise ValidationError(_("Shift Schedule validity must fit inside the referenced enterprise assignment."))
            if record.state != "cancelled":
                domain = [
                    ("id", "!=", record.id), ("employee_id", "=", record.employee_id.id),
                    ("state", "!=", "cancelled"),
                    "|", ("valid_to", "=", False), ("valid_to", ">=", record.valid_from),
                ]
                if record.valid_to:
                    domain.append(("valid_from", "<=", record.valid_to))
                if self.search_count(domain, limit=1):
                    raise ValidationError(_("An employee cannot have conflicting primary Shift Schedule intervals."))

    def _shift_for_date(self, day):
        self.ensure_one()
        if self.state == "cancelled" or day < self.valid_from or self.valid_to and day > self.valid_to:
            return self.env["onehr.shift"]
        if self.shift_id:
            return self.shift_id if self.shift_id.state == "active" and self.shift_id.valid_from <= day and (not self.shift_id.valid_to or self.shift_id.valid_to >= day) else self.env["onehr.shift"]
        return self.pattern_id._shift_for_date(day, self.cycle_offset)

    @api.model
    def resolve_for_employee(self, employee, day):
        """Resolve one effective schedule using normal ACL/rules; no sudo security bypass."""
        return self.search([
            ("employee_id", "=", employee.id),
            ("company_id", "=", employee.company_id.id),
            ("state", "!=", "cancelled"),
            ("valid_from", "<=", day),
            "|", ("valid_to", "=", False), ("valid_to", ">=", day),
        ], order="valid_from desc, id desc", limit=1)

    def _onehr_exclusion_reason_for_date(self, day):
        """Soft hook for future Time Off / Learning owners.

        Return a short reason to suppress a missing-punch exception when the worker
        is legitimately unavailable (approved leave, training, etc.). The base
        Attendance addon owns no leave/training records and therefore returns False.
        """
        self.ensure_one()
        return False

    def _detect_missing_punch_for_date(self, day):
        self.ensure_one()
        day = fields.Date.to_date(day)
        shift = self._shift_for_date(day)
        if not shift or self._onehr_exclusion_reason_for_date(day):
            return self.env["onehr.attendance.exception"]
        attendance = self.env["hr.attendance"].search([
            ("employee_id", "=", self.employee_id.id),
            ("date", "=", day),
        ], limit=1)
        if attendance:
            return self.env["onehr.attendance.exception"]
        Exception = self.env["onehr.attendance.exception"]
        existing = Exception.search([
            ("employee_id", "=", self.employee_id.id),
            ("shift_assignment_id", "=", self.id),
            ("attendance_date", "=", day),
            ("exception_type", "=", "missing_in"),
        ], limit=1)
        if existing:
            return existing
        return Exception.with_context(**{Exception._EVIDENCE_CONTEXT: True}).create({
            "company_id": self.company_id.id,
            "employee_id": self.employee_id.id,
            "shift_assignment_id": self.id,
            "shift_id": shift.id,
            "attendance_date": day,
            "exception_type": "missing_in",
            "severity": "critical",
            "detection_note": _("No canonical attendance was found for an expected working shift."),
        })

    def action_detect_missing_previous_day(self):
        self._require_manager()
        previous_day = fields.Date.context_today(self) - timedelta(days=1)
        created = self.env["onehr.attendance.exception"]
        for schedule in self:
            created |= schedule._detect_missing_punch_for_date(previous_day)
        return display_notification(
            _("Missing-punch review completed for %s. %s exception record(s) are linked/found.", previous_day, len(created)),
            notification_type="success",
        )

    @api.model
    def _cron_detect_missing_punches(self):
        previous_day = fields.Date.context_today(self) - timedelta(days=1)
        schedules = self.search([
            ("state", "in", ["active", "ended"]),
            ("valid_from", "<=", previous_day),
            "|", ("valid_to", "=", False), ("valid_to", ">=", previous_day),
        ])
        for schedule in schedules:
            schedule._detect_missing_punch_for_date(previous_day)
        return True

    def _compute_counts(self):
        Exception = self.env["onehr.attendance.exception"]
        Attendance = self.env["hr.attendance"]
        for record in self:
            record.exception_count = Exception.search_count([("shift_assignment_id", "=", record.id)])
            record.attendance_count = Attendance.search_count([("onehr_shift_assignment_id", "=", record.id)])

    def action_activate(self):
        self._require_manager()
        self._validate_schedule_integrity()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        return True

    def action_end(self):
        self._require_manager()
        today = fields.Date.context_today(self)
        values = {"state": "ended"}
        if not self.valid_to or self.valid_to > today:
            values["valid_to"] = today
        self.with_context(**{self._STATE_CONTEXT: True}).write(values)
        return True

    def action_cancel(self):
        self._require_manager()
        if any(record.state != "planned" for record in self):
            raise UserError(_("Only Planned Shift Schedules may be cancelled."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "cancelled"})
        return True

    def action_preview_today(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        shift = self._shift_for_date(today)
        message = _("Today's resolved shift: %s", shift.display_name) if shift else _("Today resolves to OFF / no active shift.")
        return display_notification(message, title=self.display_name)

    def action_open_employee(self):
        self.ensure_one()
        return open_record_action(self.employee_id.name, "hr.employee", self.employee_id.id)

    def action_open_current_shift(self):
        self.ensure_one()
        shift = self._shift_for_date(fields.Date.context_today(self))
        if not shift:
            return display_notification(_("No active shift resolves for today."), notification_type="warning")
        return open_record_action(shift.display_name, "onehr.shift", shift.id)

    def action_open_exceptions(self):
        self.ensure_one()
        return open_records_action(_("Attendance Exceptions"), "onehr.attendance.exception", [("shift_assignment_id", "=", self.id)])

    def action_open_attendances(self):
        self.ensure_one()
        return open_records_action(_("Attendance"), "hr.attendance", [("onehr_shift_assignment_id", "=", self.id)], view_mode="list,calendar,pivot,graph,form")

    @api.model
    def _cron_refresh_state(self):
        today = fields.Date.context_today(self)
        planned = self.search([("state", "=", "planned"), ("valid_from", "<=", today), "|", ("valid_to", "=", False), ("valid_to", ">=", today)])
        if planned:
            planned.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        expired = self.search([("state", "=", "active"), ("valid_to", "!=", False), ("valid_to", "<", today)])
        if expired:
            expired.with_context(**{self._STATE_CONTEXT: True}).write({"state": "ended"})

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))
