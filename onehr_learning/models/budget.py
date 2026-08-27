import base64
import json
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_records_action
from .authority_helpers import require_learning_manager


class OneHRLearningBudget(models.Model):
    """Company-period L&D budget and burn governance."""

    _name = "onehr.learning.budget"
    _description = "OneHR Learning Budget"
    _inherit = ["onehr.mixin.audit"]
    _order = "period_start desc, code, id"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_learning_budget_state_controlled"
    _DOWNLOAD_CONTEXT = "onehr_learning_budget_download_controlled"

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
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
        related="company_id.currency_id",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    period_start = fields.Date(required=True, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)
    allocated_amount = fields.Monetary(
        required=True,
        default=0.0,
        currency_field="currency_id",
        tracking=True,
    )
    overrun_policy = fields.Selection(
        [
            ("block", "Block Overrun"),
            ("warn", "Allow with Manager Governance"),
        ],
        required=True,
        default="block",
        tracking=True,
    )
    allowed_overrun_percent = fields.Float(default=0.0, tracking=True)
    policy_notes = fields.Text(tracking=True)

    cost_line_ids = fields.One2many(
        "onehr.learning.cost.line",
        "budget_id",
        string="Cost Lines",
    )
    session_ids = fields.One2many(
        "onehr.learning.session",
        "budget_id",
        string="Training Sessions",
    )
    planned_amount = fields.Monetary(
        compute="_compute_budget_summary", store=True,
        currency_field="currency_id", aggregator="sum",
    )
    committed_amount = fields.Monetary(
        compute="_compute_budget_summary", store=True,
        currency_field="currency_id", aggregator="sum",
    )
    actual_amount = fields.Monetary(
        compute="_compute_budget_summary", store=True,
        currency_field="currency_id", aggregator="sum",
    )
    remaining_amount = fields.Monetary(
        compute="_compute_budget_summary", store=True,
        currency_field="currency_id", aggregator="sum",
    )
    budget_burn_percent = fields.Float(
        compute="_compute_budget_summary", store=True,
        digits=(16, 2), aggregator="avg",
    )
    session_count = fields.Integer(compute="_compute_budget_summary", store=True)
    learner_count = fields.Integer(compute="_compute_budget_summary", store=True)
    actual_cost_per_learner = fields.Monetary(
        compute="_compute_budget_summary", store=True,
        currency_field="currency_id", aggregator="avg",
    )

    payroll_download_file = fields.Binary(attachment=False, readonly=True, copy=False)
    payroll_download_filename = fields.Char(readonly=True, copy=False)

    _budget_code_company_unique = models.Constraint(
        "unique(company_id, code)",
        "Learning Budget code must be unique within a company.",
    )

    @api.depends(
        "allocated_amount",
        "cost_line_ids.state",
        "cost_line_ids.amount",
        "session_ids.enrollment_ids.state",
        "session_ids.enrollment_ids.employee_id",
    )
    def _compute_budget_summary(self):
        for record in self:
            planned = record.cost_line_ids.filtered(lambda line: line.state == "planned")
            committed = record.cost_line_ids.filtered(lambda line: line.state == "committed")
            actual = record.cost_line_ids.filtered(lambda line: line.state == "actual")
            record.planned_amount = sum(planned.mapped("amount"))
            record.committed_amount = sum(committed.mapped("amount"))
            record.actual_amount = sum(actual.mapped("amount"))
            record.remaining_amount = record.allocated_amount - (
                record.committed_amount + record.actual_amount
            )
            record.budget_burn_percent = (
                round(record.actual_amount * 100.0 / record.allocated_amount, 2)
                if record.allocated_amount
                else 0.0
            )
            record.session_count = len(record.session_ids)
            employees = (
                record.session_ids.mapped("enrollment_ids")
                .filtered(lambda item: item.state not in {"draft", "rejected", "cancelled"})
                .mapped("employee_id")
            )
            record.learner_count = len(employees)
            record.actual_cost_per_learner = (
                record.actual_amount / len(employees) if employees else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_manager(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("Learning Budgets must be created in Draft."))
            vals["code"] = (vals.get("code") or "").strip().upper()
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_budget()
        return records

    def _write_governed(self, values):
        return super(OneHRLearningBudget, self).write(values)

    def write(self, values):
        require_learning_manager(self)
        values = dict(values)
        if {"payroll_download_file", "payroll_download_filename"} & set(values):
            if not self.env.context.get(self._DOWNLOAD_CONTEXT):
                raise AccessError(_("Generated Learning payroll-cost payload is server-controlled."))
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Learning Budget state changes only through governed actions."))
        if any(record.state in {"closed", "cancelled"} for record in self):
            if (
                not self.env.context.get(self._STATE_CONTEXT)
                and not (
                    self.env.context.get(self._DOWNLOAD_CONTEXT)
                    and set(values) <= {"payroll_download_file", "payroll_download_filename"}
                )
            ):
                raise AccessError(_("Closed/Cancelled Learning Budgets are frozen."))
        if any(record.state == "active" for record in self):
            protected = {"company_id", "period_start", "period_end", "allocated_amount"}
            if protected & set(values) and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Active Learning Budget identity/amount cannot be rewritten."))
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        result = super().write(values)
        self._validate_budget()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_budget_history(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft" or record.cost_line_ids or record.session_ids:
                raise AccessError(_("Only an unused Draft Learning Budget can be deleted."))

    @api.constrains(
        "period_start",
        "period_end",
        "allocated_amount",
        "allowed_overrun_percent",
    )
    def _check_budget(self):
        self._validate_budget()

    def _validate_budget(self):
        for record in self:
            if record.period_end < record.period_start:
                raise ValidationError(_("Budget Period End cannot be before Period Start."))
            if record.allocated_amount < 0:
                raise ValidationError(_("Allocated Budget cannot be negative."))
            if record.allowed_overrun_percent < 0:
                raise ValidationError(_("Allowed Overrun Percent cannot be negative."))
        return True

    def _assert_cost_capacity(self, additional_amount, excluding_line=None):
        self.ensure_one()
        additional_amount = float(additional_amount or 0.0)
        active_spend = sum(
            self.cost_line_ids.filtered(
                lambda line: line.state in {"committed", "actual"}
                and line != excluding_line
            ).mapped("amount")
        )
        limit = self.allocated_amount * (1.0 + self.allowed_overrun_percent / 100.0)
        projected = active_spend + additional_amount
        if projected > limit + 0.0001:
            if self.overrun_policy == "block":
                raise ValidationError(
                    _(
                        "Learning Budget overrun blocked. Projected committed/actual spend "
                        "%(projected).2f exceeds governed limit %(limit).2f.",
                        projected=projected,
                        limit=limit,
                    )
                )
            require_learning_manager(self)
        return True

    def action_activate(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a Draft Learning Budget can be activated."))
            record._validate_budget()
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "active"}
            )
            record.log_business_action(_("Learning Budget activated."))
        return True

    def action_close(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "active":
                raise UserError(_("Only an Active Learning Budget can be closed."))
            if record.cost_line_ids.filtered(lambda line: line.state == "committed"):
                raise UserError(_("Resolve all Committed Learning Costs before closing the Budget."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "closed"}
            )
            record.log_business_action(_("Learning Budget closed."))
        return True

    def action_cancel(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a Draft Learning Budget can be cancelled."))
            if record.cost_line_ids.filtered(lambda line: line.state != "planned"):
                raise UserError(_("Budget with committed/actual costs cannot be cancelled."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "cancelled"}
            )
        return True

    def action_open_sessions(self):
        self.ensure_one()
        require_learning_manager(self)
        return open_records_action(
            name=_("Learning Sessions — %s", self.display_name),
            res_model="onehr.learning.session",
            domain=[("budget_id", "=", self.id)],
            context={"default_budget_id": self.id, "default_company_id": self.company_id.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_cost_lines(self):
        self.ensure_one()
        require_learning_manager(self)
        return open_records_action(
            name=_("Learning Costs — %s", self.display_name),
            res_model="onehr.learning.cost.line",
            domain=[("budget_id", "=", self.id)],
            context={"default_budget_id": self.id, "default_company_id": self.company_id.id},
            view_mode="list,pivot,graph,form",
        )

    def onehr_payroll_cost_payload(self):
        """Stable outbound hand-off; Payroll Bridge transport remains downstream-owned."""
        self.ensure_one()
        require_learning_manager(self)
        lines = self.cost_line_ids.filtered(
            lambda line: line.state == "actual"
            and line.reimbursable
            and line.payroll_bridge_eligible
        )
        return {
            "schema": "onehr.learning.payroll-cost/v1",
            "budget": self.code,
            "company_id": self.company_id.id,
            "currency": self.currency_id.name,
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "costs": [line.onehr_payroll_cost_payload() for line in lines],
        }

    def action_export_payroll_cost_json(self):
        self.ensure_one()
        require_learning_manager(self)
        payload = self.onehr_payroll_cost_payload()
        filename = f"{self.code}-learning-payroll-costs.json"
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        )
        self.with_context(**{self._DOWNLOAD_CONTEXT: True}).write(
            {
                "payroll_download_file": encoded,
                "payroll_download_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/payroll_download_file/%s?download=true"
            % (self._name, self.id, quote(filename)),
            "target": "self",
        }
