import base64
import csv
import io

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action


REQUIRED_CSV_COLUMNS = {"employee", "check_in"}


class OneHRAttendanceImportBatch(models.Model):
    """ED3 staging batch for device/fingerprint attendance files.

    Raw rows are retained on the batch as structured JSON so no unregistered
    staging-line model is invented. Canonical ``hr.attendance`` is created only
    by the governed reconciliation service.
    """

    _name = "onehr.attendance.import.batch"
    _description = "OneHR Attendance Import Batch"
    _inherit = ["onehr.mixin.audit"]
    _order = "create_date desc, id desc"

    _STATE_CONTEXT = "onehr_attendance_import_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_attendance_import_evidence_controlled"

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _("New"), index=True, tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="restrict", index=True, tracking=True)
    source_system = fields.Char(required=True, default="FINGERPRINT", index=True, tracking=True)
    idempotency_key = fields.Char(required=True, index=True, tracking=True)
    upload_file = fields.Binary(required=True, attachment=True)
    filename = fields.Char(required=True)
    identifier_type = fields.Selection(
        [("employee_number", "OneHR Employee Number"), ("barcode", "Employee Badge / Barcode"), ("work_email", "Work Email")],
        required=True, default="employee_number", tracking=True,
    )
    timezone = fields.Selection(
        selection=lambda self: [(tz, tz) for tz in __import__("pytz").common_timezones],
        required=True, default=lambda self: self.env.company.resource_calendar_id.tz or "UTC", tracking=True,
    )
    state = fields.Selection(
        [("uploaded", "Uploaded"), ("parsed", "Parsed"), ("validated", "Validated"),
         ("reconciled", "Reconciled"), ("rejected", "Rejected")],
        required=True, default="uploaded", index=True, tracking=True,
    )
    raw_rows_json = fields.Json(readonly=True, copy=False)
    validation_payload = fields.Json(readonly=True, copy=False)
    raw_row_count = fields.Integer(readonly=True, copy=False)
    valid_row_count = fields.Integer(readonly=True, copy=False)
    error_row_count = fields.Integer(readonly=True, copy=False)
    error_log = fields.Text(readonly=True, copy=False)
    parsed_at = fields.Datetime(readonly=True, copy=False)
    validated_at = fields.Datetime(readonly=True, copy=False)
    reconciliation_ids = fields.One2many("onehr.attendance.reconciliation", "import_batch_id", string="Reconciliations", readonly=True)
    reconciliation_count = fields.Integer(compute="_compute_reconciliation_count")

    _import_idempotency_unique = models.Constraint(
        "unique(company_id, source_system, idempotency_key)",
        "Import Batch idempotency key must be unique per company and source system.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            values["source_system"] = (values.get("source_system") or "FINGERPRINT").strip().upper()
            values["idempotency_key"] = (values.get("idempotency_key") or "").strip()
            if not values["idempotency_key"]:
                raise ValidationError(_("Import Batch idempotency key is required."))
            if values.get("state", "uploaded") != "uploaded" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Import Batches must be created in Uploaded state."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.attendance.import.batch") or _("New")
            prepared.append(values)
        return super().create(prepared)

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Import Batch state can change only through governed actions."))
        evidence = {"raw_rows_json", "validation_payload", "raw_row_count", "valid_row_count", "error_row_count", "error_log", "parsed_at", "validated_at"}
        if evidence & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Parsed/validated import evidence can change only through governed services."))
        protected = {"company_id", "source_system", "idempotency_key", "upload_file", "filename", "identifier_type", "timezone"}
        if protected & set(values) and any(record.state not in {"uploaded", "rejected"} for record in self):
            raise AccessError(_("Parsed Import Batch source facts are frozen. Upload a new idempotent batch instead."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_import_evidence(self):
        if any(record.state not in {"uploaded", "rejected"} or record.reconciliation_count for record in self):
            raise AccessError(_("Parsed/reconciled Import Batch evidence is retained."))

    def _compute_reconciliation_count(self):
        Reconciliation = self.env["onehr.attendance.reconciliation"]
        for record in self:
            record.reconciliation_count = Reconciliation.search_count([("import_batch_id", "=", record.id)])

    def _decode_csv(self):
        self.ensure_one()
        try:
            raw = base64.b64decode(self.upload_file or b"")
            text = raw.decode("utf-8-sig")
        except Exception as exc:
            raise ValidationError(_("The uploaded file must be UTF-8 CSV: %s", exc)) from exc
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = {str(name or "").strip().lower() for name in (reader.fieldnames or [])}
        missing = REQUIRED_CSV_COLUMNS - fieldnames
        if missing:
            raise ValidationError(_("CSV is missing required column(s): %s", ", ".join(sorted(missing))))
        rows = []
        for line_no, raw_row in enumerate(reader, start=2):
            row = {str(key or "").strip().lower(): (value.strip() if isinstance(value, str) else value) for key, value in raw_row.items()}
            row["_line"] = line_no
            rows.append(row)
        return rows

    def action_parse(self):
        self._require_officer()
        for record in self:
            if record.state not in {"uploaded", "rejected"}:
                raise UserError(_("Only Uploaded/Rejected batches may be parsed again."))
            rows = record._decode_csv()
            record.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
                "state": "parsed", "raw_rows_json": rows, "raw_row_count": len(rows),
                "validation_payload": False, "valid_row_count": 0, "error_row_count": 0,
                "error_log": False, "parsed_at": fields.Datetime.now(), "validated_at": False,
            })
        return True

    def _employee_domain(self, identifier):
        self.ensure_one()
        if self.identifier_type == "barcode":
            return [("barcode", "=", identifier)]
        if self.identifier_type == "work_email":
            return [("work_email", "=ilike", identifier)]
        if "onehr_employee_number" not in self.env["hr.employee"]._fields:
            raise ValidationError(_("The current Core HR contract does not expose onehr_employee_number."))
        return [("onehr_employee_number", "=ilike", identifier)]

    def _local_csv_datetime_to_utc(self, value):
        """Interpret device CSV timestamps in the batch timezone and store UTC.

        Odoo Datetime values are naive UTC internally. Fingerprint exports commonly
        contain local wall-clock values, so the batch timezone is part of the frozen
        import contract instead of being ignored.
        """
        if not value:
            return False
        parsed = fields.Datetime.to_datetime(value)
        if not parsed:
            return False
        timezone = pytz.timezone(self.timezone or "UTC")
        try:
            localized = timezone.localize(parsed, is_dst=None)
        except pytz.AmbiguousTimeError:
            localized = timezone.localize(parsed, is_dst=False)
        except pytz.NonExistentTimeError as exc:
            raise ValidationError(_("Local datetime '%s' does not exist in timezone %s because of a DST transition.", value, self.timezone)) from exc
        return localized.astimezone(pytz.utc).replace(tzinfo=None)

    def _validate_row(self, row):
        self.ensure_one()
        identifier = (row.get("employee") or "").strip()
        if not identifier:
            raise ValidationError(_("Employee identifier is empty."))
        employee = self.env["hr.employee"].search(self._employee_domain(identifier) + [("company_id", "=", self.company_id.id)], limit=2)
        if len(employee) != 1:
            raise ValidationError(_("Employee identifier '%s' must resolve to exactly one employee in the batch company.", identifier))
        try:
            check_in = self._local_csv_datetime_to_utc(row.get("check_in"))
            check_out = self._local_csv_datetime_to_utc(row.get("check_out")) if row.get("check_out") else False
        except Exception as exc:
            raise ValidationError(_("Invalid check-in/check-out datetime: %s", exc)) from exc
        if not check_in:
            raise ValidationError(_("Check In is required."))
        if check_out and check_out <= check_in:
            raise ValidationError(_("Check Out must be later than Check In."))
        external_reference = (row.get("external_reference") or "").strip() or f"{self.idempotency_key}:{row.get('_line')}"

        def _float(name):
            value = row.get(name)
            if value in (None, ""):
                return 0.0
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Column '%s' must be numeric.", name)) from exc

        return {
            "employee_id": employee.id,
            "check_in": fields.Datetime.to_string(check_in),
            "check_out": fields.Datetime.to_string(check_out) if check_out else False,
            "source_channel": "fingerprint",
            "source_system": self.source_system,
            "external_reference": external_reference,
            "in_latitude": _float("in_latitude"),
            "in_longitude": _float("in_longitude"),
            "out_latitude": _float("out_latitude"),
            "out_longitude": _float("out_longitude"),
            "in_location": row.get("in_location") or False,
            "out_location": row.get("out_location") or False,
            "source_line": row.get("_line"),
        }

    def action_validate(self):
        self._require_officer()
        for record in self:
            if record.state != "parsed":
                raise UserError(_("Parse the Import Batch before validation."))
            candidates = []
            errors = []
            for row in record.raw_rows_json or []:
                try:
                    candidates.append(record._validate_row(row))
                except (ValidationError, UserError) as exc:
                    errors.append(_("Line %(line)s: %(error)s", line=row.get("_line", "?"), error=str(exc)))
            record.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
                "state": "validated" if not errors else "parsed",
                "validation_payload": candidates,
                "valid_row_count": len(candidates),
                "error_row_count": len(errors),
                "error_log": "\n".join(errors) if errors else False,
                "validated_at": fields.Datetime.now(),
            })
            if errors:
                return display_notification(
                    _("Validation found %s error row(s). Correct the source file and parse again.", len(errors)),
                    title=record.display_name, notification_type="warning", sticky=True,
                )
        return True

    def action_create_reconciliation(self):
        self._require_officer()
        self.ensure_one()
        if self.state != "validated" or self.error_row_count:
            raise UserError(_("Only a fully Validated Import Batch can create reconciliation."))
        reconciliation = self.env["onehr.attendance.reconciliation"].create({
            "company_id": self.company_id.id,
            "source_type": "import",
            "source_system": self.source_system,
            "import_batch_id": self.id,
            "candidate_payload": self.validation_payload or [],
        })
        return open_record_action(reconciliation.display_name, "onehr.attendance.reconciliation", reconciliation.id)

    def action_reject(self):
        self._require_manager()
        if any(record.state == "reconciled" for record in self):
            raise UserError(_("A reconciled Import Batch cannot be rejected."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "rejected"})
        return True

    def action_open_reconciliations(self):
        self.ensure_one()
        return open_records_action(_("Reconciliations — %s", self.display_name), "onehr.attendance.reconciliation", [("import_batch_id", "=", self.id)])

    def _require_officer(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_officer"):
            raise AccessError(_("OneHR Attendance Officer authority is required."))

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))


