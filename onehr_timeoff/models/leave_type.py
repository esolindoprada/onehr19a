from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_records_action
from .authority_helpers import require_timeoff_hr


LEAVE_TYPE_LOCKED_STATES = {"active", "retired"}


class OneHRLeaveType(models.Model):
    """Enterprise absence type and entitlement-policy master.

    The model deliberately keeps accrual/carry-over policy on the approved leave
    type master instead of inventing additional policy tables. This keeps the
    OneHR model registry stable while still supporting grade/tenure rules.
    """

    _name = "onehr.leave.type"
    _description = "OneHR Leave Type"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "sequence, code, id"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    sequence = fields.Integer(default=10, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    category = fields.Selection(
        [
            ("annual", "Annual Leave"),
            ("sick", "Sick Leave"),
            ("special", "Special Leave"),
            ("training", "Training Leave"),
            ("unpaid", "Unpaid Leave"),
            ("other", "Other Leave"),
        ],
        required=True,
        default="annual",
        index=True,
        tracking=True,
    )
    description = fields.Text(translate=True)

    paid_leave = fields.Boolean(default=True, tracking=True)
    allocation_required = fields.Boolean(default=True, tracking=True)
    approval_required = fields.Boolean(default=True, tracking=True)
    requires_attachment = fields.Boolean(tracking=True)
    allow_half_day = fields.Boolean(default=True, tracking=True)
    minimum_notice_days = fields.Integer(default=0, tracking=True)
    max_consecutive_days = fields.Float(default=0.0, tracking=True)
    allow_negative_balance = fields.Boolean(default=False, tracking=True)
    negative_balance_limit = fields.Float(default=0.0, tracking=True)

    eligible_grade_ids = fields.Many2many(
        "onehr.grade",
        "onehr_leave_type_grade_rel",
        "leave_type_id",
        "grade_id",
        string="Eligible Grades",
        tracking=True,
        help="Leave is available to all grades when no grade is selected.",
    )
    minimum_service_months = fields.Integer(default=0, tracking=True)

    accrual_enabled = fields.Boolean(default=False, tracking=True)
    accrual_frequency = fields.Selection(
        [("monthly", "Monthly"), ("annual", "Annual")],
        default="annual",
        tracking=True,
    )
    base_accrual_days = fields.Float(
        string="Base Accrual Days",
        default=0.0,
        tracking=True,
        help="Days credited for each configured accrual period.",
    )
    prorate_first_year = fields.Boolean(default=True, tracking=True)
    seniority_step_years = fields.Integer(
        string="Seniority Step (Years)", default=0, tracking=True
    )
    seniority_bonus_days = fields.Float(
        string="Bonus Days per Step", default=0.0, tracking=True
    )
    seniority_max_bonus_days = fields.Float(
        string="Maximum Seniority Bonus", default=0.0, tracking=True
    )
    accrual_cap = fields.Float(
        string="Maximum Accrued Balance",
        default=0.0,
        tracking=True,
        help="Zero means no accrual balance cap.",
    )

    carryover_enabled = fields.Boolean(default=False, tracking=True)
    carryover_cap = fields.Float(
        string="Maximum Carry-over Days",
        default=0.0,
        tracking=True,
        help="Zero means no carry-over cap beyond the available prior-year balance.",
    )
    carryover_expiry_months = fields.Integer(
        string="Carry-over Expiry (Months)", default=3, tracking=True
    )

    team_conflict_mode = fields.Selection(
        [("ignore", "Informational"), ("warn", "Warn"), ("block", "Block")],
        default="warn",
        required=True,
        tracking=True,
    )
    max_team_absent = fields.Integer(
        string="Maximum Concurrent Team Absences",
        default=0,
        tracking=True,
        help="Zero disables the numerical team-absence limit.",
    )

    request_count = fields.Integer(compute="_compute_operational_counts")
    allocation_count = fields.Integer(compute="_compute_operational_counts")
    current_year_allocated_days = fields.Float(compute="_compute_current_year_kpis")
    current_year_used_days = fields.Float(compute="_compute_current_year_kpis")
    current_year_balance_days = fields.Float(compute="_compute_current_year_kpis")
    utilization_rate = fields.Float(compute="_compute_current_year_kpis")


    @api.model_create_multi
    def create(self, vals_list):
        require_timeoff_hr(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft":
                raise AccessError(_("Leave Types must be created in Draft and activated through the governed action."))
            prepared.append(values)
        return super().create(prepared)

    def _write_governed(self, values):
        """Private server-side transition writer; private methods are not RPC actions."""
        return super(OneHRLeaveType, self).write(values)

    def write(self, values):
        require_timeoff_hr(self)
        protected = {
            "company_id", "code", "name", "category", "description", "valid_from", "valid_to",
            "paid_leave", "allocation_required", "approval_required", "requires_attachment",
            "allow_half_day", "minimum_notice_days", "max_consecutive_days",
            "allow_negative_balance", "negative_balance_limit", "eligible_grade_ids",
            "minimum_service_months", "accrual_enabled", "accrual_frequency",
            "base_accrual_days", "prorate_first_year", "seniority_step_years",
            "seniority_bonus_days", "seniority_max_bonus_days", "accrual_cap",
            "carryover_enabled", "carryover_cap", "carryover_expiry_months",
            "team_conflict_mode", "max_team_absent",
        }
        if protected & set(values) and any(record.state in LEAVE_TYPE_LOCKED_STATES for record in self):
            raise AccessError(
                _("Active/retired leave-policy facts are frozen. Retire the policy and create a new effective-dated policy version instead.")
            )
        if "state" in values or "active" in values:
            raise AccessError(_("Leave Type lifecycle can change only through governed actions."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_draft_only(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only Draft Leave Types can be deleted; activated policy history is retained."))

    @api.constrains(
        "minimum_notice_days",
        "max_consecutive_days",
        "negative_balance_limit",
        "minimum_service_months",
        "base_accrual_days",
        "seniority_step_years",
        "seniority_bonus_days",
        "seniority_max_bonus_days",
        "accrual_cap",
        "carryover_cap",
        "carryover_expiry_months",
        "max_team_absent",
    )
    def _check_non_negative_policy_values(self):
        for record in self:
            numeric_fields = {
                "minimum_notice_days": record.minimum_notice_days,
                "max_consecutive_days": record.max_consecutive_days,
                "negative_balance_limit": record.negative_balance_limit,
                "minimum_service_months": record.minimum_service_months,
                "base_accrual_days": record.base_accrual_days,
                "seniority_step_years": record.seniority_step_years,
                "seniority_bonus_days": record.seniority_bonus_days,
                "seniority_max_bonus_days": record.seniority_max_bonus_days,
                "accrual_cap": record.accrual_cap,
                "carryover_cap": record.carryover_cap,
                "carryover_expiry_months": record.carryover_expiry_months,
                "max_team_absent": record.max_team_absent,
            }
            if any(value < 0 for value in numeric_fields.values()):
                raise ValidationError(_("Leave policy numeric limits cannot be negative."))
            if record.allow_negative_balance and record.negative_balance_limit <= 0:
                raise ValidationError(_("A positive Negative Balance Limit is required when negative balance is enabled."))
            if record.accrual_enabled and record.base_accrual_days <= 0:
                raise ValidationError(_("Base Accrual Days must be positive when automatic accrual is enabled."))
            if record.carryover_enabled and record.carryover_expiry_months <= 0:
                raise ValidationError(_("Carry-over Expiry must be at least one month when carry-over is enabled."))

    @api.constrains("company_id", "code", "valid_from", "valid_to")
    def _check_policy_version_overlap(self):
        self._check_no_effective_overlap(
            ["company_id", "code"],
            message=_("Leave Type policy versions with the same company/code cannot overlap."),
        )

    @api.constrains("eligible_grade_ids", "company_id")
    def _check_grade_company_scope(self):
        for record in self:
            invalid = record.eligible_grade_ids.filtered(
                lambda grade: grade.company_id and grade.company_id != record.company_id
            )
            if invalid:
                raise ValidationError(_("Eligible Grades must be global or belong to the Leave Type company."))

    def _compute_operational_counts(self):
        Request = self.env["onehr.leave.request"]
        Allocation = self.env["onehr.leave.allocation"]
        for record in self:
            record.request_count = Request.search_count([("leave_type_id", "=", record.id)])
            record.allocation_count = Allocation.search_count([("leave_type_id", "=", record.id)])

    def _compute_current_year_kpis(self):
        today = fields.Date.context_today(self)
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)
        Allocation = self.env["onehr.leave.allocation"]
        Request = self.env["onehr.leave.request"]
        for record in self:
            allocations = Allocation.search([
                ("leave_type_id", "=", record.id),
                ("state", "=", "confirmed"),
                ("allocation_scope", "=", "single"),
                ("period_start", "<=", year_end),
                ("period_end", ">=", year_start),
            ])
            requests = Request.search([
                ("leave_type_id", "=", record.id),
                ("state", "in", ["approved", "done"]),
                ("date_from", "<=", year_end),
                ("date_to", ">=", year_start),
            ])
            allocated = sum(allocations.mapped("allocated_days"))
            used = sum(requests.mapped("requested_days"))
            record.current_year_allocated_days = allocated
            record.current_year_used_days = used
            record.current_year_balance_days = allocated - used
            record.utilization_rate = (used * 100.0 / allocated) if allocated else 0.0

    def _employee_service_start(self, employee):
        """Use Odoo native employment version start where available.

        Creation date is only a conservative fallback for legacy/imported worker
        rows that have no native contract start populated yet.
        """
        version = employee.version_id
        return (
            (version and version.contract_date_start)
            or (employee.create_date and employee.create_date.date())
            or fields.Date.context_today(self)
        )

    def _service_months(self, employee, as_of_date=None):
        self.ensure_one()
        as_of = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        start = fields.Date.to_date(self._employee_service_start(employee))
        if start > as_of:
            return 0
        delta = relativedelta(as_of, start)
        return delta.years * 12 + delta.months

    def is_employee_eligible(self, employee, as_of_date=None):
        self.ensure_one()
        as_of = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        if self.state != "active" or not self.active or not self.is_effective_on(as_of):
            return False
        if employee.company_id != self.company_id:
            return False
        if self.eligible_grade_ids and employee.onehr_grade_id not in self.eligible_grade_ids:
            return False
        return self._service_months(employee, as_of) >= self.minimum_service_months

    def accrual_days_for_employee(self, employee, period_start):
        """Calculate deterministic entitlement from the visible policy fields."""
        self.ensure_one()
        period_start = fields.Date.to_date(period_start)
        months = self._service_months(employee, period_start)
        years = months // 12
        bonus = 0.0
        if self.seniority_step_years and self.seniority_bonus_days:
            bonus = (years // self.seniority_step_years) * self.seniority_bonus_days
            if self.seniority_max_bonus_days:
                bonus = min(bonus, self.seniority_max_bonus_days)
        days = self.base_accrual_days + bonus

        if self.accrual_frequency == "annual" and self.prorate_first_year:
            service_start = fields.Date.to_date(self._employee_service_start(employee))
            if service_start.year == period_start.year:
                remaining_months = 12 - service_start.month + 1
                days *= remaining_months / 12.0
        return round(days, 4)

    def action_activate(self):
        self.ensure_one()
        require_timeoff_hr(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Leave Type can be activated."))
        self._check_non_negative_policy_values()
        self._write_governed({"state": "active", "active": True})
        self.log_business_action(_("Leave policy activated."))
        return True

    def action_retire(self):
        self.ensure_one()
        require_timeoff_hr(self)
        if self.state != "active":
            raise UserError(_("Only an Active Leave Type can be retired."))
        self._write_governed({
            "state": "retired",
            "active": False,
            "valid_to": self.valid_to or max(fields.Date.context_today(self), self.valid_from),
        })
        self.log_business_action(_("Leave policy retired; historical transactions are retained."))
        return True

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Leave Requests — %s", self.display_name),
            res_model="onehr.leave.request",
            domain=[("leave_type_id", "=", self.id)],
            context={"default_leave_type_id": self.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_allocations(self):
        self.ensure_one()
        return open_records_action(
            name=_("Leave Allocations — %s", self.display_name),
            res_model="onehr.leave.allocation",
            domain=[("leave_type_id", "=", self.id)],
            context={"default_leave_type_id": self.id},
            view_mode="list,pivot,graph,form",
        )

    def action_open_employees_without_balance(self):
        self.ensure_one()
        require_timeoff_hr(self)
        today = fields.Date.context_today(self)
        eligible = self.env["hr.employee"].search([
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ]).filtered(lambda employee: self.is_employee_eligible(employee, today))
        Allocation = self.env["onehr.leave.allocation"]
        without_balance = eligible.filtered(
            lambda employee: Allocation.balance_for_employee(employee, self, today) <= 0.000001
        )
        return open_records_action(
            name=_("Employees Without Balance — %s", self.display_name),
            res_model="hr.employee",
            domain=[("id", "in", without_balance.ids)],
            view_mode="list,form",
        )

    def action_run_accrual_now(self):
        self.ensure_one()
        require_timeoff_hr(self)
        return self.env["onehr.leave.allocation"]._run_accrual_for_types(self)
