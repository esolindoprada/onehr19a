import base64
import csv
import hashlib
import io
import json
import pytz
from datetime import datetime, time, timedelta
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action
from .authority_helpers import require_payroll_manager, require_payroll_officer


CANONICAL_EXPORT_COLUMNS = (
    "employee_number",
    "employee_name",
    "company",
    "department",
    "job",
    "grade",
    "position",
    "salary_structure_code",
    "period_start",
    "period_end",
    "work_entry_count",
    "work_entry_hours",
    "work_entries_json",
    "attendance_count",
    "worked_hours",
    "rounded_worked_hours",
    "late_minutes",
    "early_leave_minutes",
    "overtime_hours",
    "overtime_codes",
    "paid_leave_days",
    "unpaid_leave_days",
    "costing_json",
    "variables_json",
)


class OneHRPayrollExport(models.Model):
    """Governed payroll exchange batch.

    Draft rows can be regenerated. Posting freezes source evidence. Reconciliation
    requires imported payroll results and retains both source and vendor evidence.
    """

    _name = "onehr.payroll.export"
    _description = "OneHR Payroll Export Batch"
    _inherit = ["onehr.mixin.audit"]
    _order = "period_end desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_payroll_export_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_payroll_export_evidence_controlled"

    name = fields.Char(
        string="Export No.",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    config_id = fields.Many2one(
        "onehr.payroll.bridge.config",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    period_start = fields.Date(required=True, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)
    employee_ids = fields.Many2many(
        "hr.employee",
        "onehr_payroll_export_employee_rel",
        "export_id",
        "employee_id",
        string="Employee Scope",
        tracking=True,
        help="Leave empty to export all active employees in the selected company.",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted to Payroll"),
            ("reconciled", "Reconciled"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    generated = fields.Boolean(readonly=True, copy=False, index=True)
    export_file = fields.Binary(
        string="Payroll Export CSV",
        attachment=True,
        copy=False,
        readonly=True,
    )
    export_filename = fields.Char(copy=False, readonly=True)
    export_sha256 = fields.Char(copy=False, readonly=True, index=True)
    source_rows_json = fields.Text(
        string="Frozen Source Rows",
        copy=False,
        readonly=True,
        groups="onehr_payroll_bridge.group_onehr_payroll_officer,onehr_payroll_bridge.group_onehr_payroll_manager",
    )
    config_snapshot_json = fields.Text(
        string="Frozen Mapping Snapshot",
        copy=False,
        readonly=True,
        groups="onehr_payroll_bridge.group_onehr_payroll_manager",
    )
    costing_payload_json = fields.Text(
        string="Reconciled Costing Payload",
        copy=False,
        readonly=True,
        groups="onehr_payroll_bridge.group_onehr_payroll_manager",
    )

    external_batch_reference = fields.Char(
        copy=False,
        index=True,
        tracking=True,
        help="External payroll batch/reference returned by or recorded for the payroll engine.",
    )

    employee_count = fields.Integer(readonly=True, copy=False)
    source_row_count = fields.Integer(readonly=True, copy=False)
    work_entry_count = fields.Integer(readonly=True, copy=False)
    work_entry_hours = fields.Float(readonly=True, copy=False)
    attendance_count = fields.Integer(readonly=True, copy=False)
    worked_hours = fields.Float(readonly=True, copy=False)
    rounded_worked_hours = fields.Float(readonly=True, copy=False)
    overtime_hours = fields.Float(readonly=True, copy=False)
    paid_leave_days = fields.Float(readonly=True, copy=False)
    unpaid_leave_days = fields.Float(readonly=True, copy=False)

    generated_at = fields.Datetime(readonly=True, copy=False)
    generated_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    posted_at = fields.Datetime(readonly=True, copy=False)
    posted_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    reconciled_at = fields.Datetime(readonly=True, copy=False)
    reconciled_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    cancelled_at = fields.Datetime(readonly=True, copy=False)
    cancelled_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    cancellation_reason = fields.Text(copy=False, tracking=True)

    vendor_import_file = fields.Binary(
        string="Vendor Payroll Result CSV",
        attachment=True,
        copy=False,
    )
    vendor_import_filename = fields.Char(copy=False)
    vendor_import_sha256 = fields.Char(copy=False, readonly=True, index=True)
    vendor_imported_at = fields.Datetime(copy=False, readonly=True)
    vendor_imported_by_id = fields.Many2one(
        "res.users", copy=False, readonly=True, ondelete="restrict"
    )

    import_ids = fields.One2many(
        "onehr.payroll.import",
        "export_id",
        string="Imported Payroll Results",
        readonly=True,
    )
    import_count = fields.Integer(compute="_compute_reconciliation_metrics", store=True)
    current_import_count = fields.Integer(compute="_compute_reconciliation_metrics", store=True)
    matched_employee_count = fields.Integer(compute="_compute_reconciliation_metrics", store=True)
    reconciliation_accuracy = fields.Float(
        string="Reconciliation Coverage %",
        compute="_compute_reconciliation_metrics",
        store=True,
        aggregator="avg",
    )
    imported_gross_total = fields.Monetary(
        compute="_compute_reconciliation_metrics",
        currency_field="currency_id",
        store=True,
    )
    imported_deduction_total = fields.Monetary(
        compute="_compute_reconciliation_metrics",
        currency_field="currency_id",
        store=True,
    )
    imported_net_total = fields.Monetary(
        compute="_compute_reconciliation_metrics",
        currency_field="currency_id",
        store=True,
    )
    imported_employer_cost_total = fields.Monetary(
        compute="_compute_reconciliation_metrics",
        currency_field="currency_id",
        store=True,
    )
    time_to_close_hours = fields.Float(
        compute="_compute_time_to_close",
        store=True,
        aggregator="avg",
    )

    _export_number_unique = models.Constraint(
        "unique(name)",
        "Payroll Export Number must be unique.",
    )

    @api.onchange("config_id")
    def _onchange_config_id(self):
        if self.config_id:
            self.company_id = self.config_id.company_id
            self.currency_id = self.config_id.currency_id

    @api.model_create_multi
    def create(self, vals_list):
        require_payroll_officer(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            config = self.env["onehr.payroll.bridge.config"].browse(values.get("config_id")).exists()
            if not config:
                raise ValidationError(_("A valid Payroll Bridge Configuration is required."))
            if not config.active:
                raise ValidationError(_("The selected Payroll Bridge Configuration is archived."))
            values.setdefault("company_id", config.company_id.id)
            values.setdefault("currency_id", config.currency_id.id)
            if values["company_id"] != config.company_id.id:
                raise ValidationError(_("Export company must match the Payroll Bridge Configuration company."))
            if values["currency_id"] != config.currency_id.id:
                raise ValidationError(_("Export currency must match the Payroll Bridge Configuration currency."))
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Payroll Exports must be created in Draft."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.payroll.export") or _("New")
            prepared.append(values)
        records = super().create(prepared)
        records._validate_export_integrity()
        return records

    def write(self, values):
        state_controlled = self.env.context.get(self._STATE_CONTEXT)
        evidence_controlled = self.env.context.get(self._EVIDENCE_CONTEXT)

        if "state" in values and not state_controlled:
            raise AccessError(_("Payroll Export state changes only through governed actions."))

        evidence_fields = {
            "generated",
            "export_file",
            "export_filename",
            "export_sha256",
            "source_rows_json",
            "config_snapshot_json",
            "costing_payload_json",
            "vendor_import_sha256",
            "vendor_imported_at",
            "vendor_imported_by_id",
            "employee_count",
            "source_row_count",
            "attendance_count",
            "worked_hours",
            "rounded_worked_hours",
            "overtime_hours",
            "paid_leave_days",
            "unpaid_leave_days",
            "generated_at",
            "generated_by_id",
            "posted_at",
            "posted_by_id",
            "reconciled_at",
            "reconciled_by_id",
            "cancelled_at",
            "cancelled_by_id",
        }
        if evidence_fields & set(values) and not evidence_controlled:
            raise AccessError(_("Payroll Export evidence is controlled by business actions."))

        frozen_fields = {
            "config_id",
            "company_id",
            "currency_id",
            "period_start",
            "period_end",
            "employee_ids",
        }
        if frozen_fields & set(values):
            if any(record.state != "draft" for record in self):
                raise AccessError(_("Posted payroll source facts are immutable."))
            if any(record.generated for record in self):
                raise AccessError(
                    _("Generated payroll source scope is frozen. Use Reset Generated Package before editing period/configuration/employee scope.")
                )

        if {"vendor_import_file", "vendor_import_filename"} & set(values):
            if any(record.state not in {"posted"} for record in self):
                raise AccessError(_("Vendor result files can be uploaded only while an export is Posted to Payroll."))
            if "vendor_import_file" in values:
                for record in self:
                    validated_current = record.import_ids.filtered(
                        lambda row: row.is_current_revision and row.state == "validated"
                    )
                    if not validated_current:
                        continue
                    incoming_binary = values.get("vendor_import_file")
                    incoming_hash = (
                        hashlib.sha256(base64.b64decode(incoming_binary)).hexdigest()
                        if incoming_binary
                        else ""
                    )
                    if incoming_hash != (record.vendor_import_sha256 or ""):
                        raise AccessError(
                            _(
                                "Validated vendor payroll evidence already exists. "
                                "Create governed correction revision(s) before replacing the vendor result file."
                            )
                        )

        if "cancellation_reason" in values and any(record.state != "draft" for record in self):
            raise AccessError(_("Cancellation Reason can be changed only while the Payroll Export is Draft."))

        result = super().write(values)
        if frozen_fields & set(values):
            self._validate_export_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_export(self):
        if any(record.state != "draft" or record.generated or record.import_ids for record in self):
            raise AccessError(_("Only an unused Draft Payroll Export can be deleted."))

    @api.constrains("config_id", "company_id", "currency_id", "period_start", "period_end", "employee_ids")
    def _check_export_integrity(self):
        self._validate_export_integrity()

    def _validate_export_integrity(self):
        for record in self:
            if record.period_end < record.period_start:
                raise ValidationError(_("Payroll Period End cannot be before Period Start."))
            if record.config_id.company_id != record.company_id:
                raise ValidationError(_("Export and Configuration must belong to the same company."))
            if record.config_id.currency_id != record.currency_id:
                raise ValidationError(_("Export and Configuration must use the same currency."))
            wrong_company = record.employee_ids.filtered(lambda employee: employee.company_id != record.company_id)
            if wrong_company:
                raise ValidationError(_("Every scoped employee must belong to the Export company."))
        return True

    def _config_snapshot(self):
        self.ensure_one()
        try:
            snapshot = json.loads(self.config_snapshot_json or "{}")
        except ValueError as exc:
            raise ValidationError(_("Frozen Payroll Bridge configuration snapshot is invalid JSON.")) from exc
        return snapshot if isinstance(snapshot, dict) else {}

    def _snapshot_config_value(self, key, fallback=None):
        self.ensure_one()
        snapshot = self._config_snapshot()
        return snapshot.get(key, fallback)

    def _frozen_import_mapping(self):
        self.ensure_one()
        mapping = self._snapshot_config_value("import_field_mapping")
        if not isinstance(mapping, dict):
            # Compatibility fallback for a pre-snapshot Draft generated by an older
            # supported version. New packages always have the frozen mapping.
            mapping = self.config_id._parse_mapping(
                "import_field_mapping",
                required_keys=("employee_number", "external_reference", "net_amount"),
            )
        required = ("employee_number", "external_reference", "net_amount")
        missing = [key for key in required if not mapping.get(key)]
        if missing:
            raise ValidationError(
                _("Frozen import mapping is missing required key(s): %s") % ", ".join(missing)
            )
        return mapping

    def _frozen_csv_delimiter_character(self):
        self.ensure_one()
        value = self._snapshot_config_value("csv_delimiter", self.config_id.csv_delimiter)
        return "\t" if value == "tab" else value

    def _frozen_reconciliation_policy(self):
        self.ensure_one()
        return {
            "require_full_reconciliation": bool(
                self._snapshot_config_value(
                    "require_full_reconciliation",
                    self.config_id.require_full_reconciliation,
                )
            ),
            "validate_net_equation": bool(
                self._snapshot_config_value(
                    "validate_net_equation",
                    self.config_id.validate_net_equation,
                )
            ),
            "net_reconciliation_tolerance": float(
                self._snapshot_config_value(
                    "net_reconciliation_tolerance",
                    self.config_id.net_reconciliation_tolerance,
                )
                or 0.0
            ),
        }

    def _selected_employees(self):
        self.ensure_one()
        if self.employee_ids:
            return self.employee_ids.filtered(lambda employee: employee.active and employee.company_id == self.company_id)
        return self.env["hr.employee"].search(
            [("company_id", "=", self.company_id.id), ("active", "=", True)],
            order="onehr_employee_number, name, id",
        )

    def _period_datetimes(self, employee):
        """Return UTC-naive database boundaries for the employee's local payroll dates."""
        self.ensure_one()
        timezone_name = (
            employee.resource_calendar_id.tz
            or self.env.user.tz
            or "UTC"
        )
        try:
            local_tz = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError as exc:
            raise ValidationError(
                _("Unknown payroll employee timezone '%s'.") % timezone_name
            ) from exc

        local_start = local_tz.localize(datetime.combine(self.period_start, time.min))
        local_end = local_tz.localize(
            datetime.combine(self.period_end + timedelta(days=1), time.min)
        )
        start = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
        end = local_end.astimezone(pytz.UTC).replace(tzinfo=None)
        return start, end

    def _collect_work_entries(self, employee):
        """Read existing native work-entry evidence without generating or rewriting it."""
        self.ensure_one()
        result = {
            "work_entry_count": 0,
            "work_entry_hours": 0.0,
            "work_entries": [],
        }
        if not self.config_id.include_work_entries or "hr.work.entry" not in self.env:
            return result

        WorkEntry = self.env["hr.work.entry"]
        required_fields = {"employee_id", "date", "duration", "state"}
        if not required_fields.issubset(WorkEntry._fields):
            return result

        rows = WorkEntry.search(
            [
                ("employee_id", "=", employee.id),
                ("date", ">=", self.period_start),
                ("date", "<=", self.period_end),
                ("state", "in", ["draft", "validated"]),
            ],
            order="date, id",
        )
        entries = []
        for row in rows:
            entries.append(
                {
                    "work_entry_id": row.id,
                    "date": fields.Date.to_string(row.date),
                    "duration": row.duration,
                    "state": row.state,
                    "code": row.code if "code" in row._fields else "",
                    "external_code": row.external_code if "external_code" in row._fields else "",
                    "work_entry_type": (
                        row.work_entry_type_id.display_name
                        if "work_entry_type_id" in row._fields and row.work_entry_type_id
                        else ""
                    ),
                }
            )
        result["work_entry_count"] = len(rows)
        result["work_entry_hours"] = round(sum(rows.mapped("duration")), 4)
        result["work_entries"] = entries
        return result

    def _collect_attendance_variables(self, employee):
        self.ensure_one()
        result = {
            "attendance_count": 0,
            "worked_hours": 0.0,
            "rounded_worked_hours": 0.0,
            "late_minutes": 0.0,
            "early_leave_minutes": 0.0,
            "attendance_ids": [],
        }
        config = self.config_id
        if not config.include_attendance or "hr.attendance" not in self.env:
            return result

        Attendance = self.env["hr.attendance"]
        start_dt, end_dt = self._period_datetimes(employee)
        domain = [
            ("employee_id", "=", employee.id),
            ("check_in", ">=", start_dt),
            ("check_in", "<", end_dt),
        ]
        if config.require_posted_attendance and "onehr_processing_state" in Attendance._fields:
            domain.append(("onehr_processing_state", "=", "posted"))
        elif "check_out" in Attendance._fields:
            domain.append(("check_out", "!=", False))

        rows = Attendance.search(domain)
        result["attendance_count"] = len(rows)
        result["attendance_ids"] = rows.ids
        result["worked_hours"] = round(sum(rows.mapped("worked_hours")), 4) if "worked_hours" in Attendance._fields else 0.0
        if "onehr_rounded_worked_hours" in Attendance._fields:
            result["rounded_worked_hours"] = round(sum(rows.mapped("onehr_rounded_worked_hours")), 4)
        else:
            result["rounded_worked_hours"] = result["worked_hours"]
        if "onehr_late_minutes" in Attendance._fields:
            result["late_minutes"] = round(sum(rows.mapped("onehr_late_minutes")), 2)
        if "onehr_early_leave_minutes" in Attendance._fields:
            result["early_leave_minutes"] = round(sum(rows.mapped("onehr_early_leave_minutes")), 2)
        return result

    def _collect_overtime_variables(self, employee):
        self.ensure_one()
        result = {"overtime_hours": 0.0, "overtime_codes": [], "overtime_ids": []}
        if not self.config_id.include_overtime or "hr.attendance.overtime.line" not in self.env:
            return result

        Overtime = self.env["hr.attendance.overtime.line"]
        domain = [
            ("employee_id", "=", employee.id),
            ("date", ">=", self.period_start),
            ("date", "<=", self.period_end),
        ]
        if "onehr_export_ready" in Overtime._fields:
            domain.append(("onehr_export_ready", "=", True))
        elif "status" in Overtime._fields:
            domain.append(("status", "=", "approved"))

        rows = Overtime.search(domain)
        result["overtime_ids"] = rows.ids
        if "duration" in Overtime._fields:
            result["overtime_hours"] = round(sum(rows.mapped("duration")), 4)
        if "onehr_payroll_code_snapshot" in Overtime._fields:
            codes = []
            for value in rows.mapped("onehr_payroll_code_snapshot"):
                codes.extend(item.strip() for item in (value or "").split(",") if item.strip())
            result["overtime_codes"] = sorted(set(codes))
        return result

    def _leave_overlap_days(self, leave):
        self.ensure_one()
        overlap_start = max(leave.date_from, self.period_start)
        overlap_end = min(leave.date_to, self.period_end)
        if overlap_end < overlap_start:
            return 0.0
        if "half_day" in leave._fields and leave.half_day and overlap_start <= leave.date_from <= overlap_end:
            return 0.5

        calendar = leave.employee_id.resource_calendar_id
        if calendar:
            start_dt = datetime.combine(overlap_start, time.min).replace(tzinfo=pytz.UTC)
            end_dt = datetime.combine(overlap_end + timedelta(days=1), time.min).replace(tzinfo=pytz.UTC)
            hours = calendar.get_work_hours_count(start_dt, end_dt, compute_leaves=True)
            hours_per_day = calendar.hours_per_day or 8.0
            return round(hours / hours_per_day, 4) if hours_per_day else 0.0

        cursor = overlap_start
        days = 0.0
        while cursor <= overlap_end:
            if cursor.weekday() < 5:
                days += 1.0
            cursor += timedelta(days=1)
        return days

    def _collect_timeoff_variables(self, employee):
        self.ensure_one()
        result = {
            "paid_leave_days": 0.0,
            "unpaid_leave_days": 0.0,
            "leave_payloads": [],
        }
        if not self.config_id.include_timeoff or "onehr.leave.request" not in self.env:
            return result

        Leave = self.env["onehr.leave.request"]
        rows = Leave.search(
            [
                ("employee_id", "=", employee.id),
                ("state", "in", ["approved", "done"]),
                ("date_from", "<=", self.period_end),
                ("date_to", ">=", self.period_start),
            ]
        )
        for leave in rows:
            days = self._leave_overlap_days(leave)
            payload = (
                leave.onehr_timeoff_payroll_payload()
                if hasattr(leave, "onehr_timeoff_payroll_payload")
                else {
                    "request_id": leave.id,
                    "employee_id": employee.id,
                    "date_from": fields.Date.to_string(leave.date_from),
                    "date_to": fields.Date.to_string(leave.date_to),
                    "state": leave.state,
                }
            )
            payload = dict(payload)
            payload["period_overlap_days"] = days
            result["leave_payloads"].append(payload)
            paid_leave = bool(
                "leave_type_id" in leave._fields
                and leave.leave_type_id
                and "paid_leave" in leave.leave_type_id._fields
                and leave.leave_type_id.paid_leave
            )
            if paid_leave:
                result["paid_leave_days"] += days
            else:
                result["unpaid_leave_days"] += days
        result["paid_leave_days"] = round(result["paid_leave_days"], 4)
        result["unpaid_leave_days"] = round(result["unpaid_leave_days"], 4)
        return result

    def _collect_assignment_costing(self, employee):
        self.ensure_one()
        if not self.config_id.include_assignment_costing or "onehr.assignment.cost.allocation" not in self.env:
            return []

        Allocation = self.env["onehr.assignment.cost.allocation"]
        rows = Allocation.search(
            [
                ("assignment_id.employee_id", "=", employee.id),
                ("assignment_id.company_id", "=", self.company_id.id),
                ("assignment_id.state", "in", ["approved", "active", "ended"]),
                ("valid_from", "<=", self.period_end),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", self.period_start),
            ],
            order="valid_from, sequence, id",
        )
        return [
            {
                "allocation_id": line.id,
                "valid_from": fields.Date.to_string(line.valid_from),
                "valid_to": fields.Date.to_string(line.valid_to) if line.valid_to else False,
                "percentage": line.percentage,
                "cost_center_code": line.cost_center_code or "",
                "project_code": line.project_code or "",
                "product_line_code": line.product_line_code or "",
                "external_dimension": line.external_dimension or "",
            }
            for line in rows
        ]

    def _onehr_extend_employee_export_row(self, employee, row):
        """Safe downstream hook.

        Payroll localization can inherit this model because it depends on the bridge.
        Other optional domains may add an employee-side payroll payload method without
        requiring this addon to guess their model ownership.
        """
        if hasattr(employee, "onehr_payroll_variable_payload"):
            extra = employee.onehr_payroll_variable_payload(self.period_start, self.period_end)
            if isinstance(extra, dict):
                row["variables_json"]["employee_extension"] = extra
        return row

    def _build_employee_row(self, employee):
        self.ensure_one()
        work_entries = self._collect_work_entries(employee)
        attendance = self._collect_attendance_variables(employee)
        overtime = self._collect_overtime_variables(employee)
        timeoff = self._collect_timeoff_variables(employee)
        costing = self._collect_assignment_costing(employee)

        grade = employee.onehr_grade_id
        position = employee.onehr_primary_position_id
        grade_code = grade.code if grade and "code" in grade._fields else ""
        position_code = position.code if position and "code" in position._fields else ""

        variable_payload = {
            "work_entries": work_entries,
            "attendance": attendance,
            "overtime": overtime,
            "timeoff": timeoff,
        }
        row = {
            "employee_number": employee.onehr_employee_number or "",
            "employee_name": employee.name or "",
            "company": employee.company_id.name or "",
            "department": employee.department_id.name or "",
            "job": employee.job_id.name or "",
            "grade": grade_code,
            "position": position_code,
            "salary_structure_code": self.config_id.resolve_salary_structure_code(employee),
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "work_entry_count": work_entries["work_entry_count"],
            "work_entry_hours": work_entries["work_entry_hours"],
            "work_entries_json": work_entries["work_entries"],
            "attendance_count": attendance["attendance_count"],
            "worked_hours": attendance["worked_hours"],
            "rounded_worked_hours": attendance["rounded_worked_hours"],
            "late_minutes": attendance["late_minutes"],
            "early_leave_minutes": attendance["early_leave_minutes"],
            "overtime_hours": overtime["overtime_hours"],
            "overtime_codes": ",".join(overtime["overtime_codes"]),
            "paid_leave_days": timeoff["paid_leave_days"],
            "unpaid_leave_days": timeoff["unpaid_leave_days"],
            "costing_json": costing,
            "variables_json": variable_payload,
        }
        return self._onehr_extend_employee_export_row(employee, row)

    def _collect_source_rows(self):
        self.ensure_one()
        rows = []
        for employee in self._selected_employees():
            if not employee.onehr_employee_number:
                raise ValidationError(
                    _("Employee '%s' has no OneHR Employee Number and cannot be exported safely.")
                    % employee.display_name
                )
            rows.append(self._build_employee_row(employee))
        return rows

    def _csv_header_mapping(self):
        self.ensure_one()
        mapping = self.config_id._parse_mapping(
            "export_field_mapping",
            required_keys=("employee_number",),
        )
        return [(key, mapping.get(key)) for key in CANONICAL_EXPORT_COLUMNS if mapping.get(key)]

    def _csv_value(self, value):
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if value in (None, False):
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, float):
            rendered = ("%.10f" % value).rstrip("0").rstrip(".")
            decimal_separator = self._snapshot_config_value(
                "decimal_separator", self.config_id.decimal_separator
            )
            if decimal_separator == ",":
                rendered = rendered.replace(".", ",")
            return rendered
        return value

    def _build_csv_bytes(self, rows):
        self.ensure_one()
        mapping = self._csv_header_mapping()
        headers = [external_header for _key, external_header in mapping]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(
            output,
            fieldnames=headers,
            delimiter=self.config_id.csv_delimiter_character(),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    external_header: self._csv_value(row.get(canonical_key))
                    for canonical_key, external_header in mapping
                }
            )
        return output.getvalue().encode(self.config_id.csv_encoding)

    def action_generate_export(self):
        self.ensure_one()
        require_payroll_officer(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Payroll Export can be generated or regenerated."))
        self._validate_export_integrity()
        self.config_id._validate_configuration()

        rows = self._collect_source_rows()
        if not rows:
            raise UserError(_("No active employees are available in the selected payroll scope."))

        csv_bytes = self._build_csv_bytes(rows)
        canonical_json = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        filename = "%s_%s_%s.csv" % (
            self.name.replace("/", "-"),
            fields.Date.to_string(self.period_start),
            fields.Date.to_string(self.period_end),
        )

        vals = {
            "generated": True,
            "export_file": base64.b64encode(csv_bytes),
            "export_filename": filename,
            "export_sha256": digest,
            "source_rows_json": json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True),
            "config_snapshot_json": json.dumps(
                self.config_id.export_mapping_snapshot(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "employee_count": len(rows),
            "source_row_count": len(rows),
            "work_entry_count": sum(int(row.get("work_entry_count") or 0) for row in rows),
            "work_entry_hours": round(sum(float(row.get("work_entry_hours") or 0.0) for row in rows), 4),
            "attendance_count": sum(int(row.get("attendance_count") or 0) for row in rows),
            "worked_hours": round(sum(float(row.get("worked_hours") or 0.0) for row in rows), 4),
            "rounded_worked_hours": round(
                sum(float(row.get("rounded_worked_hours") or 0.0) for row in rows), 4
            ),
            "overtime_hours": round(sum(float(row.get("overtime_hours") or 0.0) for row in rows), 4),
            "paid_leave_days": round(sum(float(row.get("paid_leave_days") or 0.0) for row in rows), 4),
            "unpaid_leave_days": round(sum(float(row.get("unpaid_leave_days") or 0.0) for row in rows), 4),
            "generated_at": fields.Datetime.now(),
            "generated_by_id": self.env.user.id,
        }
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(vals)
        self.log_business_action(
            _("Generated payroll export evidence with %(employees)s employees and SHA-256 %(hash)s.",
              employees=len(rows), hash=digest)
        )
        return display_notification(
            _("Payroll CSV generated for %s employee(s).") % len(rows)
        )

    def action_reset_generation(self):
        self.ensure_one()
        require_payroll_officer(self)
        if self.state != "draft" or not self.generated:
            raise UserError(_("Only a generated Draft Payroll Export can reset its generated package."))
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "generated": False,
                "export_file": False,
                "export_filename": False,
                "export_sha256": False,
                "source_rows_json": False,
                "config_snapshot_json": False,
                "employee_count": 0,
                "source_row_count": 0,
                "work_entry_count": 0,
                "work_entry_hours": 0.0,
                "attendance_count": 0,
                "worked_hours": 0.0,
                "rounded_worked_hours": 0.0,
                "overtime_hours": 0.0,
                "paid_leave_days": 0.0,
                "unpaid_leave_days": 0.0,
                "generated_at": False,
                "generated_by_id": False,
            }
        )
        self.log_business_action(
            _("Generated payroll package was reset before changing Draft source scope.")
        )
        return True

    def action_download_export(self):
        self.ensure_one()
        require_payroll_officer(self)
        if not self.export_file or not self.export_filename:
            raise UserError(_("Generate the payroll export before downloading it."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/export_file/%s?download=true"
            % (self._name, self.id, quote(self.export_filename)),
            "target": "self",
        }

    def action_post_to_payroll(self):
        self.ensure_one()
        require_payroll_manager(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Payroll Export can be posted."))
        if not self.generated or not self.export_sha256:
            raise UserError(_("Generate the payroll package before posting it."))
        external_reference = self.config_id._onehr_dispatch_export(self)
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write(
            {
                "state": "posted",
                "external_batch_reference": external_reference or self.external_batch_reference,
                "cancellation_reason": False,
                "posted_at": fields.Datetime.now(),
                "posted_by_id": self.env.user.id,
            }
        )
        self.log_business_action(
            _("Payroll export posted to payroll boundary. Source SHA-256: %s") % self.export_sha256
        )
        return True

    def action_cancel_draft(self):
        self.ensure_one()
        require_payroll_manager(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Payroll Export can be cancelled."))
        if not (self.cancellation_reason or "").strip():
            raise UserError(_("Enter a Cancellation Reason before cancelling the payroll export."))
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write(
            {
                "state": "cancelled",
                "cancelled_at": fields.Datetime.now(),
                "cancelled_by_id": self.env.user.id,
            }
        )
        return True

    def action_schedule_payroll_review(self):
        self.ensure_one()
        require_payroll_officer(self)
        managers = self.env.ref(
            "onehr_payroll_bridge.group_onehr_payroll_manager"
        ).all_user_ids.filtered(lambda user: self.company_id in user.company_ids)
        user = managers[:1] or self.env.user
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Review payroll export %s") % self.name,
            note=_("Review source totals, mapping snapshot, generated CSV and reconciliation readiness."),
        )
        return True

    def action_open_config(self):
        self.ensure_one()
        require_payroll_officer(self)
        return open_record_action(
            name=self.config_id.display_name,
            res_model="onehr.payroll.bridge.config",
            res_id=self.config_id.id,
        )

    def action_open_imports(self):
        self.ensure_one()
        require_payroll_officer(self)
        return open_records_action(
            name=_("Imported Payroll Results — %s") % self.name,
            res_model="onehr.payroll.import",
            domain=[("export_id", "=", self.id)],
            context={"default_export_id": self.id, "default_config_id": self.config_id.id},
            view_mode="list,pivot,graph,form",
        )

    def _decode_vendor_csv(self):
        self.ensure_one()
        if not self.vendor_import_file:
            raise UserError(_("Upload a Vendor Payroll Result CSV first."))
        try:
            payload = base64.b64decode(self.vendor_import_file)
            encoding = self._snapshot_config_value(
                "csv_encoding", self.config_id.csv_encoding
            )
            return payload.decode(encoding)
        except Exception as exc:
            raise UserError(_("Unable to decode the vendor payroll result file: %s") % str(exc)) from exc

    def _normalize_decimal(self, raw_value):
        value = str(raw_value or "").strip()
        if not value:
            return 0.0
        decimal_separator = self._snapshot_config_value(
            "decimal_separator", self.config_id.decimal_separator
        )
        if decimal_separator == ",":
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
        try:
            return float(value)
        except ValueError as exc:
            raise ValidationError(_("Invalid payroll amount '%s'.") % raw_value) from exc

    def action_import_vendor_results(self):
        self.ensure_one()
        require_payroll_officer(self)
        if self.state != "posted":
            raise UserError(_("Vendor payroll results can be imported only for a Posted export."))

        text = self._decode_vendor_csv()
        vendor_bytes = base64.b64decode(self.vendor_import_file)
        vendor_sha256 = hashlib.sha256(vendor_bytes).hexdigest()
        mapping = self._frozen_import_mapping()
        reader = csv.DictReader(io.StringIO(text), delimiter=self._frozen_csv_delimiter_character())
        headers = set(reader.fieldnames or [])
        required_headers = {
            mapping["employee_number"],
            mapping["external_reference"],
            mapping["net_amount"],
        }
        missing_headers = sorted(required_headers - headers)
        if missing_headers:
            raise ValidationError(
                _("Vendor payroll CSV is missing required headers: %s") % ", ".join(missing_headers)
            )

        imported = 0
        updated = 0
        skipped = 0
        Import = self.env["onehr.payroll.import"]

        for row_number, raw_row in enumerate(reader, start=2):
            employee_number = (raw_row.get(mapping["employee_number"]) or "").strip()
            external_reference = (raw_row.get(mapping["external_reference"]) or "").strip()
            if not employee_number or not external_reference:
                raise ValidationError(
                    _("Vendor payroll CSV row %s requires employee number and external reference.") % row_number
                )

            employee = self.env["hr.employee"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("onehr_employee_number", "=", employee_number),
                ],
                limit=1,
            )
            values = {
                "export_id": self.id,
                "config_id": self.config_id.id,
                "company_id": self.company_id.id,
                "employee_id": employee.id or False,
                "employee_number_snapshot": employee_number,
                "external_reference": external_reference,
                "payslip_number": (
                    raw_row.get(mapping.get("payslip_number")) or ""
                    if mapping.get("payslip_number")
                    else ""
                ).strip(),
                "gross_amount": self._normalize_decimal(
                    raw_row.get(mapping.get("gross_amount")) if mapping.get("gross_amount") else 0
                ),
                "deduction_amount": self._normalize_decimal(
                    raw_row.get(mapping.get("deduction_amount")) if mapping.get("deduction_amount") else 0
                ),
                "net_amount": self._normalize_decimal(raw_row.get(mapping["net_amount"])),
                "employer_cost": self._normalize_decimal(
                    raw_row.get(mapping.get("employer_cost")) if mapping.get("employer_cost") else 0
                ),
                "source_channel": "csv",
                "raw_payload_json": json.dumps(raw_row, ensure_ascii=False, sort_keys=True),
            }
            if mapping.get("payment_date") and raw_row.get(mapping["payment_date"]):
                try:
                    values["payment_date"] = fields.Date.to_date(raw_row[mapping["payment_date"]])
                except Exception as exc:
                    raise ValidationError(
                        _("Invalid ISO Payment Date '%s' on vendor CSV row %s.")
                        % (raw_row[mapping["payment_date"]], row_number)
                    ) from exc
            if mapping.get("currency_code") and raw_row.get(mapping["currency_code"]):
                currency_code = raw_row[mapping["currency_code"]].strip().upper()
                currency = self.env["res.currency"].search(
                    [("name", "=", currency_code)],
                    limit=1,
                )
                if not currency:
                    raise ValidationError(
                        _("Unknown vendor payroll currency '%s' on CSV row %s.")
                        % (currency_code, row_number)
                    )
                values["currency_id"] = currency.id
            else:
                values["currency_id"] = self.currency_id.id

            existing = Import.search(
                [
                    ("export_id", "=", self.id),
                    ("external_reference", "=", external_reference),
                    ("is_current_revision", "=", True),
                ],
                order="revision desc, id desc",
                limit=1,
            )
            if existing:
                if existing.state in {"draft", "error"}:
                    existing.with_context(
                        onehr_payroll_import_evidence_controlled=True
                    ).write(values)
                    updated += 1
                else:
                    if (existing.raw_payload_json or "") != values["raw_payload_json"]:
                        raise UserError(
                            _(
                                "Vendor result '%s' changed after validation. "
                                "Create a governed correction revision instead of overwriting finalized evidence."
                            )
                            % external_reference
                        )
                    skipped += 1
                continue

            Import.create(values)
            imported += 1

        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "vendor_import_sha256": vendor_sha256,
                "vendor_imported_at": fields.Datetime.now(),
                "vendor_imported_by_id": self.env.user.id,
            }
        )
        self.log_business_action(
            _(
                "Vendor payroll CSV processed: %(created)s created, %(updated)s updated, %(skipped)s finalized rows skipped. SHA-256: %(hash)s.",
                created=imported,
                updated=updated,
                skipped=skipped,
                hash=vendor_sha256,
            )
        )
        return display_notification(
            _(
                "Vendor payroll results processed: %(created)s created, %(updated)s updated, %(skipped)s skipped.",
                created=imported,
                updated=updated,
                skipped=skipped,
            )
        )

    def action_validate_imports(self):
        self.ensure_one()
        require_payroll_officer(self)
        if self.state != "posted":
            raise UserError(_("Imported payroll results are validated while the Export is Posted."))
        current = self.import_ids.filtered(lambda row: row.is_current_revision and row.state in {"draft", "error"})
        for row in current:
            row.action_validate()
        errors = self.import_ids.filtered(lambda row: row.is_current_revision and row.state == "error")
        if errors:
            return display_notification(
                _("%s current payroll result(s) still contain validation errors.") % len(errors),
                notification_type="warning",
                sticky=True,
            )
        return display_notification(_("All current payroll results are validated."))

    def _source_employee_numbers(self):
        self.ensure_one()
        try:
            rows = json.loads(self.source_rows_json or "[]")
        except ValueError:
            rows = []
        return {
            str(row.get("employee_number") or "").strip()
            for row in rows
            if str(row.get("employee_number") or "").strip()
        }

    def _current_imports(self):
        self.ensure_one()
        return self.import_ids.filtered("is_current_revision")

    def _validate_reconciliation_ready(self):
        self.ensure_one()
        current = self._current_imports()
        if not current:
            raise UserError(_("No current vendor payroll results exist for reconciliation."))
        invalid = current.filtered(lambda row: row.state != "validated")
        if invalid:
            raise UserError(_("Every current vendor payroll result must be Validated before reconciliation."))

        source_numbers = self._source_employee_numbers()
        imported_numbers = set(current.mapped("employee_number_snapshot"))
        extra = sorted(imported_numbers - source_numbers)
        if extra:
            raise UserError(
                _("Vendor results include employee numbers not present in the frozen export: %s")
                % ", ".join(extra)
            )
        missing = sorted(source_numbers - imported_numbers)
        policy = self._frozen_reconciliation_policy()
        if policy["require_full_reconciliation"] and missing:
            raise UserError(
                _("Full reconciliation is required. Missing vendor results for: %s")
                % ", ".join(missing[:20])
            )
        return True

    def _build_costing_payload(self):
        self.ensure_one()
        current = self._current_imports().filtered(lambda row: row.state in {"validated", "reconciled"})
        totals = {}
        for row in current:
            department = row.department_snapshot or _("Unassigned")
            bucket = totals.setdefault(
                department,
                {
                    "department": department,
                    "gross_amount": 0.0,
                    "deduction_amount": 0.0,
                    "net_amount": 0.0,
                    "employer_cost": 0.0,
                    "employee_count": 0,
                },
            )
            bucket["gross_amount"] += row.gross_amount
            bucket["deduction_amount"] += row.deduction_amount
            bucket["net_amount"] += row.net_amount
            bucket["employer_cost"] += row.employer_cost
            bucket["employee_count"] += 1

        return {
            "export_id": self.id,
            "export_no": self.name,
            "external_batch_reference": self.external_batch_reference,
            "company_id": self.company_id.id,
            "company": self.company_id.name,
            "currency": self.currency_id.name,
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "departments": list(totals.values()),
        }

    def action_reconcile(self):
        self.ensure_one()
        require_payroll_manager(self)
        if self.state != "posted":
            raise UserError(_("Only a Posted payroll export can be reconciled."))
        self._validate_reconciliation_ready()
        costing_payload = self._build_costing_payload()
        current = self._current_imports().filtered(lambda row: row.state == "validated")
        current._mark_reconciled()
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write(
            {
                "state": "reconciled",
                "costing_payload_json": json.dumps(
                    costing_payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                "reconciled_at": fields.Datetime.now(),
                "reconciled_by_id": self.env.user.id,
            }
        )
        self.log_business_action(
            _("Payroll export reconciled. Source evidence SHA-256 remains %s.") % self.export_sha256
        )
        return True

    def action_prepare_costing_payload(self):
        self.ensure_one()
        require_payroll_manager(self)
        if self.state not in {"posted", "reconciled"}:
            raise UserError(_("Costing payload is prepared only after payroll results are available."))
        payload = self._build_costing_payload()
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "costing_payload_json": json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            }
        )
        return display_notification(_("Department costing payload prepared."))

    def onehr_payroll_export_payload(self):
        """Stable integration payload for an explicitly authorized downstream adapter."""
        self.ensure_one()
        require_payroll_officer(self)
        if not self.generated or not self.export_sha256:
            raise UserError(_("Generate the payroll source package before requesting its adapter payload."))
        return {
            "export_id": self.id,
            "export_no": self.name,
            "state": self.state,
            "company_id": self.company_id.id,
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "source_sha256": self.export_sha256,
            "external_batch_reference": self.external_batch_reference,
            "config_snapshot": self._config_snapshot(),
            "rows": json.loads(self.source_rows_json or "[]"),
        }

    @api.depends(
        "import_ids.state",
        "import_ids.is_current_revision",
        "import_ids.employee_number_snapshot",
        "import_ids.gross_amount",
        "import_ids.deduction_amount",
        "import_ids.net_amount",
        "import_ids.employer_cost",
        "source_rows_json",
    )
    def _compute_reconciliation_metrics(self):
        for record in self:
            all_imports = record.import_ids
            current = all_imports.filtered("is_current_revision")
            current_valid = current.filtered(lambda row: row.state in {"validated", "reconciled"})
            source_numbers = record._source_employee_numbers()
            imported_numbers = set(current_valid.mapped("employee_number_snapshot"))
            matched = source_numbers & imported_numbers

            record.import_count = len(all_imports)
            record.current_import_count = len(current)
            record.matched_employee_count = len(matched)
            record.reconciliation_accuracy = (
                round(len(matched) * 100.0 / len(source_numbers), 2)
                if source_numbers
                else 0.0
            )
            record.imported_gross_total = sum(current_valid.mapped("gross_amount"))
            record.imported_deduction_total = sum(current_valid.mapped("deduction_amount"))
            record.imported_net_total = sum(current_valid.mapped("net_amount"))
            record.imported_employer_cost_total = sum(current_valid.mapped("employer_cost"))

    @api.depends("posted_at", "reconciled_at")
    def _compute_time_to_close(self):
        for record in self:
            if record.posted_at and record.reconciled_at:
                delta = record.reconciled_at - record.posted_at
                record.time_to_close_hours = delta.total_seconds() / 3600.0
            else:
                record.time_to_close_hours = 0.0