class OneHRAttendanceReconciliation(models.Model):
    """Governed ED3 batch that validates staged payloads before canonical posting."""

    _name = "onehr.attendance.reconciliation"
    _description = "OneHR Attendance Reconciliation"
    _inherit = ["onehr.mixin.audit"]
    _order = "create_date desc, id desc"

    _STATE_CONTEXT = "onehr_attendance_reconciliation_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_attendance_reconciliation_evidence_controlled"

    name = fields.Char(required=True, readonly=True, copy=False, default=lambda self: _("New"), index=True, tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="restrict", index=True, tracking=True)
    source_type = fields.Selection(
        [("import", "File / Fingerprint Import"), ("device", "Device / Kiosk"), ("api", "External API"), ("manual", "Controlled Manual Batch")],
        required=True, default="manual", index=True, tracking=True,
    )
    source_system = fields.Char(index=True, tracking=True)
    import_batch_id = fields.Many2one("onehr.attendance.import.batch", ondelete="restrict", check_company=True, index=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved"),
         ("posted", "Posted to Attendance"), ("cancelled", "Cancelled")],
        required=True, default="draft", index=True, tracking=True,
    )
    candidate_payload = fields.Json(copy=False)
    candidate_count = fields.Integer(compute="_compute_counts")
    attendance_ids = fields.One2many("hr.attendance", "onehr_reconciliation_id", string="Canonical Attendances", readonly=True)
    attendance_count = fields.Integer(compute="_compute_counts")
    exception_ids = fields.One2many("onehr.attendance.exception", "reconciliation_id", string="Exceptions", readonly=True)
    exception_count = fields.Integer(compute="_compute_counts")
    review_note = fields.Text(tracking=True)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    submitted_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    approved_at = fields.Datetime(readonly=True, copy=False)
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    posted_at = fields.Datetime(readonly=True, copy=False)
    posted_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Attendance Reconciliation must start in Draft."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.attendance.reconciliation") or _("New")
            prepared.append(values)
        records = super().create(prepared)
        records._validate_reconciliation_integrity()
        return records

    def write(self, values):
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Reconciliation state can change only through governed actions."))
        evidence = {"submitted_at", "submitted_by_id", "approved_at", "approved_by_id", "posted_at", "posted_by_id"}
        if evidence & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Reconciliation evidence can change only through governed actions."))
        if "candidate_payload" in values and any(record.state != "draft" for record in self):
            raise AccessError(_("Candidate payload is frozen after reconciliation enters review."))
        result = super().write(values)
        if {"company_id", "import_batch_id", "candidate_payload"} & set(values):
            self._validate_reconciliation_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_reconciliation_history(self):
        if any(record.state != "draft" or record.attendance_count for record in self):
            raise AccessError(_("Only an unused Draft Reconciliation may be deleted."))

    @api.constrains("company_id", "import_batch_id")
    def _check_integrity(self):
        self._validate_reconciliation_integrity()

    def _validate_reconciliation_integrity(self):
        for record in self:
            if record.import_batch_id and record.import_batch_id.company_id != record.company_id:
                raise ValidationError(_("Import Batch and Reconciliation company must match."))

    def _compute_counts(self):
        Attendance = self.env["hr.attendance"]
        Exception = self.env["onehr.attendance.exception"]
        for record in self:
            record.candidate_count = len(record.candidate_payload or [])
            record.attendance_count = Attendance.search_count([("onehr_reconciliation_id", "=", record.id)])
            record.exception_count = Exception.search_count([("reconciliation_id", "=", record.id)])

    def action_validate_candidates(self):
        self._require_officer()
        self.ensure_one()
        errors = []
        for index, candidate in enumerate(self.candidate_payload or [], start=1):
            if not candidate.get("employee_id") or not candidate.get("check_in"):
                errors.append(_("Candidate %s is missing employee_id/check_in.", index))
            if self.source_type != "manual" and not candidate.get("external_reference"):
                errors.append(_("Candidate %s requires external_reference for retry-safe posting.", index))
            if self.source_type != "manual" and not (candidate.get("source_system") or self.source_system):
                errors.append(_("Candidate %s requires a source system.", index))
            employee = self.env["hr.employee"].browse(candidate.get("employee_id")).exists()
            if employee and employee.company_id != self.company_id:
                errors.append(_("Candidate %s employee belongs to another company.", index))
        if errors:
            raise ValidationError("\n".join(errors))
        return display_notification(_("All %s candidate row(s) are structurally valid.", len(self.candidate_payload or [])), notification_type="success")

    def action_submit_review(self):
        self._require_officer()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft Reconciliations can enter review."))
            record.action_validate_candidates()
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "in_review", "submitted_at": fields.Datetime.now(), "submitted_by_id": self.env.user.id,
        })
        return True

    def action_approve(self):
        self._require_manager()
        if any(record.state != "in_review" for record in self):
            raise UserError(_("Only In Review Reconciliations may be approved."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "approved", "approved_at": fields.Datetime.now(), "approved_by_id": self.env.user.id,
        })
        return True

    def action_post(self):
        self._require_manager()
        Attendance = self.env["hr.attendance"]
        for record in self:
            if record.state != "approved":
                raise UserError(_("Approve the Reconciliation before posting it to canonical attendance."))
            record.action_validate_candidates()
            for candidate in record.candidate_payload or []:
                payload = dict(candidate)
                payload["reconciliation_id"] = record.id
                attendance = Attendance.onehr_ingest_interval(payload)
                if attendance.onehr_processing_state == "draft" and attendance.check_out:
                    attendance.action_onehr_confirm()
            record.with_context(**{record._STATE_CONTEXT: True, record._EVIDENCE_CONTEXT: True}).write({
                "state": "posted", "posted_at": fields.Datetime.now(), "posted_by_id": record.env.user.id,
            })
            if record.import_batch_id:
                record.import_batch_id.with_context(**{record.import_batch_id._STATE_CONTEXT: True}).write({"state": "reconciled"})
        return True

    def action_cancel(self):
        self._require_manager()
        if any(record.state == "posted" for record in self):
            raise UserError(_("Posted Reconciliation evidence cannot be cancelled."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "cancelled"})
        return True

    def action_open_import_batch(self):
        self.ensure_one()
        if not self.import_batch_id:
            raise UserError(_("This Reconciliation is not linked to an Import Batch."))
        return open_record_action(self.import_batch_id.display_name, "onehr.attendance.import.batch", self.import_batch_id.id)

    def action_open_attendances(self):
        self.ensure_one()
        return open_records_action(_("Canonical Attendances"), "hr.attendance", [("onehr_reconciliation_id", "=", self.id)], view_mode="list,calendar,pivot,graph,form")

    def action_open_exceptions(self):
        self.ensure_one()
        return open_records_action(_("Reconciliation Exceptions"), "onehr.attendance.exception", [("reconciliation_id", "=", self.id)])

    def _require_officer(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_officer"):
            raise AccessError(_("OneHR Attendance Officer authority is required."))

    def _require_manager(self):
        if not self.env.user.has_group("onehr_attendance.group_onehr_attendance_manager"):
            raise AccessError(_("OneHR Attendance Manager authority is required."))
