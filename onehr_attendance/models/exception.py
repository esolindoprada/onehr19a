from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action


class OneHRAttendanceException(models.Model):
    """Immutable ED3 evidence for attendance anomalies and their disposition."""

    _name = "onehr.attendance.exception"
    _description = "OneHR Attendance Exception"
    _inherit = ["onehr.mixin.audit"]
    _order = "detected_at desc, id desc"

    _STATE_CONTEXT = "onehr_attendance_exception_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_attendance_exception_evidence_controlled"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True, tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="restrict", check_company=True,
        index=True, tracking=True,
    )
    attendance_id = fields.Many2one(
        "hr.attendance", ondelete="restrict", index=True, tracking=True,
        help="Optional because missing-punch exceptions may exist before a canonical attendance row exists.",
    )
    shift_assignment_id = fields.Many2one(
        "onehr.shift.assignment", ondelete="restrict", check_company=True,
        index=True, tracking=True,
    )
    shift_id = fields.Many2one("onehr.shift", ondelete="restrict", check_company=True, index=True, tracking=True)
    reconciliation_id = fields.Many2one("onehr.attendance.reconciliation", ondelete="restrict", index=True, tracking=True)
    attendance_date = fields.Date(required=True, index=True, tracking=True)
    exception_type = fields.Selection(
        [
            ("late", "Late Arrival"),
            ("early_leave", "Early Leave"),
            ("missing_in", "Missing Check-In"),
            ("missing_out", "Missing Check-Out"),
            ("off_schedule", "Off Schedule"),
            ("overlap", "Overlapping Attendance"),
            ("geofence", "Outside Geofence"),
            ("device_mismatch", "Device / Source Mismatch"),
            ("other", "Other"),
        ],
        required=True, index=True, tracking=True,
    )
    severity = fields.Selection(
        [("info", "Information"), ("warning", "Warning"), ("critical", "Critical")],
        required=True, default="warning", index=True, tracking=True,
    )
    variance_minutes = fields.Float(default=0.0, tracking=True)
    detected_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    detection_note = fields.Text(readonly=True)
    state = fields.Selection(
        [("open", "Open"), ("under_review", "Under Review"), ("resolved", "Resolved"), ("waived", "Waived")],
        required=True, default="open", index=True, tracking=True,
    )
    resolution_reason = fields.Text(tracking=True)
    resolved_at = fields.Datetime(readonly=True, copy=False)
    resolved_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")

    @api.depends("employee_id", "attendance_date", "exception_type")
    def _compute_name(self):
        labels = dict(self._fields["exception_type"].selection)
        for record in self:
            record.name = _(
                "%s — %s — %s",
                record.employee_id.name or _("Employee"),
                labels.get(record.exception_type, record.exception_type or _("Exception")),
                record.attendance_date or "",
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Attendance Exceptions are evidence records and may be created only by governed detection/reconciliation services."))
        records = super().create(vals_list)
        records._validate_exception_integrity()
        return records

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Exception state can change only through governed actions."))
        evidence = {
            "company_id", "employee_id", "attendance_id", "shift_assignment_id", "shift_id",
            "reconciliation_id", "attendance_date", "exception_type", "severity", "variance_minutes",
            "detected_at", "detection_note", "resolved_at", "resolved_by_id",
        }
        if evidence & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Detected attendance-exception evidence is immutable."))
        if "resolution_reason" in values and any(record.state in {"resolved", "waived"} for record in self):
            raise AccessError(_("Final attendance-exception resolution evidence is immutable."))
        result = super().write(values)
        if evidence & set(values):
            self._validate_exception_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_exception_evidence(self):
        raise AccessError(_("Attendance Exception evidence is retained. Resolve or waive it instead of deleting it."))

    @api.constrains("company_id", "employee_id", "attendance_id", "shift_assignment_id", "shift_id", "attendance_date")
    def _check_integrity(self):
        self._validate_exception_integrity()

    def _validate_exception_integrity(self):
        for record in self:
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Exception employee and company must match."))
            if record.attendance_id and record.attendance_id.employee_id != record.employee_id:
                raise ValidationError(_("Exception attendance must belong to the same employee."))
            if record.shift_assignment_id and record.shift_assignment_id.employee_id != record.employee_id:
                raise ValidationError(_("Exception shift schedule must belong to the same employee."))
            if record.shift_id and record.shift_id.company_id != record.company_id:
                raise ValidationError(_("Exception shift must belong to the same company."))

    def action_start_review(self):
        self._require_officer()
        if any(record.state != "open" for record in self):
            raise UserError(_("Only Open exceptions can enter review."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "under_review"})
        return True

    def action_resolve(self):
        self._require_officer()
        if any(record.state not in {"open", "under_review"} for record in self):
            raise UserError(_("Only Open/Under Review exceptions can be resolved."))
        if any(not record.resolution_reason for record in self):
            raise UserError(_("A resolution reason is required before resolving an attendance exception."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "resolved",
            "resolved_at": fields.Datetime.now(),
            "resolved_by_id": self.env.user.id,
        })
        return True

    def action_waive(self):
        self._require_manager()
        if any(record.state not in {"open", "under_review"} for record in self):
            raise UserError(_("Only Open/Under Review exceptions can be waived."))
        if any(not record.resolution_reason for record in self):
            raise UserError(_("A waiver reason is required."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "waived",
            "resolved_at": fields.Datetime.now(),
            "resolved_by_id": self.env.user.id,
        })
        return True

    def action_open_attendance(self):
        self.ensure_one()
        if not self.attendance_id:
            raise UserError(_("This exception is not linked to a canonical attendance row."))
        return open_record_action(self.attendance_id.display_name, "hr.attendance", self.attendance_id.id)

    def action_open_employee(self):
        self.ensure_one()
        return open_record_action(self.employee_id.name, "hr.employee", self.employee_id.id)

    def _require_officer(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_officer"):
            raise AccessError(_("OneHR Attendance Officer authority is required."))

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))
