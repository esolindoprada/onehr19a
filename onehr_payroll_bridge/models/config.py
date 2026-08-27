import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action
from .authority_helpers import require_payroll_manager, require_payroll_officer


DEFAULT_EXPORT_MAPPING = json.dumps(
    {
        "employee_number": "employee_number",
        "employee_name": "employee_name",
        "company": "company",
        "department": "department",
        "job": "job",
        "grade": "grade",
        "position": "position",
        "salary_structure_code": "salary_structure_code",
        "period_start": "period_start",
        "period_end": "period_end",
        "work_entry_count": "work_entry_count",
        "work_entry_hours": "work_entry_hours",
        "work_entries_json": "work_entries_json",
        "attendance_count": "attendance_count",
        "worked_hours": "worked_hours",
        "rounded_worked_hours": "rounded_worked_hours",
        "late_minutes": "late_minutes",
        "early_leave_minutes": "early_leave_minutes",
        "overtime_hours": "overtime_hours",
        "overtime_codes": "overtime_codes",
        "paid_leave_days": "paid_leave_days",
        "unpaid_leave_days": "unpaid_leave_days",
        "costing_json": "costing_json",
        "variables_json": "variables_json",
    },
    indent=2,
)

EXPORT_MAPPING_KEYS = {
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
}

DEFAULT_IMPORT_MAPPING = json.dumps(
    {
        "employee_number": "employee_number",
        "external_reference": "external_reference",
        "payslip_number": "payslip_number",
        "payment_date": "payment_date",
        "gross_amount": "gross_amount",
        "deduction_amount": "deduction_amount",
        "net_amount": "net_amount",
        "employer_cost": "employer_cost",
        "currency_code": "currency_code",
    },
    indent=2,
)

IMPORT_MAPPING_KEYS = {
    "employee_number",
    "external_reference",
    "payslip_number",
    "payment_date",
    "gross_amount",
    "deduction_amount",
    "net_amount",
    "employer_cost",
    "currency_code",
}


