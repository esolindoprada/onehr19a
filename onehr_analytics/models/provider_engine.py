from odoo import _, fields
from odoo.exceptions import UserError, ValidationError


SOURCE_MODEL_SELECTION = [
    ("hr.employee", "Workforce — Employees"),
    ("hr.applicant", "Recruitment — Applicants"),
    ("onehr.recruitment.source.metric", "Recruitment — Source Metrics"),
    ("hr.attendance", "Attendance — Work Attendance"),
    ("onehr.leave.request", "Time Off — Leave Requests"),
    ("onehr.learning.session", "Learning — Sessions"),
    ("onehr.learning.enrollment", "Learning — Enrollments"),
    ("onehr.appraisal.form", "Appraisal — Forms"),
    ("onehr.payroll.export", "Payroll Bridge — Exports"),
    ("onehr.talent.pool", "Career — Talent Pool"),
    ("onehr.succession.plan", "Career — Succession Plans"),
    ("onehr.discipline.case", "Discipline — Cases"),
]

ALLOWED_SOURCE_MODELS = {key for key, _label in SOURCE_MODEL_SELECTION}

SERVICE_METRIC_SELECTION = [
    ("appraisal.appraisal_count", "Appraisal — Appraisal Count"),
    ("appraisal.closed_count", "Appraisal — Closed Count"),
    ("appraisal.completion_rate", "Appraisal — Completion Rate"),
    ("appraisal.average_final_score", "Appraisal — Average Final Score"),
    ("learning.session_count", "Learning — Session Count"),
    ("learning.learner_count", "Learning — Learner Count"),
    ("learning.training_hours", "Learning — Training Hours"),
    ("learning.completion_rate", "Learning — Completion Rate"),
    ("learning.certificate_count", "Learning — Certificates"),
    ("learning.actual_cost", "Learning — Actual Cost"),
    ("learning.cost_per_learner", "Learning — Cost per Learner"),
    ("career.active_talent_count", "Career — Active Talent Count"),
    ("career.high_potential_count", "Career — High-Potential Count"),
    ("career.succession_plan_count", "Career — Succession Plan Count"),
    ("career.succession_coverage_percent", "Career — Succession Coverage"),
    ("career.average_bench_strength", "Career — Average Bench Strength"),
    ("career.average_readiness", "Career — Average Readiness"),
]


