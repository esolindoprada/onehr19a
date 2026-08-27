import math

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action


PROCESSING_STATES = {"draft", "confirmed", "posted"}
LOCKED_PROCESSING_STATES = {"confirmed", "posted"}


def _distance_meters(lat1, lon1, lat2, lon2):
    """Haversine distance used only for configured work-location geofence evidence."""
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    return radius * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class HrAttendance(models.Model):
    """OneHR enrichment of Odoo 19 canonical ``hr.attendance``.

    Odoo continues to own check-in/out validity, worked hours, native device
    metadata and overtime computation. OneHR adds shift resolution, exception
    evidence, import/reconciliation trace and a governed Draft -> Confirmed ->
    Posted business-readiness layer without replacing native overtime semantics.
    """

    _inherit = ["hr.attendance", "mail.activity.mixin"]

    _STATE_CONTEXT = "onehr_attendance_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_attendance_evidence_controlled"
    _RECALC_CONTEXT = "onehr_attendance_recalculation"

    onehr_shift_assignment_id = fields.Many2one(
        "onehr.shift.assignment", string="Shift Schedule", ondelete="restrict",
        index=True, tracking=True,
    )
    onehr_shift_id = fields.Many2one(
        "onehr.shift", string="Resolved Shift", ondelete="restrict",
        index=True, tracking=True,
    )
    onehr_reconciliation_id = fields.Many2one(
        "onehr.attendance.reconciliation", ondelete="restrict", index=True,
        tracking=True, copy=False,
    )
    onehr_source_channel = fields.Selection(
        [
            ("web", "Web / Systray"),
            ("kiosk", "Kiosk"),
            ("mobile", "Mobile"),
            ("fingerprint", "Fingerprint / Device"),
            ("api", "External API"),
            ("manual", "Controlled Manual"),
        ],
        required=True, default="manual", index=True, tracking=True,
    )
    onehr_source_system = fields.Char(index=True, tracking=True)
    onehr_external_reference = fields.Char(index=True, tracking=True)
    onehr_device_reference = fields.Char(index=True, tracking=True)

    onehr_processing_state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("posted", "Posted")],
        required=True, default="draft", index=True, tracking=True,
    )
    onehr_planned_start = fields.Datetime(readonly=True, copy=False, index=True)
    onehr_planned_end = fields.Datetime(readonly=True, copy=False, index=True)
    onehr_late_minutes = fields.Float(readonly=True, copy=False, aggregator="avg")
    onehr_early_leave_minutes = fields.Float(readonly=True, copy=False, aggregator="avg")
    onehr_schedule_variance_minutes = fields.Float(readonly=True, copy=False, aggregator="avg")
    onehr_rounded_worked_hours = fields.Float(
        string="Rounded Worked Hours", readonly=True, copy=False, aggregator="sum",
        help="Policy-rounded worked hours for downstream readiness. Native worked_hours remains untouched.",
    )
    onehr_exception_state = fields.Selection(
        [
            ("normal", "Normal"),
            ("late", "Late"),
            ("early_leave", "Early Leave"),
            ("late_early", "Late + Early Leave"),
            ("off_schedule", "Off Schedule"),
            ("incomplete", "Incomplete Punch"),
        ],
        readonly=True, copy=False, index=True,
    )
    onehr_geofence_status = fields.Selection(
        [("not_configured", "Not Configured"), ("inside", "Inside"),
         ("outside", "Outside"), ("no_coordinate", "No Coordinate")],
        readonly=True, copy=False, index=True,
    )
    onehr_requires_review = fields.Boolean(readonly=True, copy=False, index=True)
    onehr_reconciliation_note = fields.Text(tracking=True)
    onehr_reconciled_at = fields.Datetime(readonly=True, copy=False)
    onehr_reconciled_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    onehr_confirmed_at = fields.Datetime(readonly=True, copy=False)
    onehr_confirmed_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    onehr_posted_at = fields.Datetime(readonly=True, copy=False)
    onehr_posted_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    onehr_exception_ids = fields.One2many("onehr.attendance.exception", "attendance_id", string="OneHR Exceptions", readonly=True)
    onehr_exception_count = fields.Integer(compute="_compute_onehr_exception_count")

    _onehr_external_source_unique = models.Constraint(
        "unique(employee_id, onehr_source_system, onehr_external_reference)",
        "External attendance reference must be unique for an employee and source system.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("onehr_processing_state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("OneHR attendance processing must begin in Draft."))
            if not values.get("onehr_source_channel"):
                values["onehr_source_channel"] = self._onehr_channel_from_native_mode(values.get("in_mode"))
            prepared.append(values)
        records = super().create(prepared)
        records._onehr_refresh_reconciliation(create_exceptions=False)
        return records

    def write(self, values):
        if "onehr_processing_state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("OneHR attendance state can change only through governed actions."))
        evidence_fields = {
            "onehr_planned_start", "onehr_planned_end", "onehr_late_minutes",
            "onehr_early_leave_minutes", "onehr_schedule_variance_minutes", "onehr_rounded_worked_hours",
            "onehr_exception_state", "onehr_geofence_status", "onehr_requires_review",
            "onehr_reconciled_at", "onehr_reconciled_by_id", "onehr_confirmed_at",
            "onehr_confirmed_by_id", "onehr_posted_at", "onehr_posted_by_id",
        }
        if evidence_fields & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("OneHR attendance reconciliation evidence is system-controlled."))

        business_fields = {
            "employee_id", "check_in", "check_out", "onehr_shift_assignment_id", "onehr_shift_id",
            "onehr_source_channel", "onehr_source_system", "onehr_external_reference", "onehr_device_reference",
        }
        if business_fields & set(values) and any(record.onehr_processing_state in LOCKED_PROCESSING_STATES for record in self):
            raise AccessError(_("Confirmed/Posted attendance facts are frozen. Reset to Draft before governed correction."))

        result = super().write(values)
        if business_fields & set(values) and not self.env.context.get(self._RECALC_CONTEXT):
            self._onehr_refresh_reconciliation(create_exceptions=False)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_posted_attendance(self):
        if any(record.onehr_processing_state == "posted" for record in self):
            raise AccessError(_("Posted attendance evidence cannot be deleted. Use a governed correction."))

    @api.model
    def _onehr_channel_from_native_mode(self, mode):
        return {"kiosk": "kiosk", "systray": "web", "manual": "manual", "technical": "api", "auto_check_out": "api"}.get(mode, "manual")

    @api.model
    def onehr_ingest_interval(self, payload):
        """Validated adapter service for kiosk/mobile/device/API integrations.

        The caller retains normal ORM ACL and record-rule enforcement; this method
        deliberately contains no ``sudo()`` security bypass. Retries are idempotent
        when source_system + external_reference are supplied.
        """
        values = dict(payload or {})
        employee_id = values.get("employee_id")
        check_in = fields.Datetime.to_datetime(values.get("check_in"))
        check_out = fields.Datetime.to_datetime(values.get("check_out")) if values.get("check_out") else False
        if not employee_id or not check_in:
            raise ValidationError(_("Attendance ingestion requires employee_id and check_in."))
        employee = self.env["hr.employee"].browse(employee_id).exists()
        if not employee:
            raise ValidationError(_("Attendance ingestion employee does not exist."))
        if check_out and check_out <= check_in:
            raise ValidationError(_("Check Out must be later than Check In."))

        source_system = (values.get("source_system") or "ONEHR").strip().upper()
        external_reference = (values.get("external_reference") or "").strip()
        if external_reference:
            existing = self.search([
                ("employee_id", "=", employee.id),
                ("onehr_source_system", "=", source_system),
                ("onehr_external_reference", "=", external_reference),
            ], limit=1)
            if existing:
                return existing

        channel = values.get("source_channel") or "api"
        native_mode = "kiosk" if channel == "kiosk" else "systray" if channel == "web" else "manual" if channel == "manual" else "technical"
        create_values = {
            "employee_id": employee.id,
            "check_in": check_in,
            "check_out": check_out,
            "in_mode": native_mode,
            "out_mode": native_mode,
            "onehr_source_channel": channel,
            "onehr_source_system": source_system,
            "onehr_external_reference": external_reference or False,
            "onehr_device_reference": values.get("device_reference") or False,
            "onehr_reconciliation_id": values.get("reconciliation_id") or False,
        }
        for field_name in (
            "in_latitude", "in_longitude", "out_latitude", "out_longitude",
            "in_location", "out_location", "in_ip_address", "out_ip_address", "in_browser", "out_browser",
        ):
            if field_name in values:
                create_values[field_name] = values[field_name]
        return self.create(create_values)

    def _onehr_resolve_schedule(self):
        self.ensure_one()
        if not self.employee_id or not self.date:
            return self.env["onehr.shift.assignment"]
        Schedule = self.env["onehr.shift.assignment"]
        return Schedule.resolve_for_employee(self.employee_id, self.date)

    def _onehr_geofence_status_for(self, shift):
        self.ensure_one()
        if not shift or not shift.geofence_radius_m or not shift.work_location_id:
            return "not_configured"
        location = shift.work_location_id
        target_lat = getattr(location, "onehr_latitude", 0.0) or 0.0
        target_lon = getattr(location, "onehr_longitude", 0.0) or 0.0
        if not target_lat and not target_lon:
            return "no_coordinate"
        actual_lat = self.in_latitude or 0.0
        actual_lon = self.in_longitude or 0.0
        if not actual_lat and not actual_lon:
            return "no_coordinate"
        return "inside" if _distance_meters(actual_lat, actual_lon, target_lat, target_lon) <= shift.geofence_radius_m else "outside"

    def _onehr_analysis_values(self):
        self.ensure_one()
        schedule = self.onehr_shift_assignment_id or self._onehr_resolve_schedule()
        shift = self.onehr_shift_id or (
            schedule._shift_for_date(self.date)
            if schedule
            else self.env["onehr.shift"].resolve_for_employee_date(self.employee_id, self.date)
        )
        values = {
            "onehr_shift_assignment_id": schedule.id if schedule else False,
            "onehr_shift_id": shift.id if shift else False,
            "onehr_planned_start": False,
            "onehr_planned_end": False,
            "onehr_late_minutes": 0.0,
            "onehr_early_leave_minutes": 0.0,
            "onehr_schedule_variance_minutes": 0.0,
            "onehr_rounded_worked_hours": 0.0,
            "onehr_exception_state": "normal",
            "onehr_geofence_status": "not_configured",
            "onehr_requires_review": False,
            "onehr_reconciled_at": fields.Datetime.now(),
            "onehr_reconciled_by_id": self.env.user.id,
        }
        if not self.check_out:
            values.update({"onehr_exception_state": "incomplete", "onehr_requires_review": True})
            return values
        if not shift:
            values.update({"onehr_exception_state": "off_schedule", "onehr_requires_review": True})
            return values
        planned_start, planned_end = shift._planned_interval_utc(self.date)
        if not planned_start:
            values.update({"onehr_exception_state": "off_schedule", "onehr_requires_review": True})
            return values
        late_minutes = max(0.0, (self.check_in - planned_start).total_seconds() / 60.0 - shift.late_grace_minutes)
        early_minutes = max(0.0, (planned_end - self.check_out).total_seconds() / 60.0 - shift.early_leave_grace_minutes)
        actual_minutes = (self.check_out - self.check_in).total_seconds() / 60.0
        planned_minutes = (planned_end - planned_start).total_seconds() / 60.0
        rounding = max(1, int(shift.rounding_minutes or "1"))
        rounded_minutes = round(actual_minutes / rounding) * rounding
        if late_minutes and early_minutes:
            exception_state = "late_early"
        elif late_minutes:
            exception_state = "late"
        elif early_minutes:
            exception_state = "early_leave"
        else:
            exception_state = "normal"
        geofence = self._onehr_geofence_status_for(shift)
        values.update({
            "onehr_planned_start": planned_start,
            "onehr_planned_end": planned_end,
            "onehr_late_minutes": round(late_minutes, 2),
            "onehr_early_leave_minutes": round(early_minutes, 2),
            "onehr_schedule_variance_minutes": round(actual_minutes - planned_minutes, 2),
            "onehr_rounded_worked_hours": round(rounded_minutes / 60.0, 4),
            "onehr_exception_state": exception_state,
            "onehr_geofence_status": geofence,
            "onehr_requires_review": exception_state != "normal" or geofence == "outside",
        })
        return values

    def _onehr_refresh_reconciliation(self, create_exceptions=False):
        for attendance in self:
            values = attendance._onehr_analysis_values()
            super(HrAttendance, attendance.with_context(**{
                attendance._RECALC_CONTEXT: True,
                attendance._EVIDENCE_CONTEXT: True,
            })).write(values)
            if create_exceptions:
                attendance._onehr_sync_exception_evidence()
        return True

    def _onehr_sync_exception_evidence(self):
        self.ensure_one()
        Exception = self.env["onehr.attendance.exception"]
        desired = []
        if self.onehr_exception_state in {"late", "late_early"}:
            desired.append(("late", self.onehr_late_minutes, _("Arrival exceeded the configured late grace period.")))
        if self.onehr_exception_state in {"early_leave", "late_early"}:
            desired.append(("early_leave", self.onehr_early_leave_minutes, _("Departure preceded the planned end beyond the grace period.")))
        if self.onehr_exception_state == "off_schedule":
            desired.append(("off_schedule", 0.0, _("No active shift resolved for this attendance date.")))
        if self.onehr_exception_state == "incomplete":
            desired.append(("missing_out", 0.0, _("Attendance has no check-out.")))
        if self.onehr_geofence_status == "outside":
            desired.append(("geofence", 0.0, _("Check-in coordinates are outside the configured shift work-location radius.")))
        for exception_type, minutes, note in desired:
            existing = Exception.search([
                ("attendance_id", "=", self.id),
                ("exception_type", "=", exception_type),
                ("state", "in", ["open", "under_review", "resolved", "waived"]),
            ], limit=1)
            if not existing:
                Exception.with_context(**{Exception._EVIDENCE_CONTEXT: True}).create({
                    "company_id": self.employee_id.company_id.id,
                    "employee_id": self.employee_id.id,
                    "attendance_id": self.id,
                    "shift_assignment_id": self.onehr_shift_assignment_id.id or False,
                    "shift_id": self.onehr_shift_id.id or False,
                    "reconciliation_id": self.onehr_reconciliation_id.id or False,
                    "attendance_date": self.date,
                    "exception_type": exception_type,
                    "severity": "warning" if exception_type not in {"missing_out", "geofence"} else "critical",
                    "variance_minutes": minutes,
                    "detection_note": note,
                })

    def _compute_onehr_exception_count(self):
        Exception = self.env["onehr.attendance.exception"]
        for attendance in self:
            attendance.onehr_exception_count = Exception.search_count([("attendance_id", "=", attendance.id)])

    def action_onehr_recalculate(self):
        self._require_officer()
        if any(record.onehr_processing_state != "draft" for record in self):
            raise UserError(_("Reset attendance to Draft before recalculation."))
        self._onehr_refresh_reconciliation(create_exceptions=False)
        return display_notification(_("Shift and exception analysis recalculated."), notification_type="success")

    def action_onehr_confirm(self):
        self._require_officer()
        for attendance in self:
            if attendance.onehr_processing_state != "draft":
                raise UserError(_("Only Draft attendance may be confirmed."))
            if not attendance.check_out:
                raise UserError(_("Check Out is required before OneHR confirmation."))
        self._onehr_refresh_reconciliation(create_exceptions=True)
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "onehr_processing_state": "confirmed",
            "onehr_confirmed_at": fields.Datetime.now(),
            "onehr_confirmed_by_id": self.env.user.id,
        })
        return True

    def action_onehr_post(self):
        self._require_manager()
        for attendance in self:
            if attendance.onehr_processing_state != "confirmed":
                raise UserError(_("Only Confirmed attendance may be Posted."))
            if attendance.overtime_status == "to_approve":
                raise UserError(_("Resolve native Odoo overtime approval before posting attendance for downstream payroll readiness."))
            if attendance.onehr_exception_ids.filtered(lambda exception: exception.state in {"open", "under_review"} and exception.severity == "critical"):
                raise UserError(_("Resolve or waive critical attendance exceptions before posting."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "onehr_processing_state": "posted",
            "onehr_posted_at": fields.Datetime.now(),
            "onehr_posted_by_id": self.env.user.id,
        })
        return True

    def action_onehr_reset_draft(self):
        self._require_manager()
        if any(record.onehr_processing_state == "posted" for record in self):
            raise UserError(_("Posted attendance requires a governed correction/reconciliation; it cannot simply be reset."))
        if any(record.onehr_processing_state != "confirmed" for record in self):
            raise UserError(_("Only Confirmed attendance may be reset to Draft."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"onehr_processing_state": "draft"})
        return True

    def action_onehr_schedule_review(self):
        self._require_officer()
        for attendance in self:
            attendance_manager = getattr(attendance.employee_id, "attendance_manager_id", False)
            manager_user = attendance_manager or attendance.employee_id.parent_id.user_id or self.env.user
            attendance.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=manager_user.id,
                summary=_("Review attendance exception"),
                note=attendance.onehr_reconciliation_note or _("Review the OneHR attendance reconciliation and exception evidence."),
            )
        return True

    def action_onehr_open_employee(self):
        self.ensure_one()
        return open_record_action(self.employee_id.name, "hr.employee", self.employee_id.id)

    def action_onehr_open_shift(self):
        self.ensure_one()
        if not self.onehr_shift_id:
            return display_notification(_("No resolved shift is linked to this attendance."), notification_type="warning")
        return open_record_action(self.onehr_shift_id.display_name, "onehr.shift", self.onehr_shift_id.id)

    def action_onehr_open_reconciliation(self):
        self.ensure_one()
        if not self.onehr_reconciliation_id:
            return display_notification(_("This attendance was not created from a OneHR reconciliation batch."), notification_type="info")
        return open_record_action(self.onehr_reconciliation_id.display_name, "onehr.attendance.reconciliation", self.onehr_reconciliation_id.id)

    def action_onehr_open_exceptions(self):
        self.ensure_one()
        return open_records_action(_("Attendance Exceptions"), "onehr.attendance.exception", [("attendance_id", "=", self.id)])

    def _require_officer(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_officer"):
            raise AccessError(_("OneHR Attendance Officer authority is required."))

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))
