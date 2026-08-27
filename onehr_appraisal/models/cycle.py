import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .authority_helpers import (
    display_notification,
    require_appraisal_admin,
    require_appraisal_hr,
)


class OneHRAppraisalCycle(models.Model):
    _name = "onehr.appraisal.cycle"
    _description = "OneHR Appraisal Cycle"
    _inherit = ["onehr.mixin.audit"]
    _order = "date_start desc, id desc"

    _STATE_CONTEXT = "onehr_appraisal_cycle_state_controlled"

    _code_company_unique = models.Constraint(
        "UNIQUE(code, company_id)",
        "Appraisal cycle code must be unique per company.",
    )

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True, copy=False)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    cycle_type = fields.Selection(
        [
            ("annual", "Annual"),
            ("biannual", "Biannual"),
            ("quarterly", "Quarterly"),
            ("custom", "Custom"),
        ],
        default="annual", required=True, tracking=True, index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("consolidation", "Consolidation"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True,
    )
    date_start = fields.Date(required=True, tracking=True, index=True)
    date_end = fields.Date(required=True, tracking=True, index=True)
    self_review_deadline = fields.Date(tracking=True)
    manager_review_deadline = fields.Date(tracking=True)
    consolidation_deadline = fields.Date(tracking=True)

    target_department_ids = fields.Many2many(
        "hr.department",
        "onehr_appraisal_cycle_department_rel",
        "cycle_id", "department_id",
        string="Target Departments",
        check_company=True,
        help="Leave empty to include all active employees in the cycle company.",
    )

    rating_min = fields.Float(default=1.0, required=True, tracking=True)
    rating_max = fields.Float(default=5.0, required=True, tracking=True)
    self_weight = fields.Float(default=20.0, required=True, tracking=True)
    manager_weight = fields.Float(default=60.0, required=True, tracking=True)
    peer_weight = fields.Float(default=20.0, required=True, tracking=True)
    retention_years = fields.Integer(
        default=7,
        required=True,
        tracking=True,
        help="Minimum business retention horizon for closed appraisal evidence.",
    )

    instructions = fields.Html()
    calibration_notes = fields.Html()
    closure_notes = fields.Html()

    template_score_ids = fields.One2many(
        "onehr.appraisal.score", "cycle_id",
        string="Objective / KPI Template",
        domain=[("is_template", "=", True)],
        copy=True,
    )
    form_ids = fields.One2many("onehr.appraisal.form", "cycle_id", string="Appraisal Forms")

    template_count = fields.Integer(compute="_compute_metrics")
    form_count = fields.Integer(compute="_compute_metrics")
    completed_form_count = fields.Integer(compute="_compute_metrics")
    completion_rate = fields.Float(compute="_compute_metrics", string="Completion %")
    average_score = fields.Float(compute="_compute_metrics")
    outstanding_count = fields.Integer(compute="_compute_metrics")
    needs_attention_count = fields.Integer(compute="_compute_metrics")

    kpi_import_file = fields.Binary(string="KPI Target CSV", attachment=True)
    kpi_import_filename = fields.Char()
    export_file = fields.Binary(string="Result Export", readonly=True, attachment=True)
    export_filename = fields.Char(readonly=True)

    @api.depends(
        "template_score_ids",
        "template_score_ids.parent_score_id",
        "form_ids.state",
        "form_ids.final_score",
        "form_ids.final_rating_label",
    )
    def _compute_metrics(self):
        for cycle in self:
            cycle.template_count = len(cycle.template_score_ids.filtered(lambda line: not line.parent_score_id))
            forms = cycle.form_ids.filtered(lambda record: record.state != "cancelled")
            closed = forms.filtered(lambda record: record.state == "closed")
            cycle.form_count = len(forms)
            cycle.completed_form_count = len(closed)
            cycle.completion_rate = len(closed) * 100.0 / len(forms) if forms else 0.0
            scored = closed.filtered(lambda record: record.final_score > 0)
            cycle.average_score = (
                sum(scored.mapped("final_score")) / len(scored) if scored else 0.0
            )
            cycle.outstanding_count = len(
                closed.filtered(lambda record: record.final_rating_label == "outstanding")
            )
            cycle.needs_attention_count = len(
                closed.filtered(
                    lambda record: record.final_rating_label in ("below", "partial")
                )
            )

    @api.constrains(
        "date_start", "date_end", "self_review_deadline",
        "manager_review_deadline", "consolidation_deadline",
    )
    def _check_dates(self):
        for cycle in self:
            if cycle.date_start and cycle.date_end and cycle.date_start > cycle.date_end:
                raise ValidationError(_("Cycle start date cannot be after end date."))
            deadlines = [
                date for date in (
                    cycle.self_review_deadline,
                    cycle.manager_review_deadline,
                    cycle.consolidation_deadline,
                ) if date
            ]
            if deadlines != sorted(deadlines):
                raise ValidationError(_("Review deadlines must be chronological."))
            for deadline in deadlines:
                if cycle.date_start and deadline < cycle.date_start:
                    raise ValidationError(_("A review deadline cannot precede the cycle start."))
                if cycle.date_end and deadline > cycle.date_end:
                    raise ValidationError(_("A review deadline cannot exceed the cycle end."))

    @api.constrains("rating_min", "rating_max")
    def _check_rating_scale(self):
        for cycle in self:
            if cycle.rating_min < 0 or cycle.rating_max <= cycle.rating_min:
                raise ValidationError(_("Rating maximum must be greater than a non-negative minimum."))

    @api.constrains("self_weight", "manager_weight", "peer_weight")
    def _check_rater_weights(self):
        for cycle in self:
            weights = (cycle.self_weight, cycle.manager_weight, cycle.peer_weight)
            if any(weight < 0 or weight > 100 for weight in weights):
                raise ValidationError(_("Every rater weight must be between 0 and 100."))
            if abs(sum(weights) - 100.0) > 0.01:
                raise ValidationError(_("Self, Manager and Peer weights must total 100%."))

    @api.constrains("retention_years")
    def _check_retention_years(self):
        for cycle in self:
            if cycle.retention_years < 1:
                raise ValidationError(
                    _("Appraisal retention policy must be at least one year.")
                )

    def _check_template_weight_total(self):
        for cycle in self:
            lines = cycle.template_score_ids.filtered(
                lambda line: not line.parent_score_id and line.line_type != "development"
            )
            if lines and abs(sum(lines.mapped("weight")) - 100.0) > 0.01:
                raise ValidationError(_("Objective/KPI template weights must total 100%."))

    def write(self, vals):
        if "state" in vals and not self.env.context.get(self._STATE_CONTEXT):
            raise UserError(
                _("Appraisal Cycle state must change through its governed action buttons.")
            )

        frozen_definition_fields = {
            "code", "company_id", "cycle_type", "date_start", "date_end",
            "self_review_deadline", "manager_review_deadline",
            "consolidation_deadline", "target_department_ids",
            "rating_min", "rating_max", "self_weight", "manager_weight",
            "peer_weight", "retention_years",
        }
        for cycle in self:
            if (
                cycle.state != "draft"
                and frozen_definition_fields.intersection(vals)
            ):
                raise UserError(
                    _("Cycle dates, scope, rating scale and rater weights are frozen after Draft.")
                )
        return super().write(vals)

    def _write_state(self, state):
        return self.with_context(**{self._STATE_CONTEXT: True}).write({"state": state})

    def _employee_domain(self):
        self.ensure_one()
        domain = [("company_id", "=", self.company_id.id), ("active", "=", True)]
        if self.target_department_ids:
            domain.append(("department_id", "in", self.target_department_ids.ids))
        return domain

    def action_open_cycle(self):
        require_appraisal_hr(self)
        for cycle in self:
            if cycle.state != "draft":
                raise UserError(_("Only a Draft cycle can be opened."))
            if not cycle.template_score_ids:
                raise UserError(_("Define at least one Objective/KPI template before opening."))
            cycle._check_template_weight_total()
            cycle._write_state("in_review")
        return display_notification(_("Appraisal cycle opened for review."))

    def action_generate_appraisal_forms(self):
        require_appraisal_hr(self)
        Form = self.env["onehr.appraisal.form"]
        Score = self.env["onehr.appraisal.score"]
        created_count = 0

        for cycle in self:
            if cycle.state not in ("draft", "in_review"):
                raise UserError(_("Forms can only be generated before consolidation."))
            cycle._check_template_weight_total()
            templates = cycle.template_score_ids.filtered(
                lambda line: line.is_template and not line.parent_score_id
                and line.line_type != "development"
            )
            if not templates:
                raise UserError(_("The cycle has no Objective/KPI template lines."))

            existing_employee_ids = set(cycle.form_ids.mapped("employee_id").ids)
            for employee in self.env["hr.employee"].search(cycle._employee_domain()):
                if employee.id in existing_employee_ids:
                    continue
                form = Form.create({
                    "cycle_id": cycle.id,
                    "employee_id": employee.id,
                    "manager_employee_id": employee.parent_id.id or False,
                })
                for template in templates:
                    target = Score.create({
                        "cycle_id": cycle.id,
                        "form_id": form.id,
                        "line_type": template.line_type,
                        "item_code": template.item_code,
                        "title": template.title,
                        "description": template.description,
                        "weight": template.weight,
                        "target_value": template.target_value,
                        "rater_type": "target",
                    })
                    for rater_type, reviewer, configured_weight in (
                        ("self", employee, cycle.self_weight),
                        ("manager", employee.parent_id, cycle.manager_weight),
                    ):
                        if configured_weight <= 0:
                            continue
                        Score.create({
                            "cycle_id": cycle.id,
                            "form_id": form.id,
                            "parent_score_id": target.id,
                            "line_type": template.line_type,
                            "item_code": template.item_code,
                            "title": template.title,
                            "weight": template.weight,
                            "rater_type": rater_type,
                            "reviewer_employee_id": reviewer.id if reviewer else False,
                        })
                created_count += 1

        return display_notification(_("Generated %s new appraisal form(s).") % created_count)

    def action_start_consolidation(self):
        require_appraisal_hr(self)
        for cycle in self:
            if cycle.state != "in_review":
                raise UserError(_("Only an In Review cycle can enter Consolidation."))
            blocking = cycle.form_ids.filtered(
                lambda form: form.state not in ("consolidation", "closed", "cancelled")
            )
            if blocking:
                raise UserError(_("All active forms must reach Consolidation first."))
            cycle._write_state("consolidation")
        return display_notification(_("Cycle moved to Consolidation."))

    def action_close_cycle(self):
        require_appraisal_hr(self)
        for cycle in self:
            if cycle.state != "consolidation":
                raise UserError(_("Only a Consolidation cycle can be closed."))
            blocking = cycle.form_ids.filtered(
                lambda form: form.state not in ("closed", "cancelled")
            )
            if blocking:
                raise UserError(_("Close or cancel all appraisal forms first."))
            cycle._write_state("closed")
        return display_notification(_("Appraisal cycle closed."))

    def action_cancel(self):
        require_appraisal_admin(self)
        for cycle in self:
            if cycle.state == "closed":
                raise UserError(_("A closed appraisal cycle cannot be cancelled."))
            cycle._write_state("cancelled")
        return display_notification(_("Appraisal cycle cancelled."), notification_type="warning")

    def action_reset_draft(self):
        require_appraisal_admin(self)
        for cycle in self:
            if cycle.form_ids.filtered(lambda form: form.state not in ("draft", "cancelled")):
                raise UserError(_("Reset is blocked because review evidence already exists."))
            cycle._write_state("draft")
        return display_notification(_("Cycle reset to Draft."))

    def action_open_forms(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Appraisal Forms"),
            "res_model": "onehr.appraisal.form",
            "view_mode": "list,kanban,form,pivot,graph",
            "domain": [("cycle_id", "=", self.id)],
            "context": {"default_cycle_id": self.id},
        }

    def action_open_templates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Objective / KPI Template"),
            "res_model": "onehr.appraisal.score",
            "view_mode": "list,form",
            "domain": [("cycle_id", "=", self.id), ("is_template", "=", True)],
            "context": {
                "default_cycle_id": self.id,
                "default_is_template": True,
                "default_rater_type": "target",
            },
        }

    def action_import_kpi_targets(self):
        require_appraisal_hr(self)
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("KPI templates can only be imported while the cycle is Draft."))
        if not self.kpi_import_file:
            raise UserError(_("Upload a KPI target CSV first."))

        try:
            text = base64.b64decode(self.kpi_import_file).decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))
        except Exception as exc:
            raise ValidationError(_("The KPI CSV could not be read: %s") % exc) from exc

        required = {"code", "title", "line_type", "weight", "target_value"}
        if not rows:
            raise ValidationError(_("The KPI CSV is empty."))
        missing = required - set(rows[0].keys())
        if missing:
            raise ValidationError(_("Missing KPI CSV columns: %s") % ", ".join(sorted(missing)))

        allowed_types = dict(self.env["onehr.appraisal.score"]._fields["line_type"].selection)
        Score = self.env["onehr.appraisal.score"]
        processed = 0
        for row_number, row in enumerate(rows, start=2):
            code = (row.get("code") or "").strip()
            title = (row.get("title") or "").strip()
            line_type = (row.get("line_type") or "").strip()
            if not code or not title:
                raise ValidationError(_("Row %s requires code and title.") % row_number)
            if line_type not in allowed_types or line_type == "development":
                raise ValidationError(_("Row %s has unsupported KPI line_type.") % row_number)
            try:
                weight = float(row.get("weight") or 0)
                target_value = float(row.get("target_value") or 0)
            except ValueError as exc:
                raise ValidationError(_("Row %s has a non-numeric weight/target.") % row_number) from exc

            values = {
                "cycle_id": self.id,
                "is_template": True,
                "rater_type": "target",
                "line_type": line_type,
                "item_code": code,
                "title": title,
                "description": (row.get("description") or "").strip(),
                "weight": weight,
                "target_value": target_value,
            }
            existing = Score.search([
                ("cycle_id", "=", self.id),
                ("is_template", "=", True),
                ("item_code", "=", code),
                ("parent_score_id", "=", False),
            ], limit=1)
            existing.write(values) if existing else Score.create(values)
            processed += 1

        self._check_template_weight_total()
        return display_notification(_("Imported/updated %s KPI target(s).") % processed)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unstarted(self):
        for cycle in self:
            if cycle.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Started/closed appraisal cycles cannot be deleted; cancel or retain them.")
                )
            if cycle.form_ids.filtered(lambda form: form.state not in ("draft", "cancelled")):
                raise UserError(
                    _("A cycle containing started appraisal evidence cannot be deleted.")
                )

    def action_export_results_csv(self):
        require_appraisal_hr(self)
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "cycle_code", "employee_number", "employee", "department", "manager",
            "state", "self_score", "manager_score", "peer_score", "overall_score",
            "final_score", "final_rating", "acknowledged",
        ])
        for form in self.form_ids.sorted(key=lambda record: (record.employee_name or "", record.id)):
            writer.writerow([
                self.code,
                form.employee_number or "",
                form.employee_name or "",
                form.department_name or "",
                form.manager_name or "",
                form.state,
                form.self_score, form.manager_score, form.peer_score,
                form.overall_score, form.final_score,
                form.final_rating_label or "",
                bool(form.employee_acknowledged),
            ])
        filename = f"appraisal_results_{self.code}.csv"
        self.write({
            "export_file": base64.b64encode(output.getvalue().encode("utf-8-sig")),
            "export_filename": filename,
        })
        return display_notification(_("Result CSV prepared: %s") % filename)
