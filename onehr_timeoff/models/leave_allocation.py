from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_timeoff_hr


class OneHRLeaveAllocation(models.Model):
    """Immutable entitlement/allocation evidence and mass-allocation batch.

    A mass allocation is represented by the same approved persistent model with
    ``allocation_scope='mass'``. Generated employee allocations are durable child
    rows. This provides wizard-like UX without inventing an unregistered transient
    business model or losing batch audit evidence.
    """

    _name = "onehr.leave.allocation"
    _description = "OneHR Leave Allocation"
    _inherit = ["onehr.mixin.audit"]
    _order = "period_start desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Allocation No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    allocation_scope = fields.Selection(
        [("single", "Single Employee"), ("mass", "Mass Allocation Batch")],
        required=True,
        default="single",
        index=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_timeoff.group_onehr_timeoff_hr",
    )
    employee_name = fields.Char(
        related="employee_id.name", store=True, compute_sudo=True, readonly=True, index=True
    )
    employee_user_id = fields.Many2one(
        "res.users", related="employee_id.user_id", store=True, readonly=True, index=True
    )
    manager_user_id = fields.Many2one(
        "res.users", related="employee_id.parent_id.user_id", store=True, readonly=True, index=True
    )
    employee_ids = fields.Many2many(
        "hr.employee",
        "onehr_leave_allocation_batch_employee_rel",
        "allocation_id",
        "employee_id",
        string="Employees",
        check_company=True,
        tracking=True,
        groups="onehr_timeoff.group_onehr_timeoff_hr",
    )
    leave_type_id = fields.Many2one(
        "onehr.leave.type",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
    )
    source = fields.Selection(
        [
            ("manual", "Manual Allocation"),
            ("opening", "Opening Balance"),
            ("accrual", "Automatic Accrual"),
            ("carryover", "Carry-over"),
            ("adjustment", "HR Adjustment"),
            ("mass", "Mass Allocation"),
        ],
        required=True,
        default="manual",
        index=True,
        tracking=True,
    )
    period_start = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)
    expires_on = fields.Date(index=True, tracking=True)
    allocated_days = fields.Float(required=True, default=0.0, tracking=True)
    note = fields.Text(tracking=True)

    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    source_key = fields.Char(
        copy=False,
        index=True,
        readonly=True,
        help="Idempotency key for scheduler-generated entitlement rows.",
    )
    batch_parent_id = fields.Many2one(
        "onehr.leave.allocation",
        string="Mass Allocation Batch",
        ondelete="restrict",
        copy=False,
        index=True,
        readonly=True,
    )
    generated_allocation_ids = fields.One2many(
        "onehr.leave.allocation", "batch_parent_id", string="Generated Allocations", readonly=True
    )
    generated_count = fields.Integer(compute="_compute_generated_count")
    used_days = fields.Float(compute="_compute_balance_summary")
    available_days = fields.Float(compute="_compute_balance_summary")

    _allocation_number_unique = models.Constraint(
        "unique(name)", "Leave Allocation Number must be unique."
    )
    _allocation_source_key_unique = models.Constraint(
        "unique(source_key)", "Leave allocation source key must be unique."
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_timeoff_hr(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft":
                raise AccessError(_("Leave Allocations must be created in Draft and confirmed through governed actions."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.leave.allocation") or _("New")
            prepared.append(values)
        records = super().create(prepared)
        records._validate_allocation_integrity()
        return records

    def _write_governed(self, values):
        """Private server-side writer for lifecycle transitions/system generation."""
        return super(OneHRLeaveAllocation, self).write(values)

    def write(self, values):
        require_timeoff_hr(self)
        if "state" in values:
            raise AccessError(_("Leave Allocation state can change only through governed actions."))
        protected = {
            "company_id", "allocation_scope", "employee_id", "employee_ids",
            "leave_type_id", "source", "period_start", "period_end", "expires_on",
            "allocated_days", "source_key", "batch_parent_id",
        }
        if protected & set(values) and any(record.state != "draft" for record in self):
            raise AccessError(_("Confirmed/cancelled allocation evidence is frozen. Create an adjustment instead."))
        result = super().write(values)
        if protected & set(values):
            self._validate_allocation_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_draft_only(self):
        require_timeoff_hr(self)
        if any(record.state != "draft" for record in self):
            raise AccessError(_("Only Draft allocation rows can be deleted; confirmed entitlement history is retained."))

    @api.constrains(
        "company_id",
        "allocation_scope",
        "employee_id",
        "employee_ids",
        "leave_type_id",
        "period_start",
        "period_end",
        "expires_on",
        "allocated_days",
    )
    def _check_allocation_integrity(self):
        self._validate_allocation_integrity()

    def _validate_allocation_integrity(self):
        for record in self:
            if record.period_end < record.period_start:
                raise ValidationError(_("Allocation Period End cannot be before Period Start."))
            if record.expires_on and record.expires_on < record.period_start:
                raise ValidationError(_("Allocation Expiry cannot be before Period Start."))
            if record.allocated_days <= 0:
                raise ValidationError(_("Allocated Days must be greater than zero."))
            if record.leave_type_id.company_id != record.company_id:
                raise ValidationError(_("Leave Type and Allocation must belong to the same company."))
            if record.allocation_scope == "single":
                if not record.employee_id:
                    raise ValidationError(_("Single Employee allocation requires an Employee."))
                if record.employee_ids:
                    raise ValidationError(_("Single Employee allocation cannot contain a Mass Employee list."))
                if record.employee_id.company_id != record.company_id:
                    raise ValidationError(_("Employee and Allocation must belong to the same company."))
            else:
                if record.employee_id:
                    raise ValidationError(_("Mass Allocation Batch cannot have a single Employee."))
                if record.employee_ids.filtered(lambda employee: employee.company_id != record.company_id):
                    raise ValidationError(_("Every Mass Allocation employee must belong to the batch company."))
        return True

    @api.depends("generated_allocation_ids")
    def _compute_generated_count(self):
        for record in self:
            record.generated_count = len(record.generated_allocation_ids)

    def _compute_balance_summary(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.allocation_scope != "single" or record.state != "confirmed":
                record.used_days = 0.0
                record.available_days = 0.0
                continue
            used = record.used_days_as_of(today, include_future_reservations=True)
            record.used_days = used
            record.available_days = max(record.allocated_days - used, 0.0)

    def _usage_entries_from_requests(self, as_of_date=None, include_future_reservations=False):
        self.ensure_one()
        Request = self.env["onehr.leave.request"]
        domain = [
            ("state", "in", ["approved", "done"]),
            ("allocation_ids", "in", [self.id]),
        ]
        if as_of_date and not include_future_reservations:
            domain.append(("date_from", "<=", fields.Date.to_date(as_of_date)))
        requests = Request.search(domain)
        entries = []
        for request in requests:
            for item in request.allocation_usage_json or []:
                if item.get("allocation_id") == self.id:
                    entries.append((request, float(item.get("days") or 0.0)))
        return entries

    def used_days_as_of(self, as_of_date=None, include_future_reservations=False):
        self.ensure_one()
        return sum(days for _request, days in self._usage_entries_from_requests(as_of_date, include_future_reservations))

    def available_on(self, as_of_date, include_future_reservations=False):
        self.ensure_one()
        as_of = fields.Date.to_date(as_of_date)
        if self.state != "confirmed" or self.allocation_scope != "single":
            return 0.0
        if as_of < self.period_start or as_of > self.period_end:
            return 0.0
        if self.expires_on and as_of > self.expires_on:
            return 0.0
        used = self.used_days_as_of(as_of, include_future_reservations=include_future_reservations)
        return max(self.allocated_days - used, 0.0)

    @api.model
    def _negative_reserved_days(self, employee, leave_type, as_of_date=None, include_future_reservations=False):
        domain = [
            ("employee_id", "=", employee.id),
            ("leave_type_id", "=", leave_type.id),
            ("state", "in", ["approved", "done"]),
            ("allocation_usage_json", "!=", False),
        ]
        if as_of_date and not include_future_reservations:
            domain.append(("date_from", "<=", fields.Date.to_date(as_of_date)))
        requests = self.env["onehr.leave.request"].search(domain)
        return sum(
            float(item.get("days") or 0.0)
            for request in requests
            for item in (request.allocation_usage_json or [])
            if item.get("negative")
        )

    @api.model
    def balance_for_employee(self, employee, leave_type, as_of_date=None, include_future_reservations=False):
        as_of = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        allocations = self.search([
            ("allocation_scope", "=", "single"),
            ("employee_id", "=", employee.id),
            ("leave_type_id", "=", leave_type.id),
            ("state", "=", "confirmed"),
            ("period_start", "<=", as_of),
            ("period_end", ">=", as_of),
            "|", ("expires_on", "=", False), ("expires_on", ">=", as_of),
        ])
        positive_balance = sum(
            allocation.available_on(as_of, include_future_reservations=include_future_reservations)
            for allocation in allocations
        )
        negative_reserved = self._negative_reserved_days(
            employee, leave_type, as_of, include_future_reservations=include_future_reservations
        )
        return positive_balance - negative_reserved

    @api.model
    def usable_allocations_for_request(self, employee, leave_type, request_date):
        request_date = fields.Date.to_date(request_date)
        return self.search([
            ("allocation_scope", "=", "single"),
            ("employee_id", "=", employee.id),
            ("leave_type_id", "=", leave_type.id),
            ("state", "=", "confirmed"),
            ("period_start", "<=", request_date),
            ("period_end", ">=", request_date),
            "|", ("expires_on", "=", False), ("expires_on", ">=", request_date),
        ], order="expires_on asc, period_end asc, period_start asc, id asc")

    def action_confirm(self):
        for record in self:
            require_timeoff_hr(record)
            if record.state != "draft":
                raise UserError(_("Only Draft allocations can be confirmed."))
            record._validate_allocation_integrity()
            if record.allocation_scope == "mass":
                raise UserError(_("Use Generate Allocations for a Mass Allocation Batch."))
            if not record.leave_type_id.is_employee_eligible(record.employee_id, record.period_start):
                raise ValidationError(_("Employee is not eligible for this Leave Type on the allocation start date."))
            record._write_governed({"state": "confirmed"})
            record.log_business_action(_("Leave entitlement confirmed."))
        return True

    def action_cancel(self):
        for record in self:
            require_timeoff_hr(record)
            if record.state != "confirmed":
                raise UserError(_("Only a Confirmed allocation can be cancelled."))
            if record.allocation_scope == "mass":
                used_children = record.generated_allocation_ids.filtered(
                    lambda child: child.used_days_as_of(
                        fields.Date.context_today(child), include_future_reservations=True
                    ) > 0.000001
                )
                if used_children:
                    raise UserError(_("The mass batch cannot be cancelled because one or more generated allocations are already reserved/used."))
                record.generated_allocation_ids._write_governed({"state": "cancelled"})
            elif record.used_days_as_of(
                fields.Date.context_today(record), include_future_reservations=True
            ) > 0.000001:
                raise UserError(_("An allocation already reserved/used by approved leave cannot be cancelled. Create an HR adjustment instead."))
            record._write_governed({"state": "cancelled"})
            record.log_business_action(_("Leave entitlement cancelled by HR."))
        return True

    def action_generate_mass_allocations(self):
        self.ensure_one()
        require_timeoff_hr(self)
        if self.allocation_scope != "mass" or self.state != "draft":
            raise UserError(_("Generate Allocations is available only on a Draft Mass Allocation Batch."))
        if not self.employee_ids:
            raise ValidationError(_("Select at least one employee for the mass allocation."))

        generated = self.browse()
        for employee in self.employee_ids:
            if not self.leave_type_id.is_employee_eligible(employee, self.period_start):
                continue
            source_key = f"MASS:{self.id}:{employee.id}"
            existing = self.search([("source_key", "=", source_key)], limit=1)
            if existing:
                generated |= existing
                continue
            child = self.create({
                "company_id": self.company_id.id,
                "allocation_scope": "single",
                "employee_id": employee.id,
                "leave_type_id": self.leave_type_id.id,
                "source": "mass",
                "period_start": self.period_start,
                "period_end": self.period_end,
                "expires_on": self.expires_on,
                "allocated_days": self.allocated_days,
                "source_key": source_key,
                "batch_parent_id": self.id,
                "note": _("Generated from mass allocation batch %s", self.name),
            })
            child._write_governed({"state": "confirmed"})
            generated |= child

        if not generated:
            raise ValidationError(_("No selected employee is eligible for this Leave Type and period."))
        self._write_governed({"state": "confirmed"})
        self.log_business_action(_("Generated %(count)s employee allocations.", count=len(generated)))
        return self.action_open_generated_allocations()

    def action_open_employee(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_("This batch does not represent a single employee."))
        return open_record_action(
            name=self.employee_id.display_name,
            res_model="hr.employee",
            res_id=self.employee_id.id,
        )

    def action_open_leave_type(self):
        self.ensure_one()
        return open_record_action(
            name=self.leave_type_id.display_name,
            res_model="onehr.leave.type",
            res_id=self.leave_type_id.id,
        )

    def action_open_generated_allocations(self):
        self.ensure_one()
        return open_records_action(
            name=_("Generated Allocations — %s", self.name),
            res_model="onehr.leave.allocation",
            domain=[("batch_parent_id", "=", self.id)],
            view_mode="list,form",
        )

    def action_open_requests_using_allocation(self):
        self.ensure_one()
        request_ids = [request.id for request, _days in self._usage_entries_from_requests(
            fields.Date.context_today(self), include_future_reservations=True
        )]
        return open_records_action(
            name=_("Leave Requests Using %s", self.name),
            res_model="onehr.leave.request",
            domain=[("id", "in", request_ids)],
            view_mode="list,form",
        )

    @api.model
    def _accrual_period(self, leave_type, employee, run_date):
        run_date = fields.Date.to_date(run_date)
        year_start = run_date.replace(month=1, day=1)
        year_end = run_date.replace(month=12, day=31)
        if leave_type.accrual_frequency == "monthly":
            credit_date = run_date.replace(day=1)
            key = credit_date.strftime("%Y-%m")
        else:
            credit_date = year_start
            key = run_date.strftime("%Y")
        return credit_date, year_end, key

    @api.model
    def _run_accrual_for_types(self, leave_types=None, run_date=None):
        run_date = fields.Date.to_date(run_date or fields.Date.context_today(self))
        leave_types = leave_types or self.env["onehr.leave.type"].search([
            ("state", "=", "active"),
            ("active", "=", True),
            ("accrual_enabled", "=", True),
            ("valid_from", "<=", run_date),
            "|", ("valid_to", "=", False), ("valid_to", ">=", run_date),
        ])
        created = self.browse()
        for leave_type in leave_types:
            employees = self.env["hr.employee"].search([
                ("company_id", "=", leave_type.company_id.id),
                ("active", "=", True),
            ])
            for employee in employees:
                credit_date, period_end, period_key = self._accrual_period(leave_type, employee, run_date)
                if not leave_type.is_employee_eligible(employee, credit_date):
                    continue
                source_key = f"ACCRUAL:{leave_type.id}:{employee.id}:{period_key}"
                if self.search_count([("source_key", "=", source_key)], limit=1):
                    continue
                days = leave_type.accrual_days_for_employee(employee, credit_date)
                if leave_type.accrual_cap:
                    current_balance = self.balance_for_employee(
                        employee, leave_type, run_date, include_future_reservations=True
                    )
                    days = min(days, max(leave_type.accrual_cap - current_balance, 0.0))
                if days <= 0.000001:
                    continue
                allocation = self.create({
                    "company_id": leave_type.company_id.id,
                    "allocation_scope": "single",
                    "employee_id": employee.id,
                    "leave_type_id": leave_type.id,
                    "source": "accrual",
                    "period_start": credit_date,
                    "period_end": period_end,
                    "allocated_days": days,
                    "source_key": source_key,
                    "note": _("Automatic %(frequency)s accrual.", frequency=leave_type.accrual_frequency),
                })
                allocation._write_governed({"state": "confirmed"})
                created |= allocation
        return open_records_action(
            name=_("Generated Accrual Allocations"),
            res_model="onehr.leave.allocation",
            domain=[("id", "in", created.ids)],
            view_mode="list,form",
        ) if leave_types and len(leave_types) == 1 and self.env.user.has_group("onehr_timeoff.group_onehr_timeoff_hr") else True

    @api.model
    def _run_carryover(self, run_date=None):
        run_date = fields.Date.to_date(run_date or fields.Date.context_today(self))
        if run_date.month != 1:
            return True
        current_year_start = run_date.replace(month=1, day=1)
        previous_year_end = current_year_start - timedelta(days=1)
        current_year_end = run_date.replace(month=12, day=31)
        leave_types = self.env["onehr.leave.type"].search([
            ("state", "=", "active"),
            ("active", "=", True),
            ("carryover_enabled", "=", True),
        ])
        for leave_type in leave_types:
            employees = self.env["hr.employee"].search([
                ("company_id", "=", leave_type.company_id.id),
                ("active", "=", True),
            ])
            for employee in employees:
                source_key = f"CARRY:{leave_type.id}:{employee.id}:{current_year_start.year}"
                if self.search_count([("source_key", "=", source_key)], limit=1):
                    continue
                prior_balance = self.balance_for_employee(
                    employee, leave_type, previous_year_end, include_future_reservations=True
                )
                if leave_type.carryover_cap:
                    prior_balance = min(prior_balance, leave_type.carryover_cap)
                if prior_balance <= 0.000001:
                    continue
                expires_on = current_year_start + relativedelta(months=leave_type.carryover_expiry_months) - timedelta(days=1)
                expires_on = min(expires_on, current_year_end)
                allocation = self.create({
                    "company_id": leave_type.company_id.id,
                    "allocation_scope": "single",
                    "employee_id": employee.id,
                    "leave_type_id": leave_type.id,
                    "source": "carryover",
                    "period_start": current_year_start,
                    "period_end": current_year_end,
                    "expires_on": expires_on,
                    "allocated_days": prior_balance,
                    "source_key": source_key,
                    "note": _("Carry-over from year %s", previous_year_end.year),
                })
                allocation._write_governed({"state": "confirmed"})
        return True

    @api.model
    def _cron_process_timeoff(self):
        """Daily idempotent scheduler for entitlement and request lifecycle."""
        self._run_accrual_for_types()
        self._run_carryover()
        self.env["onehr.leave.request"]._cron_complete_due_requests()
        return True