class AnalyticsProviderEngine:
    """Fixed, non-elevating provider engine for OneHR KPI tiles.

    The engine supports a bounded allow-list of aggregate source models plus the
    explicit Appraisal, Learning and Career KPI service contracts already exposed by
    those addons. No arbitrary Python code, arbitrary model dispatch or sudo is used.
    """

    NUMERIC_FIELD_TYPES = {"integer", "float", "monetary"}
    DATE_FIELD_TYPES = {"date", "datetime"}

    def __init__(self, tile, period_start, period_end):
        self.tile = tile
        self.env = tile.env
        self.period_start = fields.Date.to_date(period_start)
        self.period_end = fields.Date.to_date(period_end)

    def evaluate(self):
        self.tile.ensure_one()
        if self.tile.provider_mode == "manual":
            return self._manual()
        if self.tile.provider_mode == "model_aggregate":
            return self._model_aggregate()
        if self.tile.provider_mode == "service":
            return self._service_metric()
        raise ValidationError(_("Unsupported analytics provider mode."))

    def validate_configuration(self):
        if self.tile.provider_mode == "manual":
            return True
        if self.tile.provider_mode == "model_aggregate":
            self._model_and_domain(validate_only=True)
            return True
        if self.tile.provider_mode == "service":
            self._validate_service_metric()
            return True
        raise ValidationError(_("Choose a supported analytics provider mode."))

    def _manual(self):
        return {
            "value": float(self.tile.manual_value or 0.0),
            "record_count": 0,
            "source": "manual",
            "payload": {"provider": "manual"},
            "drilldown_model": False,
            "drilldown_domain": [],
        }

    def _model_and_domain(self, validate_only=False):
        model_name = self.tile.source_model_name
        if model_name not in ALLOWED_SOURCE_MODELS:
            raise ValidationError(_("The selected source model is outside the approved Analytics allow-list."))
        if not self.env.registry.get(model_name):
            raise UserError(_("Analytics source capability is not installed: %s") % model_name)

        Model = self.env[model_name]
        Model.check_access("read")
        domain = list(self.tile._analytics_parse_domain(self.tile.domain_expression))

        # Mandatory company isolation is appended by the provider and cannot be
        # removed by a configured domain.
        if "company_id" in Model._fields:
            domain.append(("company_id", "=", self.tile.company_id.id))
        elif "employee_id" in Model._fields:
            domain.append(("employee_id.company_id", "=", self.tile.company_id.id))
        else:
            raise ValidationError(
                _("Source model %s has no verifiable company boundary for Analytics.") % model_name
            )

        if self.tile.branch_code:
            if "branch_id" not in Model._fields:
                raise ValidationError(
                    _("Branch-scoped KPI fails closed because source model %s has no branch_id field.") % model_name
                )
            if not self.env.registry.get("onehr.branch"):
                raise UserError(_("OneHR Branch capability is not installed."))
            Branch = self.env["onehr.branch"]
            Branch.check_access("read")
            branches = Branch.search([
                ("company_id", "=", self.tile.company_id.id),
                ("code", "=", self.tile.branch_code),
            ], limit=2)
            if len(branches) != 1:
                raise ValidationError(_("Branch code must resolve to exactly one branch in the KPI company."))
            domain.append(("branch_id", "=", branches.id))

        if self.tile.date_field_name:
            date_field = Model._fields.get(self.tile.date_field_name)
            if not date_field or date_field.type not in self.DATE_FIELD_TYPES:
                raise ValidationError(_("Date field must exist and be a Date/Datetime field on the source model."))
            if date_field.type == "date":
                domain.extend([
                    (self.tile.date_field_name, ">=", self.period_start),
                    (self.tile.date_field_name, "<=", self.period_end),
                ])
            else:
                start_dt, end_dt = self.tile._analytics_datetime_bounds(self.period_start, self.period_end)
                domain.extend([
                    (self.tile.date_field_name, ">=", start_dt),
                    (self.tile.date_field_name, "<=", end_dt),
                ])

        if self.tile.aggregate_function != "count":
            measure = Model._fields.get(self.tile.measure_field_name)
            if not measure or measure.type not in self.NUMERIC_FIELD_TYPES:
                raise ValidationError(_("Measure field must be numeric for Sum/Average analytics."))

        if validate_only:
            return Model, domain
        return Model, domain

    def _model_aggregate(self):
        Model, domain = self._model_and_domain()
        record_count = Model.search_count(domain)
        if self.tile.aggregate_function == "count":
            value = float(record_count)
        else:
            aggregate = "sum" if self.tile.aggregate_function == "sum" else "avg"
            grouped = Model.read_group(domain, [f"{self.tile.measure_field_name}:{aggregate}"], [])
            value = float((grouped[0].get(self.tile.measure_field_name) if grouped else 0.0) or 0.0)

        return {
            "value": value,
            "record_count": record_count,
            "source": self.tile.source_model_name,
            "payload": {
                "provider": "model_aggregate",
                "model": self.tile.source_model_name,
                "aggregate": self.tile.aggregate_function,
                "measure": self.tile.measure_field_name or False,
                "period_field": self.tile.date_field_name or False,
                "record_count": record_count,
            },
            "drilldown_model": self.tile.source_model_name,
            "drilldown_domain": domain,
        }

    def _validate_service_metric(self):
        metric = self.tile.service_metric_key or ""
        if metric not in {key for key, _label in SERVICE_METRIC_SELECTION}:
            raise ValidationError(_("Choose an approved Analytics service metric."))
        prefix = metric.split(".", 1)[0]
        model_name = {
            "appraisal": "onehr.appraisal.form",
            "learning": "onehr.learning.session",
            "career": "onehr.talent.pool",
        }[prefix]
        if not self.env.registry.get(model_name):
            raise UserError(_("Analytics service capability is not installed: %s") % model_name)
        return True

    def _service_metric(self):
        self._validate_service_metric()
        prefix, metric_key = self.tile.service_metric_key.split(".", 1)
        if prefix == "appraisal":
            Model = self.env["onehr.appraisal.form"]
            method = getattr(Model, "onehr_appraisal_kpi_snapshot", None)
            if not method:
                raise UserError(_("Appraisal KPI service contract is unavailable."))
            payload = method(self.tile.company_id)
            drill_model = "onehr.appraisal.form"
        elif prefix == "learning":
            Model = self.env["onehr.learning.session"]
            method = getattr(Model, "onehr_learning_kpi_snapshot", None)
            if not method:
                raise UserError(_("Learning KPI service contract is unavailable."))
            payload = method(self.tile.company_id, self.period_start, self.period_end)
            drill_model = "onehr.learning.session"
        else:
            Model = self.env["onehr.talent.pool"]
            method = getattr(Model, "onehr_career_kpi_snapshot", None)
            if not method:
                raise UserError(_("Career/Succession KPI service contract is unavailable."))
            payload = method(self.tile.company_id)
            drill_model = "onehr.talent.pool"

        if metric_key not in payload or not isinstance(payload[metric_key], (int, float)):
            raise ValidationError(_("The selected KPI metric is not numeric in the source service response."))

        return {
            "value": float(payload[metric_key] or 0.0),
            "record_count": 0,
            "source": f"service:{prefix}",
            "payload": {
                "provider": "service",
                "service": prefix,
                "metric": metric_key,
                "metric_value": float(payload[metric_key] or 0.0),
            },
            "drilldown_model": drill_model,
            "drilldown_domain": [("company_id", "=", self.tile.company_id.id)],
        }
