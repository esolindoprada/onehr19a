from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification
from .security_helpers import GROUP_KIOSK_ADMIN, require_kiosk_admin, require_kiosk_operator


SYNC_STATES = [
    ("queued", "Queued"),
    ("processing", "Processing"),
    ("synced", "Synced"),
    ("failed", "Failed"),
    ("blocked", "Blocked"),
    ("dead_letter", "Dead Letter"),
]


class OneHRKioskLog(models.Model):
    """Durable kiosk event evidence and server-side retry queue.

    The approved product baseline defines only ``onehr.kiosk.device`` and
    ``onehr.kiosk.log``.  Queue state therefore lives on this event evidence
    instead of inventing another persistent queue model.
    """

    _name = "onehr.kiosk.log"
    _description = "OneHR Kiosk Activity & Sync Log"
    _inherit = ["onehr.mixin.audit"]
    _order = "event_at desc, id desc"
    _rec_name = "name"

    name = fields.Char(required=True, default="New", copy=False, readonly=True, index=True)
    device_id = fields.Many2one(
        "onehr.kiosk.device",
        required=True,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    employee_name = fields.Char(readonly=True, copy=False, index=True)
    employee_number = fields.Char(readonly=True, copy=False, index=True)

    event_type = fields.Selection(
        [
            ("punch", "Attendance Punch"),
            ("timeoff", "Quick Time Off"),
            ("heartbeat", "Heartbeat"),
            ("system", "System"),
        ],
        required=True,
        default="punch",
        index=True,
        tracking=True,
    )
    punch_mode = fields.Selection(
        [("check_in", "Check In"), ("check_out", "Check Out"), ("auto", "Auto Toggle")],
        default="auto",
        tracking=True,
    )
    credential_type = fields.Selection(
        [
            ("qr", "QR / Barcode"),
            ("nfc", "NFC"),
            ("manual", "Manual Identifier"),
            ("face", "External Face Match"),
            ("external", "External Adapter"),
        ],
        required=True,
        default="qr",
        tracking=True,
        help="Credential channel only. Raw QR/NFC values and biometric material are not persisted.",
    )

    client_event_id = fields.Char(
        required=True,
        index=True,
        copy=False,
        readonly=True,
        help="Client-generated idempotency key, unique per device.",
    )
    event_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    event_date = fields.Date(compute="_compute_event_date", store=True, index=True)
    received_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    offline_event = fields.Boolean(default=False, readonly=True, index=True)

    latitude = fields.Float(digits=(10, 7), readonly=True)
    longitude = fields.Float(digits=(10, 7), readonly=True)
    location_accuracy_m = fields.Float(readonly=True)
    geofence_status = fields.Selection(
        [
            ("not_available", "Not Available"),
            ("not_required", "Not Required"),
            ("inside", "Inside"),
            ("outside_warning", "Outside — Warning"),
            ("blocked", "Blocked"),
        ],
        default="not_available",
        required=True,
        readonly=True,
        index=True,
    )

    sync_state = fields.Selection(
        SYNC_STATES,
        required=True,
        default="queued",
        readonly=True,
        index=True,
        tracking=True,
    )
    attempt_count = fields.Integer(default=0, readonly=True, copy=False)
    last_attempt_at = fields.Datetime(readonly=True, copy=False)
    next_retry_at = fields.Datetime(readonly=True, copy=False, index=True)
    synced_at = fields.Datetime(readonly=True, copy=False, index=True)
    latency_ms = fields.Float(readonly=True, copy=False, aggregator="avg")

    attendance_id = fields.Many2one(
        "hr.attendance",
        readonly=True,
        copy=False,
        ondelete="set null",
        index=True,
    )

    # Soft Time Off bridge: no Many2one dependency to a model that may not exist.
    target_model = fields.Char(readonly=True, copy=False)
    target_res_id = fields.Integer(readonly=True, copy=False)
    target_label = fields.Char(readonly=True, copy=False)

    leave_type_code = fields.Char(readonly=True, copy=False, index=True)
    leave_date_from = fields.Date(readonly=True, copy=False)
    leave_date_to = fields.Date(readonly=True, copy=False)
    leave_reason = fields.Char(readonly=True, copy=False)

    request_summary = fields.Text(
        readonly=True,
        copy=False,
        help="Sanitized operational metadata. It intentionally excludes raw QR/NFC credentials.",
    )
    payload_hash = fields.Char(readonly=True, copy=False, index=True)
    error_code = fields.Char(readonly=True, copy=False, index=True)
    error_message = fields.Text(readonly=True, copy=False)
    operator_note = fields.Text(tracking=True)

    _device_client_event_unique = models.Constraint(
        "unique(device_id, client_event_id)",
        "Client event id must be unique for each kiosk device.",
    )

    @api.depends("event_at")
    def _compute_event_date(self):
        for log in self:
            log.event_date = fields.Date.to_date(log.event_at) if log.event_at else False

    @api.model_create_multi
    def create(self, vals_list):
        require_kiosk_operator(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            device = self.env["onehr.kiosk.device"].browse(vals.get("device_id")).exists()
            if not device:
                raise ValidationError(_("A valid kiosk device is required."))
            # Record rules and the explicit service-user boundary are both enforced.
            if (
                self.env.user != device.service_user_id
                and not self.env.user.has_group(GROUP_KIOSK_ADMIN)
            ):
                raise AccessError(_("You cannot create kiosk evidence for another service user's device."))
            employee = self.env["hr.employee"].browse(vals.get("employee_id")).exists()
            if employee and employee.company_id != device.company_id:
                raise ValidationError(_("Kiosk employee and device must belong to the same company."))
            vals["company_id"] = device.company_id.id
            vals["employee_name"] = employee.name if employee else False
            vals["employee_number"] = employee.onehr_employee_number if employee else False
            vals["name"] = self.env["ir.sequence"].next_by_code("onehr.kiosk.log") or "KLOG"
            vals["sync_state"] = "queued"
            vals["attempt_count"] = 0
            vals["received_at"] = fields.Datetime.now()
            # Target/result evidence cannot be injected through normal create.
            for key in (
                "attendance_id",
                "target_model",
                "target_res_id",
                "target_label",
                "last_attempt_at",
                "next_retry_at",
                "synced_at",
                "latency_ms",
                "error_code",
                "error_message",
            ):
                vals.pop(key, None)
            prepared.append(vals)
        return super().create(prepared)

    def write(self, values):
        require_kiosk_operator(self)
        protected = {
            "name",
            "device_id",
            "company_id",
            "employee_id",
            "employee_name",
            "employee_number",
            "event_type",
            "punch_mode",
            "credential_type",
            "client_event_id",
            "event_at",
            "received_at",
            "offline_event",
            "latitude",
            "longitude",
            "location_accuracy_m",
            "geofence_status",
            "sync_state",
            "attempt_count",
            "last_attempt_at",
            "next_retry_at",
            "synced_at",
            "latency_ms",
            "attendance_id",
            "target_model",
            "target_res_id",
            "target_label",
            "leave_type_code",
            "leave_date_from",
            "leave_date_to",
            "leave_reason",
            "request_summary",
            "payload_hash",
            "error_code",
            "error_message",
        }
        if protected.intersection(values):
            raise AccessError(
                _("Kiosk transaction/sync evidence is immutable through ordinary write operations.")
            )
        return super().write(values)

    def _write_governed(self, values):
        """Private evidence writer used only by bounded server-side orchestration."""
        return super(OneHRKioskLog, self).write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_kiosk_evidence(self):
        if any(log.sync_state != "queued" or log.attempt_count for log in self):
            raise AccessError(
                _("Processed kiosk evidence cannot be deleted. Use retention governance instead.")
            )

    def kiosk_result(self):
        self.ensure_one()
        return {
            "event_id": self.client_event_id,
            "log_id": self.id,
            "log_no": self.name,
            "state": self.sync_state,
            "message": self.error_message or False,
            "attendance_id": self.attendance_id.id if self.attendance_id else False,
            "target": (
                {
                    "model": self.target_model,
                    "id": self.target_res_id,
                    "label": self.target_label,
                }
                if self.target_model and self.target_res_id
                else False
            ),
        }

    def _record_failure(self, exception):
        self.ensure_one()
        max_attempts = self.device_id.max_sync_attempts
        attempts = self.attempt_count
        terminal = attempts >= max_attempts
        delay_minutes = min(60, 2 ** min(attempts, 6))
        state = "dead_letter" if terminal else "failed"
        self._write_governed(
            {
                "sync_state": state,
                "error_code": type(exception).__name__.upper()[:80],
                "error_message": str(exception)[:2000],
                "next_retry_at": (
                    False
                    if terminal
                    else fields.Datetime.now() + timedelta(minutes=delay_minutes)
                ),
            }
        )

    def _sync_one(self):
        """Process one event under the device service user, never under a business sudo bypass."""
        self.ensure_one()
        if self.sync_state in ("synced", "blocked"):
            return self
        if self.device_id.state != "active":
            self._record_failure(UserError(_("Kiosk device is not Active.")))
            return self

        attempt = self.attempt_count + 1
        self._write_governed(
            {
                "sync_state": "processing",
                "attempt_count": attempt,
                "last_attempt_at": fields.Datetime.now(),
                "next_retry_at": False,
                "error_code": False,
                "error_message": False,
            }
        )

        target_values = {}
        try:
            with self.env.cr.savepoint():
                if self.event_type == "punch":
                    attendance = self.env["hr.attendance"].onehr_kiosk_apply_punch(
                        self.device_id, self
                    )
                    target_values["attendance_id"] = attendance.id
                elif self.event_type == "timeoff":
                    target_values.update(self._sync_timeoff_request())
                elif self.event_type in ("heartbeat", "system"):
                    target_values = {}
                else:
                    raise ValidationError(_("Unsupported kiosk event type: %s", self.event_type))
        except Exception as exc:  # queue captures operational failures for retry/dead-letter review
            self._record_failure(exc)
            return self

        now = fields.Datetime.now()
        latency_ms = max(
            ((now - self.received_at).total_seconds() * 1000.0) if self.received_at else 0.0,
            0.0,
        )
        target_values.update(
            {
                "sync_state": "synced",
                "synced_at": now,
                "latency_ms": latency_ms,
                "next_retry_at": False,
                "error_code": False,
                "error_message": False,
            }
        )
        self._write_governed(target_values)
        self.device_id._write_governed({"last_sync_at": now, "last_seen_at": now})
        return self

    def _sync_timeoff_request(self):
        self.ensure_one()
        if (
            "onehr.leave.request" not in self.env
            or "onehr.leave.type" not in self.env
            or "onehr.leave.allocation" not in self.env
        ):
            raise UserError(_("OneHR Time Off is not installed; quick request remains queued/failed."))
        employee = self.employee_id
        employee_user = employee.user_id
        if not employee_user:
            raise AccessError(_("Employee has no linked Odoo self-service user for Time Off."))
        if not employee_user.has_group("onehr_timeoff.group_onehr_timeoff_user"):
            raise AccessError(_("Employee does not have OneHR Time Off self-service authority."))
        if not self.leave_type_code or not self.leave_date_from:
            raise ValidationError(_("Quick Time Off requires leave type code and start date."))
        date_to = self.leave_date_to or self.leave_date_from
        today = self.leave_date_from

        LeaveType = self.env["onehr.leave.type"].with_user(employee_user)
        leave_type = LeaveType.search(
            [
                ("company_id", "=", self.company_id.id),
                ("code", "=", self.leave_type_code),
                ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", today),
            ],
            limit=1,
        )
        if not leave_type:
            raise ValidationError(_("No active leave policy matches code %s.", self.leave_type_code))

        Request = self.env["onehr.leave.request"].with_user(employee_user)
        request = Request.create(
            {
                "employee_id": employee.id,
                "leave_type_id": leave_type.id,
                "date_from": self.leave_date_from,
                "date_to": date_to,
                "reason": self.leave_reason or _("Submitted from OneHR Kiosk"),
            }
        )
        request.action_submit_for_approval()
        return {
            "target_model": "onehr.leave.request",
            "target_res_id": request.id,
            "target_label": request.display_name,
        }

    def action_retry_sync(self):
        for log in self:
            require_kiosk_operator(log)
            if log.sync_state not in ("queued", "failed", "dead_letter"):
                raise UserError(_("Only Queued, Failed or Dead Letter events can be retried."))
            if log.sync_state == "dead_letter":
                require_kiosk_admin(log)
            log.with_user(log.device_id.service_user_id)._sync_one()
        return display_notification(_("Kiosk Sync"), _("Selected kiosk event(s) were processed."))

    def action_mark_dead_letter(self):
        for log in self:
            require_kiosk_admin(log)
            if log.sync_state == "synced":
                raise UserError(_("A synchronized event cannot be moved to Dead Letter."))
            log._write_governed(
                {
                    "sync_state": "dead_letter",
                    "next_retry_at": False,
                    "error_code": log.error_code or "ADMIN_DEAD_LETTER",
                    "error_message": log.error_message
                    or _("Moved to Dead Letter by Kiosk Administrator."),
                }
            )
        return True

    def action_open_device(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Kiosk Device"),
            "res_model": "onehr.kiosk.device",
            "res_id": self.device_id.id,
            "view_mode": "form",
        }

    def action_open_attendance(self):
        self.ensure_one()
        if not self.attendance_id:
            raise UserError(_("This kiosk event has no canonical attendance record."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendance"),
            "res_model": "hr.attendance",
            "res_id": self.attendance_id.id,
            "view_mode": "form",
        }

    def action_open_target(self):
        self.ensure_one()
        if not self.target_model or not self.target_res_id:
            raise UserError(_("This kiosk event has no downstream target record."))
        if self.target_model not in self.env:
            raise UserError(_("The downstream addon/model is not currently installed."))
        return {
            "type": "ir.actions.act_window",
            "name": self.target_label or _("Kiosk Target"),
            "res_model": self.target_model,
            "res_id": self.target_res_id,
            "view_mode": "form",
        }

    @api.model
    def _cron_retry_due(self):
        """Root cron discovers queue rows; each business operation is re-bound to its service user."""
        due = self.search(
            [
                ("sync_state", "in", ["queued", "failed"]),
                "|",
                ("next_retry_at", "=", False),
                ("next_retry_at", "<=", fields.Datetime.now()),
                ("device_id.state", "=", "active"),
            ],
            order="event_at, id",
            limit=500,
        )
        for log in due:
            service_user = log.device_id.service_user_id
            if service_user:
                log.with_user(service_user)._sync_one()
        return True