class OneHRPayrollBridgeConfig(models.Model):
    """Payroll interchange configuration.

    This model owns transport/mapping policy only. It deliberately does not own
    payroll calculations, tax rules, accounting journals, or external API secrets.
    Every generated export snapshots the mapping used at generation time so later
    configuration edits do not rewrite historical payroll evidence.
    """

    _name = "onehr.payroll.bridge.config"
    _description = "OneHR Payroll Bridge Configuration"
    _inherit = ["onehr.mixin.audit"]
    _order = "company_id, code, id"
    _rec_name = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    provider_mode = fields.Selection(
        [
            ("csv_manual", "CSV / Manual Exchange"),
            ("api_adapter", "External API Adapter"),
            ("oca_adapter", "OCA Payroll Adapter"),
        ],
        required=True,
        default="csv_manual",
        index=True,
        tracking=True,
    )
    external_system_code = fields.Char(
        required=True,
        default="PAYROLL",
        index=True,
        tracking=True,
        help="Stable non-secret code identifying the receiving payroll system.",
    )
    external_endpoint_reference = fields.Char(
        tracking=True,
        help="Non-secret endpoint/adapter reference only. Credentials belong to the integration owner.",
    )

    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        ondelete="restrict",
        tracking=True,
    )
    csv_delimiter = fields.Selection(
        [(",", "Comma"), (";", "Semicolon"), ("tab", "Tab"), ("|", "Pipe")],
        required=True,
        default=",",
        tracking=True,
    )
    csv_encoding = fields.Selection(
        [("utf-8", "UTF-8"), ("utf-8-sig", "UTF-8 with BOM")],
        required=True,
        default="utf-8-sig",
        tracking=True,
    )
    decimal_separator = fields.Selection(
        [(".", "Dot (.)"), (",", "Comma (,)")],
        required=True,
        default=".",
        tracking=True,
    )

    include_work_entries = fields.Boolean(
        default=True,
        tracking=True,
        help="Read existing native Odoo work entries when hr_work_entry is installed; this addon never generates them.",
    )
    include_attendance = fields.Boolean(default=True, tracking=True)
    require_posted_attendance = fields.Boolean(
        default=True,
        tracking=True,
        help="When Attendance is installed, only Posted attendance contributes payroll work variables.",
    )
    include_overtime = fields.Boolean(default=True, tracking=True)
    include_timeoff = fields.Boolean(default=True, tracking=True)
    include_assignment_costing = fields.Boolean(
        default=True,
        tracking=True,
        help="Consume effective assignment costing only when the Assignment addon is installed.",
    )

    require_full_reconciliation = fields.Boolean(
        default=True,
        tracking=True,
        help="Require a current validated vendor result for every employee exported before reconciliation.",
    )
    validate_net_equation = fields.Boolean(
        default=False,
        tracking=True,
        help="Optionally validate gross - deductions = net within the configured tolerance.",
    )
    net_reconciliation_tolerance = fields.Monetary(
        currency_field="currency_id",
        default=1.0,
        tracking=True,
    )

    export_schedule_enabled = fields.Boolean(default=False, tracking=True)
    export_schedule_day = fields.Integer(
        default=1,
        tracking=True,
        help="Day 1-28 when a Draft export for the previous calendar month is prepared automatically.",
    )

    export_field_mapping = fields.Text(
        required=True,
        default=DEFAULT_EXPORT_MAPPING,
        tracking=True,
        help="JSON object mapping canonical OneHR export keys to external CSV headers. Empty values omit a column.",
    )
    import_field_mapping = fields.Text(
        required=True,
        default=DEFAULT_IMPORT_MAPPING,
        tracking=True,
        help="JSON object mapping canonical import keys to vendor CSV headers.",
    )
    grade_structure_mapping = fields.Text(
        default="{}",
        tracking=True,
        help='JSON object such as {"G7": "MONTHLY-MGR"} mapping OneHR grade codes to external payroll structures.',
    )
    position_structure_mapping = fields.Text(
        default="{}",
        tracking=True,
        help='JSON object such as {"POS-001": "EXECUTIVE"}; position mapping takes precedence over grade mapping.',
    )

    export_ids = fields.One2many(
        "onehr.payroll.export",
        "config_id",
        string="Payroll Exports",
        readonly=True,
    )
    import_ids = fields.One2many(
        "onehr.payroll.import",
        "config_id",
        string="Payroll Imports",
        readonly=True,
    )
    export_count = fields.Integer(compute="_compute_counts")
    import_count = fields.Integer(compute="_compute_counts")
    latest_export_id = fields.Many2one("onehr.payroll.export", compute="_compute_counts")

    _config_code_company_unique = models.Constraint(
        "unique(company_id, code)",
        "Payroll Bridge Configuration Code must be unique within a company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_payroll_manager(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("code"):
                values["code"] = values["code"].strip().upper()
            if values.get("external_system_code"):
                values["external_system_code"] = values["external_system_code"].strip().upper()
            prepared.append(values)
        records = super().create(prepared)
        records._validate_configuration()
        return records

    def write(self, values):
        require_payroll_manager(self)
        values = dict(values)
        locked_identity_fields = {"company_id", "code", "currency_id"}
        if locked_identity_fields & set(values):
            for record in self:
                if record.export_ids or record.import_ids:
                    raise AccessError(
                        _("Used Payroll Bridge Configuration company/code/currency are frozen. "
                          "Create a new configuration for a different legal payroll identity.")
                    )
        if values.get("code"):
            values["code"] = values["code"].strip().upper()
        if values.get("external_system_code"):
            values["external_system_code"] = values["external_system_code"].strip().upper()
        result = super().write(values)
        self._validate_configuration()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_used_configuration(self):
        for record in self:
            if record.export_ids or record.import_ids:
                raise AccessError(
                    _("A Payroll Bridge Configuration with payroll evidence cannot be deleted. Archive it instead.")
                )

    @api.constrains(
        "export_schedule_day",
        "net_reconciliation_tolerance",
        "export_field_mapping",
        "import_field_mapping",
        "grade_structure_mapping",
        "position_structure_mapping",
    )
    def _check_configuration(self):
        self._validate_configuration()

    def _parse_mapping(self, field_name, *, required_keys=None, allowed_keys=None):
        self.ensure_one()
        raw = self[field_name] or "{}"
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                _("%(field)s must contain valid JSON: %(error)s", field=field_name, error=str(exc))
            ) from exc
        if not isinstance(value, dict):
            raise ValidationError(_("%s must be a JSON object.") % field_name)
        if allowed_keys is not None:
            unknown_keys = sorted(set(value) - set(allowed_keys))
            if unknown_keys:
                raise ValidationError(
                    _("Unknown canonical mapping key(s) in %(field)s: %(keys)s",
                      field=field_name, keys=", ".join(unknown_keys))
                )

        normalized = {}
        for key, mapped in value.items():
            if not isinstance(key, str):
                raise ValidationError(_("%s JSON keys must be text.") % field_name)
            if mapped in (None, False, ""):
                normalized[key] = ""
            elif not isinstance(mapped, str):
                raise ValidationError(_("%s JSON values must be text or empty.") % field_name)
            else:
                normalized[key] = mapped.strip()
        for key in required_keys or ():
            if not normalized.get(key):
                raise ValidationError(
                    _("Required mapping key '%(key)s' is missing in %(field)s.", key=key, field=field_name)
                )
        non_empty_headers = [value for value in normalized.values() if value]
        if len(non_empty_headers) != len(set(non_empty_headers)):
            raise ValidationError(_("%s contains duplicate external headers.") % field_name)
        return normalized

    def _validate_configuration(self):
        for record in self:
            if not 1 <= record.export_schedule_day <= 28:
                raise ValidationError(_("Scheduled Export Day must be between 1 and 28."))
            if record.net_reconciliation_tolerance < 0:
                raise ValidationError(_("Net Reconciliation Tolerance cannot be negative."))
            record._parse_mapping(
                "export_field_mapping",
                required_keys=("employee_number",),
                allowed_keys=EXPORT_MAPPING_KEYS,
            )
            record._parse_mapping(
                "import_field_mapping",
                required_keys=("employee_number", "external_reference", "net_amount"),
                allowed_keys=IMPORT_MAPPING_KEYS,
            )
            record._parse_mapping("grade_structure_mapping")
            record._parse_mapping("position_structure_mapping")
        return True

    def _compute_counts(self):
        Export = self.env["onehr.payroll.export"]
        Import = self.env["onehr.payroll.import"]
        for record in self:
            record.export_count = Export.search_count([("config_id", "=", record.id)])
            record.import_count = Import.search_count([("config_id", "=", record.id)])
            record.latest_export_id = Export.search(
                [("config_id", "=", record.id)],
                order="period_end desc, id desc",
                limit=1,
            )

    def resolve_salary_structure_code(self, employee):
        """Resolve a stable external structure code without owning salary rules."""
        self.ensure_one()
        position_map = self._parse_mapping("position_structure_mapping")
        grade_map = self._parse_mapping("grade_structure_mapping")

        position = employee.onehr_primary_position_id
        grade = employee.onehr_grade_id

        position_code = position.code if position and "code" in position._fields else ""
        grade_code = grade.code if grade and "code" in grade._fields else ""

        return (
            position_map.get(position_code)
            or grade_map.get(grade_code)
            or ""
        )

    def csv_delimiter_character(self):
        """Translate the human-readable selection value to csv module syntax."""
        self.ensure_one()
        return "\t" if self.csv_delimiter == "tab" else self.csv_delimiter

    def export_mapping_snapshot(self):
        self.ensure_one()
        self._validate_configuration()
        return {
            "config_id": self.id,
            "config_code": self.code,
            "provider_mode": self.provider_mode,
            "external_system_code": self.external_system_code,
            "external_endpoint_reference": self.external_endpoint_reference or "",
            "currency": self.currency_id.name,
            "csv_delimiter": self.csv_delimiter,
            "csv_encoding": self.csv_encoding,
            "decimal_separator": self.decimal_separator,
            "include_work_entries": self.include_work_entries,
            "include_attendance": self.include_attendance,
            "require_posted_attendance": self.require_posted_attendance,
            "include_overtime": self.include_overtime,
            "include_timeoff": self.include_timeoff,
            "include_assignment_costing": self.include_assignment_costing,
            "require_full_reconciliation": self.require_full_reconciliation,
            "validate_net_equation": self.validate_net_equation,
            "net_reconciliation_tolerance": self.net_reconciliation_tolerance,
            "export_field_mapping": self._parse_mapping(
                "export_field_mapping", allowed_keys=EXPORT_MAPPING_KEYS
            ),
            "import_field_mapping": self._parse_mapping(
                "import_field_mapping", allowed_keys=IMPORT_MAPPING_KEYS
            ),
            "grade_structure_mapping": self._parse_mapping("grade_structure_mapping"),
            "position_structure_mapping": self._parse_mapping("position_structure_mapping"),
        }

    def action_validate_configuration(self):
        self.ensure_one()
        require_payroll_manager(self)
        self._validate_configuration()
        return display_notification(_("Payroll Bridge configuration and mapping JSON are valid."))

    def action_open_exports(self):
        self.ensure_one()
        require_payroll_officer(self)
        return open_records_action(
            name=_("Payroll Exports — %s") % self.display_name,
            res_model="onehr.payroll.export",
            domain=[("config_id", "=", self.id)],
            context={"default_config_id": self.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_imports(self):
        self.ensure_one()
        require_payroll_officer(self)
        return open_records_action(
            name=_("Payroll Imports — %s") % self.display_name,
            res_model="onehr.payroll.import",
            domain=[("config_id", "=", self.id)],
            view_mode="list,pivot,graph,form",
        )

    def action_open_latest_export(self):
        self.ensure_one()
        require_payroll_officer(self)
        if not self.latest_export_id:
            return self.action_open_exports()
        return open_record_action(
            name=self.latest_export_id.display_name,
            res_model="onehr.payroll.export",
            res_id=self.latest_export_id.id,
        )

    def _previous_calendar_month(self, today=None):
        self.ensure_one()
        today = fields.Date.to_date(today or fields.Date.context_today(self))
        current_first = today.replace(day=1)
        previous_end = current_first - timedelta(days=1)
        return previous_end.replace(day=1), previous_end

    def action_prepare_previous_month_export(self):
        self.ensure_one()
        require_payroll_officer(self)
        period_start, period_end = self._previous_calendar_month()
        existing = self.env["onehr.payroll.export"].search(
            [
                ("config_id", "=", self.id),
                ("period_start", "=", period_start),
                ("period_end", "=", period_end),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
        )
        export = existing or self.env["onehr.payroll.export"].create(
            {
                "config_id": self.id,
                "period_start": period_start,
                "period_end": period_end,
            }
        )
        return open_record_action(
            name=export.display_name,
            res_model="onehr.payroll.export",
            res_id=export.id,
        )

    @api.model
    def _cron_prepare_scheduled_exports(self):
        """Prepare Draft batches only; automatic payroll posting is intentionally prohibited."""
        today = fields.Date.context_today(self)
        configs = self.search(
            [
                ("active", "=", True),
                ("export_schedule_enabled", "=", True),
                ("export_schedule_day", "=", today.day),
            ]
        )
        for config in configs:
            period_start, period_end = config._previous_calendar_month(today)
            exists = self.env["onehr.payroll.export"].search_count(
                [
                    ("config_id", "=", config.id),
                    ("period_start", "=", period_start),
                    ("period_end", "=", period_end),
                    ("state", "!=", "cancelled"),
                ],
                limit=1,
            )
            if not exists:
                self.env["onehr.payroll.export"].create(
                    {
                        "config_id": config.id,
                        "period_start": period_start,
                        "period_end": period_end,
                    }
                )
        return True

    def _onehr_dispatch_export(self, payroll_export):
        """Adapter hook for an installed payroll transport owner.

        CSV/manual mode requires no transport implementation. API/OCA modes must be
        provided by an addon that explicitly owns that external integration.
        """
        self.ensure_one()
        provider_mode = payroll_export._snapshot_config_value(
            "provider_mode", self.provider_mode
        )
        if provider_mode == "csv_manual":
            return payroll_export.external_batch_reference or payroll_export.name
        raise UserError(
            _(
                "Provider mode '%s' requires an installed payroll transport adapter. "
                "OneHR Payroll Bridge does not own API credentials or an OCA payroll engine."
            )
            % provider_mode
        )
