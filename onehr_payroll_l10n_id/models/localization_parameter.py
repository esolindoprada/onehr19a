import base64
import csv
import hashlib
import io
import json
from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action
from .regulatory_defaults import (
    DEFAULT_ARTICLE17_JSON,
    DEFAULT_PTKP_MAP_JSON,
    DEFAULT_TER_A_JSON,
    DEFAULT_TER_B_JSON,
    DEFAULT_TER_C_JSON,
    DEFAULT_TER_CATEGORY_MAP_JSON,
    DEFAULT_THR_CALENDAR_JSON,
)


PAYROLL_MANAGER_GROUP = "onehr_payroll_bridge.group_onehr_payroll_manager"

# Only this approved model owns Indonesian localization configuration.
PARAMETER_MODEL = "onehr.payroll.l10n.param"

# The import/export contract is intentionally flat and human-editable.
# JSON-heavy statutory tables remain JSON strings so no fourth/fifth child model is invented.
IMPORTABLE_FIELDS = (
    "default_tax_method",
    "ptkp_map_json",
    "pph21_special_policy_json",
    "ptkp_spouse_combined_addition",
    "job_expense_rate_percent",
    "job_expense_monthly_ceiling",
    "job_expense_annual_ceiling",
    "article17_brackets_json",
    "ter_category_map_json",
    "ter_a_json",
    "ter_b_json",
    "ter_c_json",
    "ter_daily_zero_ceiling",
    "ter_daily_half_percent_ceiling",
    "ter_daily_rate_percent",
    "bpjs_health_enabled",
    "bpjs_health_employer_rate_percent",
    "bpjs_health_employee_rate_percent",
    "bpjs_health_wage_ceiling",
    "bpjs_health_wage_floor_mode",
    "bpjs_health_manual_wage_floor",
    "bpjs_tk_enabled",
    "bpjs_jht_employer_rate_percent",
    "bpjs_jht_employee_rate_percent",
    "bpjs_jkm_employer_rate_percent",
    "bpjs_jp_employer_rate_percent",
    "bpjs_jp_employee_rate_percent",
    "bpjs_jp_wage_ceiling",
    "bpjs_jp_ceiling_effective_from",
    "bpjs_jkk_default_risk",
    "bpjs_jkk_very_low_rate_percent",
    "bpjs_jkk_low_rate_percent",
    "bpjs_jkk_medium_rate_percent",
    "bpjs_jkk_high_rate_percent",
    "bpjs_jkk_very_high_rate_percent",
    "bpjs_jkp_total_rate_percent",
    "bpjs_jkp_government_rate_percent",
    "bpjs_jkp_recompose_jkk_rate_percent",
    "bpjs_jkp_recompose_jkm_rate_percent",
    "thr_enabled",
    "thr_min_service_months",
    "thr_full_service_months",
    "thr_full_month_multiplier",
    "thr_payment_deadline_days_before_holiday",
    "thr_wage_basis",
    "thr_prorata_enabled",
    "thr_holiday_calendar_json",
    "thr_leave_impact_mode",
    "thr_leave_impact_notes",
    "pph21_legal_reference",
    "bpjs_health_legal_reference",
    "bpjs_tk_legal_reference",
    "thr_legal_reference",
    "regulatory_notes",
)

FLOAT_FIELDS = {
    name
    for name in IMPORTABLE_FIELDS
    if (
        "rate_percent" in name
        or name.endswith("_ceiling")
        or name.endswith("_wage_floor")
        or name.endswith("_addition")
        or name.endswith("_multiplier")
    )
}
INTEGER_FIELDS = {
    "thr_min_service_months",
    "thr_full_service_months",
    "thr_payment_deadline_days_before_holiday",
}
BOOLEAN_FIELDS = {
    "bpjs_health_enabled",
    "bpjs_tk_enabled",
    "thr_enabled",
    "thr_prorata_enabled",
}
DATE_FIELDS = {"bpjs_jp_ceiling_effective_from"}

# Changes to any of these values invalidate a prior regulatory review.
REGULATORY_FIELDS = set(IMPORTABLE_FIELDS) | {
    "valid_from",
    "valid_to",
}

