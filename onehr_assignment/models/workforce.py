
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_assignment_manager, require_assignment_officer


class OneHRWorkforcePlan(models.Model):
    _name = "onehr.workforce.plan"
    _description = "OneHR Workforce Plan"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "period_start desc, plan_code, version desc"

    _STATE_CONTEXT = "onehr_workforce_plan_state_controlled"
    _VERSION_CONTEXT = "onehr_workforce_plan_version_controlled"

    name = fields.Char(required=True, tracking=True)
    plan_code = fields.Char(required=True, index=True, tracking=True)
    version = fields.Integer(required=True, default=1, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True, tracking=True,
    )
    scenario = fields.Selection(
        [("baseline", "Baseline"), ("budget", "Budget"), ("forecast", "Forecast"), ("what_if", "What-if")],
        required=True, default="budget", index=True, tracking=True,
    )
    period_start = fields.Date(required=True, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)
    predecessor_plan_id = fields.Many2one("onehr.workforce.plan", ondelete="restrict", copy=False, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"), ("proposed", "Proposed"), ("approved", "Approved"),
            ("active", "Active"), ("closed", "Closed"), ("rejected", "Rejected"),
        ],
        required=True, default="draft", index=True, tracking=True,
    )
    line_ids = fields.One2many(
        "onehr.workforce.plan.line", "plan_id", string="Position Plan Lines", copy=False,
    )
    line_count = fields.Integer(compute="_compute_totals")
    planned_headcount = fields.Integer(compute="_compute_totals")
    planned_fte = fields.Float(compute="_compute_totals")
    planned_cost = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    note = fields.Text(tracking=True)

    _plan_version_unique = models.Constraint(
        "unique(company_id, plan_code, version)",
        "Workforce Plan code/version must be unique within a company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_assignment_manager(self)
        if not self.env.context.get(self._STATE_CONTEXT) and any(
            incoming.get("state", "draft") != "draft" for incoming in vals_list
        ):
            raise AccessError(_("Workforce Plans must be created in Draft."))
        if not self.env.context.get(self._VERSION_CONTEXT) and any(
            incoming.get("predecessor_plan_id") for incoming in vals_list
        ):
            raise AccessError(_("Workforce Plan lineage can be set only by Create New Version."))
        records = super().create(vals_list)
        records._validate_plan_integrity()
        return records

    def write(self, values):
        require_assignment_manager(self)
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Workforce Plan state can change only through governed actions."))
        if "predecessor_plan_id" in values and not self.env.context.get(self._VERSION_CONTEXT):
            raise AccessError(_("Workforce Plan lineage can change only through governed versioning."))
        editable = {"name", "plan_code", "version", "company_id", "scenario", "period_start", "period_end", "line_ids", "note"}
        if editable & set(values) and any(plan.state not in {"draft", "rejected"} for plan in self):
            raise AccessError(_("Submitted Workforce Plans are frozen; create a new version instead."))
        result = super().write(values)
        if editable & set(values):
            self._validate_plan_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_plan_history(self):
        if any(plan.state != "draft" for plan in self):
            raise AccessError(_("Only Draft Workforce Plans can be deleted."))

    @api.constrains("period_start", "period_end", "version", "company_id")
    def _check_plan_integrity(self):
        self._validate_plan_integrity()

    def _validate_plan_integrity(self):
        for plan in self:
            if plan.period_end < plan.period_start:
                raise ValidationError(_("Workforce Plan End Date cannot be before Start Date."))
            if plan.version <= 0:
                raise ValidationError(_("Workforce Plan Version must be positive."))
            if plan.line_ids:
                plan.line_ids._validate_line_integrity()
        return True

    @api.depends("line_ids.planned_headcount", "line_ids.planned_fte", "line_ids.planned_cost")
    def _compute_totals(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.planned_headcount = sum(plan.line_ids.mapped("planned_headcount"))
            plan.planned_fte = sum(plan.line_ids.mapped("planned_fte"))
            plan.planned_cost = sum(plan.line_ids.mapped("planned_cost"))

    def _approval_payload(self):
        self.ensure_one()
        return {
            "workforce_plan": self.display_name,
            "plan_code": self.plan_code,
            "version": self.version,
            "scenario": self.scenario,
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "position_lines": len(self.line_ids),
            "planned_headcount": self.planned_headcount,
            "planned_fte": self.planned_fte,
            "planned_cost": self.planned_cost,
            "currency": self.currency_id.name,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        values.update({
            "document_type": "onehr_workforce_plan",
            "amount": self.planned_cost,
            "currency_id": self.currency_id.id,
            "extra": {
                "scenario": self.scenario,
                "planned_headcount": self.planned_headcount,
                "planned_fte": self.planned_fte,
                "position_ids": self.line_ids.mapped("position_id").ids,
            },
        })
        return values

    def action_submit_for_approval(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state not in {"draft", "rejected"}:
            raise UserError(_("Only Draft or Rejected Workforce Plans can be submitted."))
        if not self.line_ids:
            raise ValidationError(_("Workforce Plan requires at least one position line."))
        self._validate_plan_integrity()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "proposed"})
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "proposed":
            return True
        self.with_context(**{self._STATE_CONTEXT: True}).write({
            "state": "approved" if decision == "approve" else "rejected"
        })
        return True

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        if self.state in {"active", "closed"}:
            raise UserError(_("Approval cannot be cancelled after Workforce Plan activation."))
        return True

    def action_create_new_version(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state in {"draft", "proposed"}:
            raise UserError(_("Finish or reject the current version before creating a successor version."))
        new_plan = self.with_context(**{self._VERSION_CONTEXT: True}).copy({
            "name": _("%s — v%s", self.plan_code, self.version + 1),
            "version": self.version + 1,
            "state": "draft",
            "predecessor_plan_id": self.id,
        })
        for line in self.line_ids:
            line.copy({"plan_id": new_plan.id, "generated_budget_id": False})
        return open_record_action(name=new_plan.display_name, res_model=self._name, res_id=new_plan.id)

    def action_activate(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "approved":
            raise UserError(_("Only an Approved Workforce Plan can be activated."))
        self._validate_plan_integrity()
        for line in self.line_ids:
            line._materialize_position_budget()
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        approval = self.env["onehr.approval.request"].search(
            [("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")],
            order="finalized_at desc, id desc", limit=1,
        )
        if approval:
            self.onehr_mark_approval_executed(approval)
        return self.action_open_position_budgets()

    def action_close(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "active":
            raise UserError(_("Only an Active Workforce Plan can be closed."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "closed"})
        return True

    def action_open_position_budgets(self):
        self.ensure_one()
        return open_records_action(
            name=_("Position Budgets — %s", self.display_name),
            res_model="onehr.position.budget",
            domain=[("source_plan_line_id.plan_id", "=", self.id)],
        )


class OneHRWorkforcePlanLine(models.Model):
    _name = "onehr.workforce.plan.line"
    _description = "OneHR Workforce Plan Line"
    _inherit = ["onehr.mixin.audit"]
    _order = "plan_id, sequence, position_id"

    _INTERNAL_CONTEXT = "onehr_workforce_plan_line_controlled"

    plan_id = fields.Many2one("onehr.workforce.plan", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="plan_id.company_id", store=True, readonly=True, index=True)
    sequence = fields.Integer(default=10)
    position_id = fields.Many2one("onehr.position", required=True, ondelete="restrict", check_company=True, index=True, tracking=True)
    department_id = fields.Many2one(related="position_id.department_id", store=True, readonly=True)
    job_id = fields.Many2one(related="position_id.job_id", store=True, readonly=True)
    grade_id = fields.Many2one(related="position_id.grade_id", store=True, readonly=True)
    planned_headcount = fields.Integer(required=True, default=1, tracking=True)
    planned_fte = fields.Float(required=True, default=1.0, tracking=True)
    planned_cost = fields.Monetary(default=0.0, currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one(related="plan_id.currency_id", readonly=True)
    rationale = fields.Char(tracking=True)
    generated_budget_id = fields.Many2one("onehr.position.budget", readonly=True, copy=False, ondelete="restrict")

    _plan_position_unique = models.Constraint(
        "unique(plan_id, position_id)", "A Position may appear only once in a Workforce Plan version."
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_assignment_manager(self)
        if not self.env.context.get(self._INTERNAL_CONTEXT) and any(
            incoming.get("generated_budget_id") for incoming in vals_list
        ):
            raise AccessError(_("Generated Position Budget evidence is set only by plan activation."))
        records = super().create(vals_list)
        records._validate_line_integrity()
        return records

    def write(self, values):
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            require_assignment_manager(self)
            if "generated_budget_id" in values:
                raise AccessError(_("Generated Position Budget evidence is set only by plan activation."))
            if any(line.plan_id.state not in {"draft", "rejected"} for line in self):
                raise AccessError(_("Workforce Plan lines are frozen after submission."))
        result = super().write(values)
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            self._validate_line_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_plan_lines(self):
        if any(line.plan_id.state != "draft" for line in self):
            raise AccessError(_("Only lines of a Draft Workforce Plan can be deleted."))

    @api.constrains("position_id", "planned_headcount", "planned_fte", "planned_cost")
    def _check_line_integrity(self):
        self._validate_line_integrity()

    def _validate_line_integrity(self):
        for line in self:
            if line.position_id.company_id != line.company_id:
                raise ValidationError(_("Planned Position must belong to the Workforce Plan company."))
            if line.planned_headcount < 0 or line.planned_fte < 0 or line.planned_cost < 0:
                raise ValidationError(_("Planned Headcount, FTE and Cost cannot be negative."))
            if line.planned_fte > line.planned_headcount + 0.000001:
                raise ValidationError(_("Planned FTE cannot exceed Planned Headcount."))
        return True

    def _materialize_position_budget(self):
        self.ensure_one()
        if self.generated_budget_id:
            budget = self.generated_budget_id
        else:
            budget = self.env["onehr.position.budget"].with_context(
                onehr_position_budget_source_controlled=True
            ).create({
                "position_id": self.position_id.id,
                "valid_from": self.plan_id.period_start,
                "valid_to": self.plan_id.period_end,
                "authorized_headcount": self.planned_headcount,
                "authorized_fte": self.planned_fte,
                "budget_amount": self.planned_cost,
                "source_plan_line_id": self.id,
            })
            self.with_context(**{self._INTERNAL_CONTEXT: True}).write({"generated_budget_id": budget.id})
        if budget.state == "draft":
            budget.action_activate()
        return budget

    def action_open_position(self):
        self.ensure_one()
        return open_record_action(name=self.position_id.display_name, res_model="onehr.position", res_id=self.position_id.id)

    def action_open_budget(self):
        self.ensure_one()
        if not self.generated_budget_id:
            raise UserError(_("This plan line has not generated a Position Budget."))
        return open_record_action(name=self.generated_budget_id.display_name, res_model="onehr.position.budget", res_id=self.generated_budget_id.id)


class OneHRPositionBudget(models.Model):
    _name = "onehr.position.budget"
    _description = "OneHR Position Budget Authorization"
    _inherit = ["onehr.mixin.audit"]
    _order = "valid_from desc, position_id, id desc"

    _STATE_CONTEXT = "onehr_position_budget_state_controlled"
    _SOURCE_CONTEXT = "onehr_position_budget_source_controlled"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    company_id = fields.Many2one(related="position_id.company_id", store=True, readonly=True, index=True)
    position_id = fields.Many2one("onehr.position", required=True, ondelete="restrict", index=True, tracking=True)
    valid_from = fields.Date(required=True, index=True, tracking=True)
    valid_to = fields.Date(index=True, tracking=True)
    authorized_headcount = fields.Integer(required=True, default=1, tracking=True)
    authorized_fte = fields.Float(required=True, default=1.0, tracking=True)
    budget_amount = fields.Monetary(default=0.0, currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    source_plan_line_id = fields.Many2one("onehr.workforce.plan.line", ondelete="restrict", copy=False, readonly=True, index=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("closed", "Closed")],
        required=True, default="draft", index=True, tracking=True,
    )
    assigned_headcount = fields.Integer(compute="_compute_assignment_metrics")
    assigned_fte = fields.Float(compute="_compute_assignment_metrics")
    available_headcount = fields.Integer(compute="_compute_assignment_metrics")
    available_fte = fields.Float(compute="_compute_assignment_metrics")

    @api.depends("position_id", "valid_from", "valid_to")
    def _compute_name(self):
        for budget in self:
            budget.name = _("%(position)s | %(start)s → %(end)s",
                position=budget.position_id.display_name if budget.position_id else _("Position"),
                start=budget.valid_from or _("?"), end=budget.valid_to or _("Open"))

    @api.model_create_multi
    def create(self, vals_list):
        require_assignment_manager(self)
        if not self.env.context.get(self._STATE_CONTEXT) and any(
            incoming.get("state", "draft") != "draft" for incoming in vals_list
        ):
            raise AccessError(_("Position Budgets must be created in Draft."))
        if not self.env.context.get(self._SOURCE_CONTEXT) and any(
            incoming.get("source_plan_line_id") for incoming in vals_list
        ):
            raise AccessError(_("Position Budget source-plan evidence is set only by Workforce Plan activation."))
        records = super().create(vals_list)
        records._validate_budget_integrity()
        return records

    def write(self, values):
        require_assignment_manager(self)
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Position Budget state can change only through governed actions."))
        if "source_plan_line_id" in values and not self.env.context.get(self._SOURCE_CONTEXT):
            raise AccessError(_("Position Budget source-plan evidence cannot be rewritten."))
        editable = {"position_id", "valid_from", "valid_to", "authorized_headcount", "authorized_fte", "budget_amount"}
        if editable & set(values) and any(budget.state != "draft" for budget in self):
            raise AccessError(_("Active/Closed Position Budgets are frozen; create a successor budget interval."))
        result = super().write(values)
        if editable & set(values):
            self._validate_budget_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_budget_history(self):
        if any(budget.state != "draft" for budget in self):
            raise AccessError(_("Only Draft Position Budgets can be deleted."))

    @api.constrains("position_id", "valid_from", "valid_to", "authorized_headcount", "authorized_fte", "budget_amount", "state")
    def _check_budget_integrity(self):
        self._validate_budget_integrity()

    def _validate_budget_integrity(self):
        for budget in self:
            if budget.valid_to and budget.valid_to < budget.valid_from:
                raise ValidationError(_("Position Budget End Date cannot be before Start Date."))
            if budget.authorized_headcount < 0 or budget.authorized_fte < 0 or budget.budget_amount < 0:
                raise ValidationError(_("Authorized Headcount, FTE and Budget Amount cannot be negative."))
            if budget.authorized_fte > budget.authorized_headcount + 0.000001:
                raise ValidationError(_("Authorized FTE cannot exceed Authorized Headcount."))
            if budget.position_id and budget.position_id.company_id != budget.company_id:
                raise ValidationError(_("Position Budget company must follow the Position company."))
            if budget.state == "active":
                domain = [
                    ("id", "!=", budget.id), ("position_id", "=", budget.position_id.id), ("state", "=", "active")
                ]
                if budget.valid_to:
                    domain.append(("valid_from", "<=", budget.valid_to))
                domain += ["|", ("valid_to", "=", False), ("valid_to", ">=", budget.valid_from)]
                if self.search_count(domain, limit=1):
                    raise ValidationError(_("Active Position Budget intervals cannot overlap for the same Position."))
        return True

    def _compute_assignment_metrics(self):
        Assignment = self.env["onehr.assignment"]
        for budget in self:
            if not budget.position_id or not budget.valid_from:
                budget.assigned_headcount = budget.assigned_fte = budget.available_headcount = budget.available_fte = 0
                continue
            as_of = max(budget.valid_from, fields.Date.context_today(self))
            if budget.valid_to and as_of > budget.valid_to:
                as_of = budget.valid_to
            assignments = Assignment.search([
                ("position_id", "=", budget.position_id.id),
                ("state", "in", ["approved", "active"]),
                ("effective_from", "<=", as_of),
                "|", ("effective_to", "=", False), ("effective_to", ">=", as_of),
            ])
            budget.assigned_headcount = len(assignments)
            budget.assigned_fte = sum(assignments.mapped("fte"))
            budget.available_headcount = budget.authorized_headcount - budget.assigned_headcount
            budget.available_fte = budget.authorized_fte - budget.assigned_fte

    def action_activate(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Position Budget can be activated."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "active"})
        overlapping_assignments = self.env["onehr.assignment"].search([
            ("position_id", "=", self.position_id.id),
            ("state", "in", ["approved", "active"]),
            ("effective_from", "<=", self.valid_to or fields.Date.to_date("9999-12-31")),
            "|", ("effective_to", "=", False), ("effective_to", ">=", self.valid_from),
        ])
        for assignment in overlapping_assignments:
            assignment._check_position_capacity()
        return True

    def action_close(self):
        self.ensure_one()
        require_assignment_manager(self)
        if self.state != "active":
            raise UserError(_("Only an Active Position Budget can be closed."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "closed"})
        return True

    def action_open_assignments(self):
        self.ensure_one()
        return open_records_action(
            name=_("Assignments — %s", self.position_id.display_name),
            res_model="onehr.assignment",
            domain=[("position_id", "=", self.position_id.id)],
        )

    def action_open_source_plan(self):
        self.ensure_one()
        if not self.source_plan_line_id:
            raise UserError(_("This Position Budget was not generated by a Workforce Plan."))
        return open_record_action(
            name=self.source_plan_line_id.plan_id.display_name,
            res_model="onehr.workforce.plan",
            res_id=self.source_plan_line_id.plan_id.id,
        )
