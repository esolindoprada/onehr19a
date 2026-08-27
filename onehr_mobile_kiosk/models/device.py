import hashlib
import hmac
import math
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_records_action
from .security_helpers import GROUP_KIOSK_ADMIN, require_kiosk_admin, require_kiosk_operator


DEVICE_STATES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("suspended", "Suspended"),
    ("retired", "Retired"),
]


class OneHRKioskDevice(models.Model):
    """Governed kiosk/mobile endpoint.

    Raw device tokens are never stored.  A dedicated authenticated Odoo service
    user supplies normal ACL/record-rule context, while the device token provides
    a second device-specific proof at the application boundary.
    """

    _name = "onehr.kiosk.device"
    _description = "OneHR Kiosk Device"
    _inherit = ["onehr.mixin.audit"]
    _order = "company_id, name, id"

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(
        required=True,
        default="New",
        copy=False,
        tracking=True,
        index=True,
        help="Stable device identifier used in kiosk URLs and integration evidence.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    state = fields.Selection(DEVICE_STATES, required=True, default="draft", tracking=True, index=True)
    active = fields.Boolean(default=True)

    device_kind = fields.Selection(
        [
            ("shared_kiosk", "Shared Kiosk"),
            ("mobile", "Managed Mobile"),
            ("tablet", "Managed Tablet"),
            ("terminal", "Attendance Terminal"),
            ("third_party", "Third-Party Device"),
        ],
        required=True,
        default="shared_kiosk",
        tracking=True,
    )
    platform = fields.Selection(
        [
            ("web", "Web / PWA"),
            ("android", "Android"),
            ("ios", "iOS"),
            ("windows", "Windows"),
            ("linux", "Linux"),
            ("other", "Other"),
        ],
        default="web",
        required=True,
        tracking=True,
    )
    work_location_id = fields.Many2one(
        "hr.work.location",
        string="Work Location",
        index=True,
        tracking=True,
        check_company=True,
    )
    service_user_id = fields.Many2one(
        "res.users",
        string="Kiosk Service User",
        required=True,
        index=True,
        tracking=True,
        domain="[('share', '=', False)]",
        help="Dedicated authenticated user for this device. It must have Kiosk Operator permission.",
    )

    token_hash = fields.Char(
        string="Device Token Hash",
        readonly=True,
        copy=False,
        groups="onehr_mobile_kiosk.group_onehr_kiosk_admin",
    )
    token_last4 = fields.Char(
        string="Token Last 4",
        readonly=True,
        copy=False,
        groups="onehr_mobile_kiosk.group_onehr_kiosk_admin",
    )
    token_issued_at = fields.Datetime(
        readonly=True, copy=False, groups="onehr_mobile_kiosk.group_onehr_kiosk_admin"
    )
    token_expires_at = fields.Datetime(
        readonly=True, copy=False, groups="onehr_mobile_kiosk.group_onehr_kiosk_admin"
    )
    token_rotated_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_mobile_kiosk.group_onehr_kiosk_admin",
    )
    token_validity_days = fields.Integer(
        default=365,
        required=True,
        tracking=True,
        help="Token lifetime. Rotation immediately supersedes the previous token.",
    )

    allow_qr = fields.Boolean(string="Allow QR / Barcode", default=True, tracking=True)
    allow_nfc = fields.Boolean(string="Allow NFC", default=True, tracking=True)
    face_ready = fields.Boolean(
        string="Face-Ready",
        default=False,
        tracking=True,
        help="Capability flag only. This addon stores no face templates, embeddings or biometric images.",
    )
    quick_timeoff_enabled = fields.Boolean(
        string="Quick Time Off",
        default=True,
        tracking=True,
        help="Available only when OneHR Time Off is installed and the employee has self-service authority.",
    )

    geolocation_required = fields.Boolean(default=False, tracking=True)
    geofence_policy = fields.Selection(
        [("ignore", "Ignore"), ("warn", "Warn"), ("block", "Block")],
        required=True,
        default="warn",
        tracking=True,
    )
    geofence_radius_m = fields.Integer(
        string="Device Geofence Radius (m)",
        default=250,
        tracking=True,
    )

    offline_queue_enabled = fields.Boolean(default=True, tracking=True)
    sync_batch_size = fields.Integer(default=25, required=True, tracking=True)
    max_sync_attempts = fields.Integer(default=5, required=True, tracking=True)

    last_seen_at = fields.Datetime(readonly=True, copy=False)
    last_sync_at = fields.Datetime(readonly=True, copy=False)
    client_version = fields.Char(readonly=True, copy=False)

    log_ids = fields.One2many("onehr.kiosk.log", "device_id", string="Activity & Sync Evidence")
    log_count = fields.Integer(compute="_compute_operational_metrics", store=True)
    queued_count = fields.Integer(compute="_compute_operational_metrics", store=True)
    error_count = fields.Integer(compute="_compute_operational_metrics", store=True)
    average_latency_ms = fields.Float(compute="_compute_operational_metrics", store=True, digits=(16, 2))

    note = fields.Text(string="Internal Notes", tracking=True)

    _code_company_unique = models.Constraint(
        "unique(code, company_id)",
        "Kiosk device code must be unique within a company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_kiosk_admin(self)
        prepared = []
        sequence = self.env["ir.sequence"]
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code", "New") == "New":
                vals["code"] = sequence.next_by_code("onehr.kiosk.device") or "KIOSK"
            vals["code"] = (vals.get("code") or "").strip().upper()
            # Token evidence is system-controlled and cannot be seeded through ORM create.
            for key in (
                "token_hash",
                "token_last4",
                "token_issued_at",
                "token_expires_at",
                "token_rotated_by_id",
                "last_seen_at",
                "last_sync_at",
                "client_version",
            ):
                vals.pop(key, None)
            vals["state"] = "draft"
            prepared.append(vals)
        records = super().create(prepared)
        records._check_configuration_integrity()
        return records

    def write(self, values):
        require_kiosk_admin(self)
        protected = {
            "state",
            "token_hash",
            "token_last4",
            "token_issued_at",
            "token_expires_at",
            "token_rotated_by_id",
            "last_seen_at",
            "last_sync_at",
            "client_version",
        }
        if protected.intersection(values):
            raise AccessError(
                _("Device lifecycle and token/runtime evidence can change only through governed actions.")
            )
        if any(record.state == "retired" for record in self) and set(values) - {"active", "note"}:
            raise AccessError(_("Retired kiosk devices are historical records and cannot be reconfigured."))
        result = super().write(values)
        self._check_configuration_integrity()
        return result

    def _write_governed(self, values):
        """Private server-side transition writer; leading underscore blocks normal RPC."""
        return super(OneHRKioskDevice, self).write(values)

    @api.constrains(
        "service_user_id",
        "company_id",
        "token_validity_days",
        "sync_batch_size",
        "max_sync_attempts",
        "geofence_radius_m",
    )
    def _check_configuration_integrity(self):
        for device in self:
            if device.token_validity_days <= 0:
                raise ValidationError(_("Token validity must be greater than zero days."))
            if device.sync_batch_size <= 0 or device.sync_batch_size > 500:
                raise ValidationError(_("Sync batch size must be between 1 and 500."))
            if device.max_sync_attempts <= 0 or device.max_sync_attempts > 20:
                raise ValidationError(_("Maximum sync attempts must be between 1 and 20."))
            if device.geofence_radius_m < 0:
                raise ValidationError(_("Geofence radius cannot be negative."))
            if device.company_id not in device.service_user_id.company_ids:
                raise ValidationError(
                    _("The kiosk service user must be allowed to access the device company.")
                )
            if device.work_location_id and device.work_location_id.company_id and (
                device.work_location_id.company_id != device.company_id
            ):
                raise ValidationError(_("Work Location must belong to the device company."))

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_device(self):
        for device in self:
            if device.state != "draft" or device.log_ids:
                raise AccessError(
                    _("Only an unused Draft kiosk device can be deleted. Retire operational devices instead.")
                )

    @api.depends("log_ids", "log_ids.sync_state", "log_ids.latency_ms")
    def _compute_operational_metrics(self):
        Log = self.env["onehr.kiosk.log"]
        for device in self:
            domain = [("device_id", "=", device.id)]
            device.log_count = Log.search_count(domain)
            device.queued_count = Log.search_count(
                domain + [("sync_state", "in", ["queued", "failed", "processing"])]
            )
            device.error_count = Log.search_count(
                domain + [("sync_state", "in", ["failed", "blocked", "dead_letter"])]
            )
            synced = Log.search(domain + [("sync_state", "=", "synced"), ("latency_ms", ">", 0)])
            device.average_latency_ms = (
                sum(synced.mapped("latency_ms")) / len(synced) if synced else 0.0
            )

    def _issue_token(self):
        """Issue a token and return the raw value once; only its SHA-256 digest persists."""
        self.ensure_one()
        require_kiosk_admin(self)
        if self.state == "retired":
            raise UserError(_("A retired device cannot receive a new token."))
        raw_token = secrets.token_urlsafe(32)
        now = fields.Datetime.now()
        self._write_governed(
            {
                "token_hash": hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
                "token_last4": raw_token[-4:],
                "token_issued_at": now,
                "token_expires_at": now + timedelta(days=self.token_validity_days),
                "token_rotated_by_id": self.env.user.id,
            }
        )
        self.log_business_action(_("Device token issued/rotated; plaintext was not persisted."))
        return raw_token

    def _token_is_valid(self, raw_token):
        self.ensure_one()
        if not raw_token or not self.token_hash:
            return False
        if self.token_expires_at and fields.Datetime.now() > self.token_expires_at:
            return False
        supplied = hashlib.sha256(str(raw_token).encode("utf-8")).hexdigest()
        return hmac.compare_digest(supplied, self.token_hash)

    def _assert_kiosk_request(self, raw_token):
        """Enforce user scope AND device token; neither replaces the other."""
        self.ensure_one()
        require_kiosk_operator(self)
        if self.state != "active":
            raise AccessError(_("This kiosk device is not Active."))
        is_admin = self.env.user.has_group(GROUP_KIOSK_ADMIN)
        if self.env.user != self.service_user_id and not is_admin:
            raise AccessError(_("This authenticated user is not assigned to the kiosk device."))
        if self.company_id not in self.env.user.company_ids:
            raise AccessError(_("The kiosk company is outside the current user's allowed companies."))
        if not self._token_is_valid(raw_token):
            raise AccessError(_("Invalid or expired kiosk device token."))
        self._write_governed({"last_seen_at": fields.Datetime.now()})
        return True

    def action_issue_token(self):
        self.ensure_one()
        raw_token = self._issue_token()
        return display_notification(
            _("Kiosk Token — Copy Now"),
            _("Token: %s\nThis plaintext token is displayed once and is not stored by OneHR.", raw_token),
            notification_type="warning",
            sticky=True,
        )

    def action_activate(self):
        self.ensure_one()
        require_kiosk_admin(self)
        if self.state not in ("draft", "suspended"):
            raise UserError(_("Only Draft or Suspended devices can be activated."))
        self._check_configuration_integrity()
        if not self.service_user_id.has_group("onehr_mobile_kiosk.group_onehr_kiosk_operator"):
            raise ValidationError(
                _("The assigned service user must have the OneHR Kiosk Operator privilege before activation.")
            )
        raw_token = False
        if not self.token_hash or (
            self.token_expires_at and fields.Datetime.now() > self.token_expires_at
        ):
            raw_token = self._issue_token()
        self._write_governed({"state": "active", "active": True})
        self.log_business_action(_("Kiosk device activated."))
        if raw_token:
            return display_notification(
                _("Device Activated — Copy Token Now"),
                _("Token: %s\nThe token is displayed once and is stored only as a hash.", raw_token),
                notification_type="warning",
                sticky=True,
            )
        return True

    def action_suspend(self):
        self.ensure_one()
        require_kiosk_admin(self)
        if self.state != "active":
            raise UserError(_("Only an Active device can be suspended."))
        self._write_governed({"state": "suspended"})
        self.log_business_action(_("Kiosk device suspended."))
        return True

    def action_retire(self):
        self.ensure_one()
        require_kiosk_admin(self)
        if self.state == "retired":
            return True
        self._write_governed({"state": "retired", "active": False})
        self.log_business_action(_("Kiosk device retired. Existing token is no longer accepted."))
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        require_kiosk_admin(self)
        if self.state != "suspended":
            raise UserError(_("Only a Suspended device can be reset to Draft."))
        self._write_governed({"state": "draft"})
        return True

    def action_open_kiosk(self):
        self.ensure_one()
        require_kiosk_operator(self)
        if self.state != "active":
            raise UserError(_("Activate the device before opening Kiosk Mode."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/onehr/kiosk/{self.code}",
            "target": "new",
        }

    def action_open_logs(self):
        self.ensure_one()
        return open_records_action(
            name=_("Kiosk Activity — %s", self.display_name),
            res_model="onehr.kiosk.log",
            domain=[("device_id", "=", self.id)],
            context={"default_device_id": self.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_queue(self):
        self.ensure_one()
        return open_records_action(
            name=_("Sync Queue — %s", self.display_name),
            res_model="onehr.kiosk.log",
            domain=[
                ("device_id", "=", self.id),
                ("sync_state", "in", ["queued", "processing", "failed", "dead_letter"]),
            ],
            view_mode="list,form",
        )

    def action_open_errors(self):
        self.ensure_one()
        return open_records_action(
            name=_("Kiosk Errors — %s", self.display_name),
            res_model="onehr.kiosk.log",
            domain=[
                ("device_id", "=", self.id),
                ("sync_state", "in", ["failed", "blocked", "dead_letter"]),
            ],
            view_mode="list,form",
        )

    def action_print_usage_report(self):
        self.ensure_one()
        require_kiosk_admin(self)
        return self.env.ref("onehr_mobile_kiosk.action_report_onehr_kiosk_device_usage").report_action(self)

    def action_sync_pending(self):
        self.ensure_one()
        require_kiosk_admin(self)
        logs = self.env["onehr.kiosk.log"].search(
            [
                ("device_id", "=", self.id),
                ("sync_state", "in", ["queued", "failed"]),
                "|",
                ("next_retry_at", "=", False),
                ("next_retry_at", "<=", fields.Datetime.now()),
            ],
            limit=self.sync_batch_size,
            order="event_at, id",
        )
        for log in logs:
            log.with_user(self.service_user_id)._sync_one()
        return display_notification(
            _("Kiosk Sync"),
            _("%s queued event(s) were processed.", len(logs)),
            notification_type="success",
        )

    # -------------------------------------------------------------------------
    # Kiosk-facing domain services
    # -------------------------------------------------------------------------

    def kiosk_bootstrap(self, raw_token, client_version=None):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        if client_version:
            self._write_governed({"client_version": str(client_version)[:80]})
        return {
            "device": {
                "id": self.id,
                "name": self.name,
                "code": self.code,
                "kind": self.device_kind,
                "platform": self.platform,
                "work_location": self.work_location_id.display_name if self.work_location_id else False,
            },
            "capabilities": {
                "qr": self.allow_qr,
                "nfc": self.allow_nfc,
                "face_ready": self.face_ready,
                "quick_timeoff": self.quick_timeoff_enabled and "onehr.leave.request" in self.env,
                "offline_queue": self.offline_queue_enabled,
                "geolocation_required": self.geolocation_required,
            },
            "policy": {
                "geofence_policy": self.geofence_policy,
                "geofence_radius_m": self.geofence_radius_m,
                "sync_batch_size": self.sync_batch_size,
                "max_sync_attempts": self.max_sync_attempts,
            },
        }

    def _resolve_employee(self, identity):
        self.ensure_one()
        value = str(identity or "").strip()
        if not value:
            raise ValidationError(_("Scan or enter an employee QR/NFC identifier."))
        employee = self.env["hr.employee"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
                "|",
                ("barcode", "=", value),
                ("onehr_employee_number", "=", value),
            ],
            limit=2,
        )
        if len(employee) != 1:
            raise ValidationError(_("Employee identifier is unknown or ambiguous for this company."))
        return employee

    def _schedule_snapshot(self, employee):
        today = fields.Date.context_today(self)
        Schedule = self.env["onehr.shift.assignment"]
        schedule = Schedule.resolve_for_employee(employee, today)
        shift = schedule._shift_for_date(today) if schedule else False
        if not shift:
            shift = self.env["onehr.shift"].resolve_for_employee_date(employee, today)
        if not shift:
            return {"available": False, "date": fields.Date.to_string(today)}
        planned_start, planned_end = shift._planned_interval_utc(today)
        return {
            "available": True,
            "date": fields.Date.to_string(today),
            "shift": shift.display_name,
            "planned_start": fields.Datetime.to_string(planned_start) if planned_start else False,
            "planned_end": fields.Datetime.to_string(planned_end) if planned_end else False,
        }

    def _timeoff_snapshot(self, employee):
        if "onehr.leave.request" not in self.env or "onehr.leave.allocation" not in self.env:
            return {"available": False, "reason": _("OneHR Time Off is not installed.")}
        employee_user = employee.user_id
        if not employee_user or not employee_user.has_group("onehr_timeoff.group_onehr_timeoff_user"):
            return {
                "available": False,
                "reason": _("Employee self-service Time Off authority is not configured."),
            }
        today = fields.Date.context_today(self)
        LeaveType = self.env["onehr.leave.type"].with_user(employee_user)
        Allocation = self.env["onehr.leave.allocation"].with_user(employee_user)
        leave_types = LeaveType.search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "active"),
                ("valid_from", "<=", today),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", today),
            ],
            order="sequence, name",
        )
        balances = []
        for leave_type in leave_types:
            balance = Allocation.balance_for_employee(employee, leave_type, today)
            balances.append(
                {
                    "code": leave_type.code,
                    "name": leave_type.name,
                    "balance": round(balance, 4),
                }
            )
        return {"available": True, "balances": balances}

    def kiosk_employee_snapshot(self, raw_token, identity):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        employee = self._resolve_employee(identity)
        open_attendance = self.env["hr.attendance"].search(
            [("employee_id", "=", employee.id), ("check_out", "=", False)],
            order="check_in desc, id desc",
            limit=1,
        )
        return {
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "employee_number": employee.onehr_employee_number or False,
            },
            "attendance": {
                "checked_in": bool(open_attendance),
                "check_in": (
                    fields.Datetime.to_string(open_attendance.check_in) if open_attendance else False
                ),
            },
            "schedule": self._schedule_snapshot(employee),
            "timeoff": self._timeoff_snapshot(employee),
        }

    def _distance_from_device_m(self, latitude, longitude):
        """Haversine distance from configured OneHR work-location coordinates."""
        self.ensure_one()
        location = self.work_location_id
        if not location or not location.onehr_latitude or not location.onehr_longitude:
            return False
        lat1 = math.radians(location.onehr_latitude)
        lon1 = math.radians(location.onehr_longitude)
        lat2 = math.radians(float(latitude))
        lon2 = math.radians(float(longitude))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371000.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _evaluate_geofence(self, payload):
        self.ensure_one()
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if latitude in (None, False, "") or longitude in (None, False, ""):
            if self.geolocation_required:
                return "blocked", _("Device policy requires geolocation.")
            return "not_available", False
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise ValidationError(_("Latitude/longitude must be numeric."))
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValidationError(_("Latitude/longitude is outside the valid geographic range."))
        distance = self._distance_from_device_m(latitude, longitude)
        if distance is False or self.geofence_policy == "ignore" or not self.geofence_radius_m:
            return "not_required", False
        if distance <= self.geofence_radius_m:
            return "inside", False
        if self.geofence_policy == "block":
            return "blocked", _(
                "Punch is outside the device geofence (%(distance).0f m > %(radius)s m).",
                distance=distance,
                radius=self.geofence_radius_m,
            )
        return "outside_warning", _(
            "Outside device geofence (%(distance).0f m > %(radius)s m); event will be retained for review.",
            distance=distance,
            radius=self.geofence_radius_m,
        )

    def _existing_client_event(self, client_event_id):
        self.ensure_one()
        if not client_event_id:
            return self.env["onehr.kiosk.log"]
        return self.env["onehr.kiosk.log"].search(
            [("device_id", "=", self.id), ("client_event_id", "=", client_event_id)],
            limit=1,
        )

    def _create_kiosk_log(self, payload, event_type):
        self.ensure_one()
        client_event_id = str(payload.get("client_event_id") or "").strip()
        if not client_event_id:
            raise ValidationError(_("Every kiosk event requires a client_event_id for idempotency."))
        existing = self._existing_client_event(client_event_id)
        if existing:
            return existing

        employee = self._resolve_employee(payload.get("identity")) if event_type != "heartbeat" else False
        event_at = fields.Datetime.to_datetime(payload.get("event_at")) or fields.Datetime.now()
        if event_type == "heartbeat":
            geofence_status, geofence_message = "not_required", False
        else:
            geofence_status, geofence_message = self._evaluate_geofence(payload)
        summary = {
            "event_type": event_type,
            "punch_mode": payload.get("punch_mode") or False,
            "credential_type": payload.get("credential_type") or "qr",
            "offline": bool(payload.get("offline")),
            "has_coordinates": payload.get("latitude") not in (None, False, ""),
        }
        digest = hashlib.sha256(repr(sorted(summary.items())).encode("utf-8")).hexdigest()

        log = self.env["onehr.kiosk.log"].create(
            {
                "device_id": self.id,
                "employee_id": employee.id if employee else False,
                "event_type": event_type,
                "punch_mode": payload.get("punch_mode") or "auto",
                "credential_type": payload.get("credential_type") or "qr",
                "client_event_id": client_event_id,
                "event_at": event_at,
                "offline_event": bool(payload.get("offline")),
                "latitude": payload.get("latitude") or 0.0,
                "longitude": payload.get("longitude") or 0.0,
                "location_accuracy_m": payload.get("accuracy") or 0.0,
                "geofence_status": geofence_status,
                "request_summary": repr(summary),
                "payload_hash": digest,
                "leave_type_code": str(payload.get("leave_type_code") or "").strip().upper() or False,
                "leave_date_from": payload.get("date_from") or False,
                "leave_date_to": payload.get("date_to") or False,
                "leave_reason": str(payload.get("reason") or "").strip()[:1000] or False,
            }
        )
        if geofence_message:
            log._write_governed({"error_message": geofence_message})
        if geofence_status == "blocked":
            log._write_governed(
                {
                    "sync_state": "blocked",
                    "error_code": "GEOFENCE_BLOCKED",
                    "error_message": geofence_message,
                }
            )
        return log

    def kiosk_submit_punch(self, raw_token, payload):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        payload = dict(payload or {})
        log = self._create_kiosk_log(payload, "punch")
        if log.sync_state not in ("synced", "blocked", "dead_letter"):
            log._sync_one()
        return log.kiosk_result()

    def kiosk_submit_timeoff(self, raw_token, payload):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        if not self.quick_timeoff_enabled:
            raise AccessError(_("Quick Time Off is disabled on this kiosk device."))
        payload = dict(payload or {})
        log = self._create_kiosk_log(payload, "timeoff")
        if log.sync_state not in ("synced", "blocked", "dead_letter"):
            log._sync_one()
        return log.kiosk_result()

    def kiosk_heartbeat(self, raw_token, payload=None):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        payload = dict(payload or {})
        payload.setdefault("client_event_id", secrets.token_hex(12))
        log = self._create_kiosk_log(payload, "heartbeat")
        log._sync_one()
        return log.kiosk_result()

    def kiosk_sync_events(self, raw_token, events):
        self.ensure_one()
        self._assert_kiosk_request(raw_token)
        if not self.offline_queue_enabled:
            raise AccessError(_("Offline synchronization is disabled on this device."))
        results = []
        for incoming in list(events or [])[: self.sync_batch_size]:
            payload = dict(incoming or {})
            payload["offline"] = True
            event_type = payload.get("event_type")
            if event_type == "timeoff":
                results.append(self.kiosk_submit_timeoff(raw_token, payload))
            elif event_type == "heartbeat":
                results.append(self.kiosk_heartbeat(raw_token, payload))
            else:
                results.append(self.kiosk_submit_punch(raw_token, payload))
        self._write_governed({"last_sync_at": fields.Datetime.now()})
        return {"results": results, "processed": len(results)}