def _require_payroll_manager(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group(PAYROLL_MANAGER_GROUP):
        raise AccessError(_("OneHR Payroll Manager authority is required."))
    return True


class OneHRPayrollL10nParam(models.Model):
    """Effective-dated Indonesian payroll-localization parameter bundle.

    The model is deliberately configuration-only. It does not calculate payslips,
    own employee NPWP/PTKP identity, post accounting, execute payments, or expose
    public APIs. Payroll Bridge freezes a reviewed bundle into each generated export.
    """

    _name = "onehr.payroll.l10n.param"
    _description = "OneHR Indonesian Payroll Localization Parameters"
    _inherit = ["onehr.mixin.audit"]
    _order = "company_id, valid_from desc, revision desc, id desc"
    _rec_name = "name"

    _HISTORY_CONTEXT = "onehr_l10n_history_controlled"
    _REVIEW_CONTEXT = "onehr_l10n_review_controlled"
    _DOWNLOAD_CONTEXT = "onehr_l10n_download_controlled"

    # ------------------------------------------------------------------
    # Identity, effective dating and regulatory governance
    # ------------------------------------------------------------------
    name = fields.Char(required=True, default="Indonesia Payroll Parameters", tracking=True)
    code = fields.Char(required=True, default="ID-PAYROLL", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        ondelete="restrict",
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    valid_to = fields.Date(index=True, tracking=True)
    revision = fields.Integer(required=True, default=1, readonly=True, copy=False, index=True)
    predecessor_id = fields.Many2one(
        PARAMETER_MODEL,
        ondelete="restrict",
        readonly=True,
        copy=False,
        index=True,
    )
    successor_ids = fields.One2many(
        PARAMETER_MODEL,
        "predecessor_id",
        string="Successor / Correction Versions",
        readonly=True,
    )

    regulatory_reviewed_on = fields.Date(readonly=True, copy=False, index=True)
    regulatory_reviewed_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    next_regulatory_review_date = fields.Date(readonly=True, copy=False, index=True)
    pph21_legal_reference = fields.Char(
        default="PMK 168 Tahun 2023; PP 58 Tahun 2023; UU PPh sebagaimana diubah UU HPP",
        tracking=True,
    )
    bpjs_health_legal_reference = fields.Char(
        default="Pedoman Iuran PPU BPJS Kesehatan — review terhadap ketentuan berlaku sebelum penggunaan",
        tracking=True,
    )
    bpjs_tk_legal_reference = fields.Char(
        default="PP 44/2015; PP 45/2015; PP 6/2025; ketentuan BPJS Ketenagakerjaan berlaku",
        tracking=True,
    )
    thr_legal_reference = fields.Char(
        default="Permenaker Nomor 6 Tahun 2016",
        tracking=True,
    )
    regulatory_notes = fields.Text(
        help="Document material regulatory assumptions, company interpretation and review evidence.",
        tracking=True,
    )

    is_effective_today = fields.Boolean(compute="_compute_effective_status")
    period_status = fields.Selection(
        [
            ("current", "Effective Today"),
            ("future", "Future"),
            ("historical", "Historical"),
            ("inactive", "Inactive / Superseded"),
        ],
        compute="_compute_effective_status",
    )
    history_count = fields.Integer(compute="_compute_counts")
    payroll_export_count = fields.Integer(compute="_compute_counts")
    parameter_sha256 = fields.Char(compute="_compute_parameter_sha256")

    # Operational inputs for governed actions; not statutory facts.
    next_version_effective_from = fields.Date(copy=False)
    correction_reason = fields.Text(copy=False)
    ter_preview_category = fields.Selection(
        [("A", "TER A"), ("B", "TER B"), ("C", "TER C")],
        default="A",
        copy=False,
    )
    ter_preview_monthly_gross = fields.Monetary(
        currency_field="currency_id",
        copy=False,
    )
    ter_preview_rate_percent = fields.Float(
        compute="_compute_ter_preview",
        digits=(16, 4),
    )

    # Human-friendly parameter interchange without inventing a staging/wizard model.
    import_file = fields.Binary(attachment=False, copy=False)
    import_filename = fields.Char(copy=False)
    import_effective_from = fields.Date(copy=False)
    download_file = fields.Binary(attachment=False, readonly=True, copy=False)
    download_filename = fields.Char(readonly=True, copy=False)

    # ------------------------------------------------------------------
    # PPh21 / PTKP
    # ------------------------------------------------------------------
    default_tax_method = fields.Selection(
        [
            ("gross", "Gross"),
            ("gross_up", "Gross-Up"),
        ],
        required=True,
        default="gross",
        tracking=True,
    )
    ptkp_map_json = fields.Text(
        required=True,
        default=DEFAULT_PTKP_MAP_JSON,
        tracking=True,
        help="PTKP status → annual PTKP amount. Kept as JSON to preserve the one-model Registry contract.",
    )
    pph21_special_policy_json = fields.Text(
        required=True,
        default="{}",
        tracking=True,
        help=(
            "Optional effective-period policy payload for temporary/special PPh21 programs "
            "(for example government-borne incentives). Eligibility/calculation remains the payroll engine's responsibility."
        ),
    )
    ptkp_spouse_combined_addition = fields.Monetary(
        currency_field="currency_id",
        default=54_000_000.0,
        tracking=True,
    )
    job_expense_rate_percent = fields.Float(default=5.0, digits=(16, 4), tracking=True)
    job_expense_monthly_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=500_000.0,
        tracking=True,
    )
    job_expense_annual_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=6_000_000.0,
        tracking=True,
    )
    article17_brackets_json = fields.Text(
        required=True,
        default=DEFAULT_ARTICLE17_JSON,
        tracking=True,
    )
    ter_category_map_json = fields.Text(
        required=True,
        default=DEFAULT_TER_CATEGORY_MAP_JSON,
        tracking=True,
    )
    ter_a_json = fields.Text(required=True, default=DEFAULT_TER_A_JSON, tracking=True)
    ter_b_json = fields.Text(required=True, default=DEFAULT_TER_B_JSON, tracking=True)
    ter_c_json = fields.Text(required=True, default=DEFAULT_TER_C_JSON, tracking=True)
    ter_daily_zero_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=450_000.0,
        tracking=True,
    )
    ter_daily_half_percent_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=2_500_000.0,
        tracking=True,
    )
    ter_daily_rate_percent = fields.Float(default=0.5, digits=(16, 4), tracking=True)

    # ------------------------------------------------------------------
    # BPJS Kesehatan — PPU parameter bundle
    # ------------------------------------------------------------------
    bpjs_health_enabled = fields.Boolean(default=True, tracking=True)
    bpjs_health_employer_rate_percent = fields.Float(default=4.0, digits=(16, 4), tracking=True)
    bpjs_health_employee_rate_percent = fields.Float(default=1.0, digits=(16, 4), tracking=True)
    bpjs_health_wage_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=12_000_000.0,
        tracking=True,
    )
    bpjs_health_wage_floor_mode = fields.Selection(
        [
            ("regional_minimum_wage", "Regional Minimum Wage"),
            ("manual", "Manual Wage Floor"),
        ],
        required=True,
        default="regional_minimum_wage",
        tracking=True,
    )
    bpjs_health_manual_wage_floor = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # BPJS Ketenagakerjaan
    # ------------------------------------------------------------------
    bpjs_tk_enabled = fields.Boolean(default=True, tracking=True)
    bpjs_jht_employer_rate_percent = fields.Float(default=3.7, digits=(16, 4), tracking=True)
    bpjs_jht_employee_rate_percent = fields.Float(default=2.0, digits=(16, 4), tracking=True)
    bpjs_jkm_employer_rate_percent = fields.Float(default=0.3, digits=(16, 4), tracking=True)
    bpjs_jp_employer_rate_percent = fields.Float(default=2.0, digits=(16, 4), tracking=True)
    bpjs_jp_employee_rate_percent = fields.Float(default=1.0, digits=(16, 4), tracking=True)
    bpjs_jp_wage_ceiling = fields.Monetary(
        currency_field="currency_id",
        default=11_086_300.0,
        tracking=True,
        help="2026 reviewed baseline: effective March 2026. This ceiling is adjusted annually; verify before reuse.",
    )
    bpjs_jp_ceiling_effective_from = fields.Date(
        default=lambda self: fields.Date.to_date("2026-03-01"),
        tracking=True,
    )
    bpjs_jkk_default_risk = fields.Selection(
        [
            ("very_low", "Very Low"),
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("very_high", "Very High"),
        ],
        required=True,
        default="very_low",
        tracking=True,
    )
    bpjs_jkk_very_low_rate_percent = fields.Float(default=0.24, digits=(16, 4), tracking=True)
    bpjs_jkk_low_rate_percent = fields.Float(default=0.54, digits=(16, 4), tracking=True)
    bpjs_jkk_medium_rate_percent = fields.Float(default=0.89, digits=(16, 4), tracking=True)
    bpjs_jkk_high_rate_percent = fields.Float(default=1.27, digits=(16, 4), tracking=True)
    bpjs_jkk_very_high_rate_percent = fields.Float(default=1.74, digits=(16, 4), tracking=True)

    # JKP is parameterized for completeness; employee/employer direct deduction remains zero.
    bpjs_jkp_total_rate_percent = fields.Float(default=0.46, digits=(16, 4), tracking=True)
    bpjs_jkp_government_rate_percent = fields.Float(default=0.22, digits=(16, 4), tracking=True)
    bpjs_jkp_recompose_jkk_rate_percent = fields.Float(default=0.14, digits=(16, 4), tracking=True)
    bpjs_jkp_recompose_jkm_rate_percent = fields.Float(default=0.10, digits=(16, 4), tracking=True)

    # ------------------------------------------------------------------
    # THR
    # ------------------------------------------------------------------
    thr_enabled = fields.Boolean(default=True, tracking=True)
    thr_min_service_months = fields.Integer(default=1, tracking=True)
    thr_full_service_months = fields.Integer(default=12, tracking=True)
    thr_full_month_multiplier = fields.Float(default=1.0, digits=(16, 4), tracking=True)
    thr_payment_deadline_days_before_holiday = fields.Integer(default=7, tracking=True)
    thr_wage_basis = fields.Selection(
        [
            ("base_plus_fixed_allowance", "Basic Wage + Fixed Allowance"),
            ("clean_wage", "Clean Wage without Allowance"),
        ],
        required=True,
        default="base_plus_fixed_allowance",
        tracking=True,
    )
    thr_prorata_enabled = fields.Boolean(default=True, tracking=True)
    thr_holiday_calendar_json = fields.Text(
        required=True,
        default=DEFAULT_THR_CALENDAR_JSON,
        tracking=True,
        help='Optional company THR calendar, e.g. [{"code":"eid","date":"2027-...","label":"Idul Fitri"}].',
    )
    thr_leave_impact_mode = fields.Selection(
        [
            ("none", "No Localization Override"),
            ("external_engine", "External Payroll Engine / Company Rule"),
        ],
        required=True,
        default="none",
        tracking=True,
    )
    thr_leave_impact_notes = fields.Text(
        tracking=True,
        help="Optional employer-specific leave impact. No statutory leave deduction is invented by this addon.",
    )

    _code_revision_company_unique = models.Constraint(
        "unique(company_id, code, revision)",
        "Indonesia Payroll Parameter code/revision must be unique within a company.",
    )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.currency_id = self.company_id.currency_id

    # ------------------------------------------------------------------
    # ORM governance
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        _require_payroll_manager(self)
        history_controlled = self.env.context.get(self._HISTORY_CONTEXT)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if not history_controlled and (
                values.get("predecessor_id") or int(values.get("revision") or 1) != 1
            ):
                raise AccessError(
                    _("Localization revision lineage can be created only by governed version/correction actions.")
                )
            values["code"] = (values.get("code") or "ID-PAYROLL").strip().upper()
            company = self.env["res.company"].browse(values.get("company_id") or self.env.company.id)
            values.setdefault("company_id", company.id)
            values.setdefault("currency_id", company.currency_id.id)
            values.setdefault("revision", 1)
            # A newly created/changed parameter is intentionally unreviewed.
            values.update(
                {
                    "regulatory_reviewed_on": False,
                    "regulatory_reviewed_by_id": False,
                    "next_regulatory_review_date": False,
                }
            )
            prepared.append(values)
        records = super().create(prepared)
        records._validate_parameter_set(require_review=False)
        records._check_no_effective_overlap()
        return records

    def write(self, values):
        _require_payroll_manager(self)
        values = dict(values)
        history_controlled = self.env.context.get(self._HISTORY_CONTEXT)
        review_controlled = self.env.context.get(self._REVIEW_CONTEXT)
        download_controlled = self.env.context.get(self._DOWNLOAD_CONTEXT)

        if values.get("code"):
            values["code"] = values["code"].strip().upper()

        lineage_fields = {"revision", "predecessor_id"}
        if lineage_fields & set(values) and not history_controlled:
            raise AccessError(_("Localization revision lineage cannot be rewritten directly."))

        identity_fields = {"company_id", "currency_id", "code"}
        if identity_fields & set(values) and not history_controlled:
            for record in self:
                if (
                    record.payroll_export_count
                    or record.predecessor_id
                    or record.successor_ids
                    or record.regulatory_reviewed_on
                ):
                    raise AccessError(
                        _("Reviewed/used/versioned localization identity cannot be rewritten.")
                    )
            if values.get("company_id") and "currency_id" not in values:
                company = self.env["res.company"].browse(values["company_id"]).exists()
                if not company:
                    raise ValidationError(_("A valid company is required."))
                values["currency_id"] = company.currency_id.id

        review_fields = {
            "regulatory_reviewed_on",
            "regulatory_reviewed_by_id",
            "next_regulatory_review_date",
        }
        if review_fields & set(values) and not review_controlled:
            raise AccessError(_("Regulatory review evidence changes only through the review action."))

        download_fields = {"download_file", "download_filename"}
        if download_fields & set(values) and not download_controlled:
            raise AccessError(_("Generated parameter download evidence is controlled by export actions."))

        changed_regulatory = REGULATORY_FIELDS & set(values)
        if changed_regulatory and not history_controlled:
            for record in self:
                if record.payroll_export_count:
                    raise AccessError(
                        _(
                            "This parameter version is frozen by payroll export evidence. "
                            "Create a new version or governed correction instead."
                        )
                    )
            if not review_controlled:
                values.update(
                    {
                        "regulatory_reviewed_on": False,
                        "regulatory_reviewed_by_id": False,
                        "next_regulatory_review_date": False,
                    }
                )

        if "active" in values and any(record.payroll_export_count for record in self) and not history_controlled:
            raise AccessError(
                _("A used localization version can be superseded only by governed version/correction actions.")
            )

        result = super().write(values)
        if REGULATORY_FIELDS & set(values) or {"active"} & set(values):
            self._validate_parameter_set(require_review=False)
            self._check_no_effective_overlap()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_localization_history(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.payroll_export_count:
                raise AccessError(_("Localization parameters referenced by payroll evidence cannot be deleted."))
            if record.valid_from <= today:
                raise AccessError(
                    _("Effective/historical localization parameters are retained for payroll audit. Archive/supersede them.")
                )
            if record.predecessor_id or record.successor_ids:
                raise AccessError(_("Version-lineage records cannot be deleted."))

    @api.constrains("valid_from", "valid_to", "company_id", "active")
    def _check_effective_dates(self):
        self._validate_parameter_set(require_review=False)
        self._check_no_effective_overlap()

    @api.constrains(
        "job_expense_rate_percent",
        "bpjs_health_employer_rate_percent",
        "bpjs_health_employee_rate_percent",
        "bpjs_jht_employer_rate_percent",
        "bpjs_jht_employee_rate_percent",
        "bpjs_jkm_employer_rate_percent",
        "bpjs_jp_employer_rate_percent",
        "bpjs_jp_employee_rate_percent",
        "bpjs_jkk_very_low_rate_percent",
        "bpjs_jkk_low_rate_percent",
        "bpjs_jkk_medium_rate_percent",
        "bpjs_jkk_high_rate_percent",
        "bpjs_jkk_very_high_rate_percent",
        "bpjs_jkp_total_rate_percent",
        "bpjs_jkp_government_rate_percent",
        "bpjs_jkp_recompose_jkk_rate_percent",
        "bpjs_jkp_recompose_jkm_rate_percent",
        "ter_daily_rate_percent",
    )
    def _check_percentage_ranges(self):
        for record in self:
            for field_name in (
                "job_expense_rate_percent",
                "bpjs_health_employer_rate_percent",
                "bpjs_health_employee_rate_percent",
                "bpjs_jht_employer_rate_percent",
                "bpjs_jht_employee_rate_percent",
                "bpjs_jkm_employer_rate_percent",
                "bpjs_jp_employer_rate_percent",
                "bpjs_jp_employee_rate_percent",
                "bpjs_jkk_very_low_rate_percent",
                "bpjs_jkk_low_rate_percent",
                "bpjs_jkk_medium_rate_percent",
                "bpjs_jkk_high_rate_percent",
                "bpjs_jkk_very_high_rate_percent",
                "bpjs_jkp_total_rate_percent",
                "bpjs_jkp_government_rate_percent",
                "bpjs_jkp_recompose_jkk_rate_percent",
                "bpjs_jkp_recompose_jkm_rate_percent",
                "ter_daily_rate_percent",
            ):
                value = record[field_name]
                if value < 0 or value > 100:
                    raise ValidationError(_("%s must be between 0 and 100 percent.") % field_name)

    # ------------------------------------------------------------------
    # Validation / parsing
    # ------------------------------------------------------------------
    def _parse_json_object(self, field_name):
        self.ensure_one()
        try:
            value = json.loads(self[field_name] or "{}")
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("%s must contain valid JSON.") % field_name) from exc
        if not isinstance(value, dict):
            raise ValidationError(_("%s must be a JSON object.") % field_name)
        return value

    def _parse_json_list(self, field_name):
        self.ensure_one()
        try:
            value = json.loads(self[field_name] or "[]")
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("%s must contain valid JSON.") % field_name) from exc
        if not isinstance(value, list):
            raise ValidationError(_("%s must be a JSON array.") % field_name)
        return value

    def _validate_progressive_table(self, field_name, *, max_key, rate_key):
        self.ensure_one()
        table = self._parse_json_list(field_name)
        if not table:
            raise ValidationError(_("%s cannot be empty.") % field_name)
        previous_max = -1
        for index, row in enumerate(table, start=1):
            if not isinstance(row, dict):
                raise ValidationError(_("%s row %s must be a JSON object.") % (field_name, index))
            if rate_key not in row:
                raise ValidationError(_("%s row %s is missing %s.") % (field_name, index, rate_key))
            try:
                rate = float(row[rate_key])
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("%s row %s has an invalid rate.") % (field_name, index)) from exc
            if not 0 <= rate <= 100:
                raise ValidationError(_("%s row %s rate must be 0..100.") % (field_name, index))

            ceiling = row.get(max_key)
            is_last = index == len(table)
            if ceiling is None:
                if not is_last:
                    raise ValidationError(_("%s may use a null ceiling only on the final row.") % field_name)
                continue
            try:
                ceiling = float(ceiling)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("%s row %s has an invalid ceiling.") % (field_name, index)) from exc
            if ceiling <= previous_max:
                raise ValidationError(_("%s ceilings must be strictly ascending.") % field_name)
            previous_max = ceiling
        if table[-1].get(max_key) is not None:
            raise ValidationError(_("%s final row must use a null/open-ended ceiling.") % field_name)
        return table

    def _validate_thr_calendar(self):
        self.ensure_one()
        rows = self._parse_json_list("thr_holiday_calendar_json")
        seen_codes = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValidationError(_("THR calendar row %s must be a JSON object.") % index)
            code = str(row.get("code") or "").strip()
            label = str(row.get("label") or "").strip()
            date_value = row.get("date")
            if not code or not label or not date_value:
                raise ValidationError(_("THR calendar row %s requires code, label and date.") % index)
            if code in seen_codes:
                raise ValidationError(_("THR calendar code '%s' is duplicated.") % code)
            seen_codes.add(code)
            try:
                fields.Date.to_date(date_value)
            except Exception as exc:
                raise ValidationError(_("THR calendar row %s has an invalid ISO date.") % index) from exc
        return rows

    def _validate_parameter_set(self, *, require_review):
        for record in self:
            if record.valid_to and record.valid_to < record.valid_from:
                raise ValidationError(_("Valid To cannot be earlier than Valid From."))
            if record.company_id and record.currency_id != record.company_id.currency_id:
                raise ValidationError(
                    _("Localization parameter currency must equal the company currency.")
                )

            if record.job_expense_monthly_ceiling < 0 or record.job_expense_annual_ceiling < 0:
                raise ValidationError(_("Job-expense ceilings cannot be negative."))
            if record.job_expense_annual_ceiling < record.job_expense_monthly_ceiling:
                raise ValidationError(_("Annual job-expense ceiling cannot be below the monthly ceiling."))
            if record.ter_daily_half_percent_ceiling < record.ter_daily_zero_ceiling:
                raise ValidationError(_("TER daily upper threshold cannot be below the zero-rate threshold."))

            record._parse_json_object("pph21_special_policy_json")
            ptkp = record._parse_json_object("ptkp_map_json")
            required_ptkp = {"TK/0", "TK/1", "TK/2", "TK/3", "K/0", "K/1", "K/2", "K/3"}
            if set(ptkp) != required_ptkp:
                raise ValidationError(
                    _("PTKP mapping must contain exactly: %s") % ", ".join(sorted(required_ptkp))
                )
            try:
                ptkp_values = [float(value) for value in ptkp.values()]
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Every PTKP amount must be numeric.")) from exc
            if any(value < 0 for value in ptkp_values):
                raise ValidationError(_("PTKP values cannot be negative."))

            category_map = record._parse_json_object("ter_category_map_json")
            if set(category_map) != required_ptkp:
                raise ValidationError(_("TER category mapping must cover every supported PTKP code."))
            if any(value not in {"A", "B", "C"} for value in category_map.values()):
                raise ValidationError(_("TER category mapping values must be A, B or C."))

            record._validate_progressive_table(
                "article17_brackets_json",
                max_key="max_taxable_income",
                rate_key="rate_percent",
            )
            for ter_field in ("ter_a_json", "ter_b_json", "ter_c_json"):
                record._validate_progressive_table(
                    ter_field,
                    max_key="max_gross",
                    rate_key="rate_percent",
                )

            if record.bpjs_health_enabled:
                if abs(
                    record.bpjs_health_employer_rate_percent
                    + record.bpjs_health_employee_rate_percent
                    - 5.0
                ) > 0.0001:
                    raise ValidationError(
                        _("BPJS Kesehatan PPU employer + employee rate must total 5%.")
                    )
                if record.bpjs_health_wage_ceiling <= 0:
                    raise ValidationError(_("BPJS Kesehatan wage ceiling must be positive."))
                if (
                    record.bpjs_health_wage_floor_mode == "manual"
                    and record.bpjs_health_manual_wage_floor <= 0
                ):
                    raise ValidationError(_("Manual BPJS Kesehatan wage floor must be positive."))

            if record.bpjs_tk_enabled:
                if abs(
                    record.bpjs_jht_employer_rate_percent
                    + record.bpjs_jht_employee_rate_percent
                    - 5.7
                ) > 0.0001:
                    raise ValidationError(_("JHT employer + employee rate must total 5.7%."))
                if abs(
                    record.bpjs_jp_employer_rate_percent
                    + record.bpjs_jp_employee_rate_percent
                    - 3.0
                ) > 0.0001:
                    raise ValidationError(_("JP employer + employee rate must total 3%."))
                if record.bpjs_jp_wage_ceiling <= 0:
                    raise ValidationError(_("JP wage ceiling must be positive."))
                if not record.bpjs_jp_ceiling_effective_from:
                    raise ValidationError(_("JP ceiling effective date is required."))
                if record.valid_from < record.bpjs_jp_ceiling_effective_from:
                    raise ValidationError(
                        _(
                            "This parameter bundle starts before the configured JP wage ceiling became effective. "
                            "Use the historically correct JP ceiling/effective date for earlier payroll periods."
                        )
                    )
                if abs(
                    record.bpjs_jkp_government_rate_percent
                    + record.bpjs_jkp_recompose_jkk_rate_percent
                    + record.bpjs_jkp_recompose_jkm_rate_percent
                    - record.bpjs_jkp_total_rate_percent
                ) > 0.0001:
                    raise ValidationError(_("JKP funding components must equal the total JKP rate."))

            if record.thr_enabled:
                if record.thr_min_service_months < 1:
                    raise ValidationError(_("THR minimum service must be at least one month."))
                if record.thr_full_service_months < record.thr_min_service_months:
                    raise ValidationError(_("THR full-service months cannot be below minimum service."))
                if record.thr_full_month_multiplier <= 0:
                    raise ValidationError(_("THR full-month multiplier must be positive."))
                if record.thr_payment_deadline_days_before_holiday < 0:
                    raise ValidationError(_("THR payment deadline days cannot be negative."))
                record._validate_thr_calendar()

            if require_review and not record.regulatory_reviewed_on:
                raise ValidationError(
                    _(
                        "This Indonesian payroll parameter version has not been regulatorily reviewed. "
                        "A Payroll Manager must use 'Mark Regulatory Review Complete' first."
                    )
                )
        return True

    def _check_no_effective_overlap(self):
        for record in self.filtered("active"):
            domain = [
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("active", "=", True),
                ("valid_from", "<=", record.valid_to or "9999-12-31"),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", record.valid_from),
            ]
            if self.search_count(domain, limit=1):
                raise ValidationError(
                    _("Only one active Indonesian payroll parameter version may cover a company/date.")
                )
        return True

    # ------------------------------------------------------------------
    # Derived status / counts / hash
    # ------------------------------------------------------------------
    @api.depends("active", "valid_from", "valid_to")
    def _compute_effective_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if not record.active:
                record.period_status = "inactive"
                record.is_effective_today = False
            elif record.valid_from > today:
                record.period_status = "future"
                record.is_effective_today = False
            elif record.valid_to and record.valid_to < today:
                record.period_status = "historical"
                record.is_effective_today = False
            else:
                record.period_status = "current"
                record.is_effective_today = True

    def _compute_counts(self):
        Export = self.env["onehr.payroll.export"]
        for record in self:
            record.history_count = self.search_count(
                [("company_id", "=", record.company_id.id), ("code", "=", record.code)]
            )
            record.payroll_export_count = Export.search_count(
                [("onehr_l10n_param_id", "=", record.id)]
            )

    @api.depends(
        *tuple(sorted((REGULATORY_FIELDS - {"valid_to"}) | {"company_id", "currency_id", "code", "revision"}))
    )
    def _compute_parameter_sha256(self):
        for record in self:
            material = record._parameter_hash_material()
            canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            record.parameter_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @api.depends("ter_preview_category", "ter_preview_monthly_gross", "ter_a_json", "ter_b_json", "ter_c_json")
    def _compute_ter_preview(self):
        for record in self:
            if record.ter_preview_monthly_gross < 0:
                record.ter_preview_rate_percent = 0.0
            else:
                record.ter_preview_rate_percent = record.onehr_ter_monthly_rate(
                    record.ter_preview_category or "A",
                    record.ter_preview_monthly_gross or 0.0,
                )

    # ------------------------------------------------------------------
    # Parameter services
    # ------------------------------------------------------------------
    @api.model
    def onehr_find_effective_parameter(self, company, as_of_date, *, require_review=True):
        date_value = fields.Date.to_date(as_of_date)
        records = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
                ("valid_from", "<=", date_value),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", date_value),
            ],
            order="valid_from desc, revision desc, id desc",
            limit=2,
        )
        if not records:
            raise ValidationError(
                _("No active Indonesian payroll parameter version covers %s for %s.")
                % (fields.Date.to_string(date_value), company.display_name)
            )
        if len(records) > 1:
            raise ValidationError(
                _("Multiple Indonesian payroll parameter versions overlap for %s.")
                % company.display_name
            )
        records._validate_parameter_set(require_review=require_review)
        if (
            require_review
            and records.next_regulatory_review_date
            and date_value > records.next_regulatory_review_date
        ):
            raise ValidationError(
                _(
                    "The regulatory review on this localization version expires before payroll date %s. "
                    "Create/review the appropriate effective version before payroll generation."
                )
                % fields.Date.to_string(date_value)
            )
        return records

    def onehr_ter_category_for_ptkp(self, ptkp_code):
        self.ensure_one()
        mapping = self._parse_json_object("ter_category_map_json")
        category = mapping.get(str(ptkp_code or "").upper())
        if not category:
            raise ValidationError(_("Unsupported PTKP code '%s'.") % ptkp_code)
        return category

    def onehr_ter_monthly_rate(self, category, gross_monthly):
        self.ensure_one()
        category = str(category or "").upper()
        field_name = {"A": "ter_a_json", "B": "ter_b_json", "C": "ter_c_json"}.get(category)
        if not field_name:
            raise ValidationError(_("TER category must be A, B or C."))
        gross = float(gross_monthly or 0.0)
        if gross < 0:
            raise ValidationError(_("Gross monthly income cannot be negative."))
        table = self._validate_progressive_table(
            field_name,
            max_key="max_gross",
            rate_key="rate_percent",
        )
        for row in table:
            ceiling = row.get("max_gross")
            if ceiling is None or gross <= float(ceiling):
                return float(row["rate_percent"])
        return 0.0

    def onehr_thr_multiplier(self, service_months):
        self.ensure_one()
        months = max(float(service_months or 0.0), 0.0)
        if not self.thr_enabled or months < self.thr_min_service_months:
            return 0.0
        if months >= self.thr_full_service_months or not self.thr_prorata_enabled:
            return self.thr_full_month_multiplier
        return round(
            self.thr_full_month_multiplier * months / self.thr_full_service_months,
            8,
        )

    def _parameter_payload_without_hash(self):
        self.ensure_one()
        return {
            "schema": "onehr.payroll.l10n.id/v1",
            "parameter_id": self.id,
            "code": self.code,
            "revision": self.revision,
            "company_id": self.company_id.id,
            "company": self.company_id.name,
            "currency": self.currency_id.name,
            "valid_from": fields.Date.to_string(self.valid_from),
            "valid_to": fields.Date.to_string(self.valid_to) if self.valid_to else False,
            "regulatory_reviewed_on": (
                fields.Date.to_string(self.regulatory_reviewed_on)
                if self.regulatory_reviewed_on
                else False
            ),
            "legal_references": {
                "pph21": self.pph21_legal_reference or "",
                "bpjs_health": self.bpjs_health_legal_reference or "",
                "bpjs_tk": self.bpjs_tk_legal_reference or "",
                "thr": self.thr_legal_reference or "",
            },
            "pph21": {
                "default_tax_method": self.default_tax_method,
                "ptkp_map": self._parse_json_object("ptkp_map_json"),
                "special_policy": self._parse_json_object("pph21_special_policy_json"),
                "ptkp_spouse_combined_addition": self.ptkp_spouse_combined_addition,
                "job_expense_rate_percent": self.job_expense_rate_percent,
                "job_expense_monthly_ceiling": self.job_expense_monthly_ceiling,
                "job_expense_annual_ceiling": self.job_expense_annual_ceiling,
                "article17_brackets": self._parse_json_list("article17_brackets_json"),
                "ter_category_map": self._parse_json_object("ter_category_map_json"),
                "ter_monthly_usage": "regular_non_final_tax_period",
                "final_tax_period_method": "article17_annual_reconciliation",
                "ter_monthly": {
                    "A": self._parse_json_list("ter_a_json"),
                    "B": self._parse_json_list("ter_b_json"),
                    "C": self._parse_json_list("ter_c_json"),
                },
                "ter_daily": {
                    "zero_rate_max_gross": self.ter_daily_zero_ceiling,
                    "half_percent_max_gross": self.ter_daily_half_percent_ceiling,
                    "rate_percent": self.ter_daily_rate_percent,
                    "above_upper_threshold_rule": "50%_gross_x_article17",
                },
            },
            "bpjs_health": {
                "enabled": self.bpjs_health_enabled,
                "employer_rate_percent": self.bpjs_health_employer_rate_percent,
                "employee_rate_percent": self.bpjs_health_employee_rate_percent,
                "wage_ceiling": self.bpjs_health_wage_ceiling,
                "wage_floor_mode": self.bpjs_health_wage_floor_mode,
                "manual_wage_floor": self.bpjs_health_manual_wage_floor,
            },
            "bpjs_employment": {
                "enabled": self.bpjs_tk_enabled,
                "jht": {
                    "employer_rate_percent": self.bpjs_jht_employer_rate_percent,
                    "employee_rate_percent": self.bpjs_jht_employee_rate_percent,
                },
                "jkm": {
                    "employer_rate_percent": self.bpjs_jkm_employer_rate_percent,
                },
                "jp": {
                    "employer_rate_percent": self.bpjs_jp_employer_rate_percent,
                    "employee_rate_percent": self.bpjs_jp_employee_rate_percent,
                    "wage_ceiling": self.bpjs_jp_wage_ceiling,
                    "ceiling_effective_from": fields.Date.to_string(
                        self.bpjs_jp_ceiling_effective_from
                    ),
                    "annual_review_required": True,
                },
                "jkk": {
                    "default_risk": self.bpjs_jkk_default_risk,
                    "risk_rates_percent": {
                        "very_low": self.bpjs_jkk_very_low_rate_percent,
                        "low": self.bpjs_jkk_low_rate_percent,
                        "medium": self.bpjs_jkk_medium_rate_percent,
                        "high": self.bpjs_jkk_high_rate_percent,
                        "very_high": self.bpjs_jkk_very_high_rate_percent,
                    },
                },
                "jkp": {
                    "total_rate_percent": self.bpjs_jkp_total_rate_percent,
                    "government_rate_percent": self.bpjs_jkp_government_rate_percent,
                    "recompose_jkk_rate_percent": self.bpjs_jkp_recompose_jkk_rate_percent,
                    "recompose_jkm_rate_percent": self.bpjs_jkp_recompose_jkm_rate_percent,
                    "employee_direct_rate_percent": 0.0,
                    "employer_direct_rate_percent": 0.0,
                },
            },
            "thr": {
                "enabled": self.thr_enabled,
                "minimum_service_months": self.thr_min_service_months,
                "full_service_months": self.thr_full_service_months,
                "full_month_multiplier": self.thr_full_month_multiplier,
                "payment_deadline_days_before_holiday": self.thr_payment_deadline_days_before_holiday,
                "wage_basis": self.thr_wage_basis,
                "prorata_enabled": self.thr_prorata_enabled,
                "holiday_calendar": self._parse_json_list("thr_holiday_calendar_json"),
                "leave_impact_mode": self.thr_leave_impact_mode,
                "leave_impact_notes": self.thr_leave_impact_notes or "",
            },
            "regulatory_notes": self.regulatory_notes or "",
        }

    def _parameter_hash_material(self):
        """Return the immutable statutory/configuration material used for SHA-256.

        `valid_to` is intentionally excluded because a governed successor closes an
        older open-ended period after payroll evidence may already reference it.
        Regulatory review timestamps are evidence metadata, not tax/social-security rates.
        """
        self.ensure_one()
        payload = self._parameter_payload_without_hash()
        payload.pop("valid_to", None)
        payload.pop("regulatory_reviewed_on", None)
        return payload

    def onehr_parameter_payload(self, *, as_of_date=None, require_review=True):
        self.ensure_one()
        self._validate_parameter_set(require_review=require_review)
        if as_of_date:
            date_value = fields.Date.to_date(as_of_date)
            if date_value < self.valid_from or (self.valid_to and date_value > self.valid_to):
                raise ValidationError(
                    _("This localization version is not effective on %s.")
                    % fields.Date.to_string(date_value)
                )
            if not self.active:
                raise ValidationError(_("This localization version is inactive/superseded."))
        payload = self._parameter_payload_without_hash()
        canonical = json.dumps(
            self._parameter_hash_material(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        payload["parameter_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return payload

    # ------------------------------------------------------------------
    # Governed history / review actions
    # ------------------------------------------------------------------
    def action_validate_parameters(self):
        self.ensure_one()
        _require_payroll_manager(self)
        self._validate_parameter_set(require_review=False)
        self._check_no_effective_overlap()
        message = _("Parameter structure is valid.")
        if not self.regulatory_reviewed_on:
            message += _(" Regulatory review is still required before payroll export.")
            return display_notification(message, notification_type="warning", sticky=True)
        return display_notification(message)

    def action_mark_regulatory_reviewed(self):
        self.ensure_one()
        _require_payroll_manager(self)
        if self.payroll_export_count:
            raise UserError(_("A used parameter version is already frozen and cannot receive new review evidence."))
        self._validate_parameter_set(require_review=False)
        today = fields.Date.context_today(self)
        self.with_context(**{self._REVIEW_CONTEXT: True}).write(
            {
                "regulatory_reviewed_on": today,
                "regulatory_reviewed_by_id": self.env.user.id,
                "next_regulatory_review_date": today + timedelta(days=365),
            }
        )
        self.message_post(
            body=_("Regulatory review completed by %s on %s.")
            % (self.env.user.display_name, fields.Date.to_string(today))
        )
        return display_notification(_("Regulatory review evidence recorded."))

    def _next_revision(self):
        self.ensure_one()
        latest = self.search(
            [("company_id", "=", self.company_id.id), ("code", "=", self.code)],
            order="revision desc, id desc",
            limit=1,
        )
        return (latest.revision or 0) + 1

    def _version_copy_values(self, *, valid_from, valid_to=False, active=True, reason=None):
        self.ensure_one()
        return {
            "name": self.name,
            "code": self.code,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "active": active,
            "revision": self._next_revision(),
            "predecessor_id": self.id,
            "regulatory_reviewed_on": False,
            "regulatory_reviewed_by_id": False,
            "next_regulatory_review_date": False,
            "next_version_effective_from": False,
            "correction_reason": reason or False,
            "import_file": False,
            "import_filename": False,
            "import_effective_from": False,
            "download_file": False,
            "download_filename": False,
        }

    def action_create_new_version(self):
        self.ensure_one()
        _require_payroll_manager(self)
        effective_from = self.next_version_effective_from
        if not effective_from:
            raise UserError(_("Enter Next Version Effective From first."))
        if effective_from <= self.valid_from:
            raise ValidationError(_("A new version must start after this version's Valid From date."))
        if self.valid_to and effective_from > self.valid_to + timedelta(days=1):
            raise ValidationError(
                _("The new version would leave an unexplained gap after the current version.")
            )

        new_valid_to = effective_from - timedelta(days=1)
        self.with_context(**{self._HISTORY_CONTEXT: True}).write({"valid_to": new_valid_to})
        self.message_post(
            body=_("Effective period closed at %s by governed successor creation.")
            % fields.Date.to_string(new_valid_to)
        )
        successor = self.with_context(
            **{self._HISTORY_CONTEXT: True}
        ).copy(
            self._version_copy_values(valid_from=effective_from)
        )
        successor.message_post(
            body=_("New effective-dated localization version created from %s.") % self.display_name
        )
        return open_record_action(
            name=successor.display_name,
            res_model=self._name,
            res_id=successor.id,
        )

    def action_create_correction(self):
        self.ensure_one()
        _require_payroll_manager(self)
        if not (self.correction_reason or "").strip():
            raise UserError(_("Enter a Correction Reason before creating a correction version."))

        self.with_context(**{self._HISTORY_CONTEXT: True}).write({"active": False})
        correction = self.with_context(
            **{self._HISTORY_CONTEXT: True}
        ).copy(
            self._version_copy_values(
                valid_from=self.valid_from,
                valid_to=self.valid_to,
                active=True,
                reason=self.correction_reason.strip(),
            )
        )
        correction.message_post(
            body=_("Governed correction created. Superseded revision: %s. Reason: %s")
            % (self.revision, self.correction_reason.strip())
        )
        return open_record_action(
            name=correction.display_name,
            res_model=self._name,
            res_id=correction.id,
        )

    def action_open_history(self):
        self.ensure_one()
        _require_payroll_manager(self)
        return open_records_action(
            name=_("Localization Parameter History — %s") % self.code,
            res_model=self._name,
            domain=[("company_id", "=", self.company_id.id), ("code", "=", self.code)],
            view_mode="list,calendar,form",
        )

    def action_open_payroll_exports(self):
        self.ensure_one()
        _require_payroll_manager(self)
        return open_records_action(
            name=_("Payroll Exports Using %s") % self.display_name,
            res_model="onehr.payroll.export",
            domain=[("onehr_l10n_param_id", "=", self.id)],
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_record(self):
        self.ensure_one()
        _require_payroll_manager(self)
        return open_record_action(
            name=self.display_name,
            res_model=self._name,
            res_id=self.id,
        )

    def action_preview_ter_rate(self):
        self.ensure_one()
        _require_payroll_manager(self)
        rate = self.onehr_ter_monthly_rate(
            self.ter_preview_category,
            self.ter_preview_monthly_gross,
        )
        return display_notification(
            _("TER %(category)s for gross %(gross)s is %(rate).2f%%.",
              category=self.ter_preview_category,
              gross=self.ter_preview_monthly_gross,
              rate=rate)
        )

    # ------------------------------------------------------------------
    # JSON / CSV parameter interchange
    # ------------------------------------------------------------------
    def _serialize_importable_fields(self):
        self.ensure_one()
        values = {}
        for field_name in IMPORTABLE_FIELDS:
            value = self[field_name]
            if field_name in DATE_FIELDS:
                value = fields.Date.to_string(value) if value else ""
            values[field_name] = value
        return values

    def _prepare_download(self, content, filename):
        self.ensure_one()
        self.with_context(**{self._DOWNLOAD_CONTEXT: True}).write(
            {
                "download_file": base64.b64encode(content),
                "download_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/download_file/%s?download=true"
            % (self._name, self.id, quote(filename)),
            "target": "self",
        }

    def action_download_json(self):
        self.ensure_one()
        _require_payroll_manager(self)
        document = {
            "schema": "onehr.payroll.l10n.param-import/v1",
            "source": {
                "code": self.code,
                "revision": self.revision,
                "company": self.company_id.name,
                "valid_from": fields.Date.to_string(self.valid_from),
                "valid_to": fields.Date.to_string(self.valid_to) if self.valid_to else False,
                "parameter_sha256": self.parameter_sha256,
            },
            "parameters": self._serialize_importable_fields(),
        }
        content = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        return self._prepare_download(
            content,
            "%s-R%s-parameters.json" % (self.code, self.revision),
        )

    def action_download_csv(self):
        self.ensure_one()
        _require_payroll_manager(self)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["parameter", "value"])
        for key, value in self._serialize_importable_fields().items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            writer.writerow([key, value if value is not False else ""])
        return self._prepare_download(
            output.getvalue().encode("utf-8-sig"),
            "%s-R%s-parameters.csv" % (self.code, self.revision),
        )

    def _decode_import_document(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Upload a JSON or CSV parameter file first."))
        try:
            raw = base64.b64decode(self.import_file)
            text = raw.decode("utf-8-sig")
        except Exception as exc:
            raise ValidationError(_("Unable to decode the parameter import file.")) from exc

        if text.lstrip().startswith("{"):
            try:
                document = json.loads(text)
            except ValueError as exc:
                raise ValidationError(_("Parameter JSON is invalid.")) from exc
            parameters = document.get("parameters") if isinstance(document, dict) else None
            if not isinstance(parameters, dict):
                raise ValidationError(_("Parameter JSON requires a 'parameters' object."))
            return parameters

        reader = csv.DictReader(io.StringIO(text))
        if set(reader.fieldnames or []) != {"parameter", "value"}:
            raise ValidationError(_("Parameter CSV must contain exactly 'parameter,value' headers."))
        parameters = {}
        for row in reader:
            key = (row.get("parameter") or "").strip()
            if not key:
                continue
            if key in parameters:
                raise ValidationError(_("Parameter CSV contains duplicate key '%s'.") % key)
            parameters[key] = row.get("value")
        return parameters

    def _convert_import_value(self, field_name, value):
        if field_name in BOOLEAN_FIELDS:
            if isinstance(value, bool):
                return value
            normalized = str(value or "").strip().lower()
            if normalized in {"1", "true", "yes", "y"}:
                return True
            if normalized in {"0", "false", "no", "n", ""}:
                return False
            raise ValidationError(_("Invalid boolean for %s.") % field_name)
        if field_name in INTEGER_FIELDS:
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Invalid integer for %s.") % field_name) from exc
        if field_name in FLOAT_FIELDS:
            try:
                return float(value or 0.0)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Invalid number for %s.") % field_name) from exc
        if field_name in DATE_FIELDS:
            try:
                return fields.Date.to_date(value) if value else False
            except Exception as exc:
                raise ValidationError(_("Invalid ISO date for %s.") % field_name) from exc
        if field_name.endswith("_json"):
            # Normalize while validating JSON syntax. Object-style fields are explicit;
            # statutory bracket/calendar tables use arrays.
            object_fields = {
                "ptkp_map_json",
                "ter_category_map_json",
                "pph21_special_policy_json",
            }
            empty_value = "{}" if field_name in object_fields else "[]"
            try:
                parsed = json.loads(value or empty_value)
            except ValueError as exc:
                raise ValidationError(_("Invalid JSON value for %s.") % field_name) from exc
            return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
        return value if value is not None else ""

    def action_import_as_new_version(self):
        self.ensure_one()
        _require_payroll_manager(self)
        if not self.import_effective_from:
            raise UserError(_("Enter Import Effective From first."))
        if self.import_effective_from <= self.valid_from:
            raise ValidationError(
                _("Parameter import creates a new version and must start after this version.")
            )

        raw_parameters = self._decode_import_document()
        unknown = sorted(set(raw_parameters) - set(IMPORTABLE_FIELDS))
        if unknown:
            raise ValidationError(
                _("Unknown localization parameter key(s): %s") % ", ".join(unknown)
            )
        missing = sorted(set(IMPORTABLE_FIELDS) - set(raw_parameters))
        if missing:
            raise ValidationError(
                _("Imported parameter set is incomplete. Missing: %s") % ", ".join(missing)
            )

        imported_values = {
            key: self._convert_import_value(key, raw_parameters[key])
            for key in IMPORTABLE_FIELDS
        }

        new_valid_to = self.import_effective_from - timedelta(days=1)
        self.with_context(**{self._HISTORY_CONTEXT: True}).write({"valid_to": new_valid_to})
        values = self._version_copy_values(valid_from=self.import_effective_from)
        values.update(imported_values)
        imported = self.with_context(
            **{self._HISTORY_CONTEXT: True}
        ).copy(values)
        imported._validate_parameter_set(require_review=False)
        imported.message_post(
            body=_("Localization parameter version created from imported JSON/CSV parameters.")
        )
        return open_record_action(
            name=imported.display_name,
            res_model=self._name,
            res_id=imported.id,
        )
