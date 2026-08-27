from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_hrbp,
    is_legal,
    is_manager,
    open_record_action,
    require_hrbp,
    require_investigator,
    require_legal,
    require_manager,
)


class OneHRDisciplineCase(models.Model):
    """Confidential employee-relations case.

    The authoritative OneHR product registry names only Case and Sanction as
    persistent Discipline models. Investigation, hearing, appeal, violation
    classification and SLA are therefore governed domains of this Case model
    rather than separate persistence invented by this addon.
    """

    _name = "onehr.discipline.case"
    _description = "OneHR Discipline Case"
    _inherit = ["onehr.mixin.audit"]
    _order = "reported_at desc, id desc"

    _reference_company_uniq = models.Constraint(
        "UNIQUE(reference, company_id)",
        "Discipline case reference must be unique per company.",
    )

    reference = fields.Char(
        string="Case Reference",
        required=True,
        default="New",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    name = fields.Char(
        string="Case Title",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    branch_scope_key = fields.Char(
        string="Optional Branch / Site Scope Key",
        tracking=True,
        index=True,
        help=(
            "Soft extension key for onehr_multicompany_branch. "
            "No reverse dependency is created."
        ),
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
        check_company=True,
        groups=(
            "onehr_discipline.group_onehr_discipline_hrbp,"
            "onehr_discipline.group_onehr_discipline_manager,"
            "onehr_discipline.group_onehr_discipline_legal"
        ),
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups=(
            "onehr_discipline.group_onehr_discipline_hrbp,"
            "onehr_discipline.group_onehr_discipline_manager,"
            "onehr_discipline.group_onehr_discipline_legal"
        ),
    )
    employee_name = fields.Char(
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        string="Employee",
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_name = fields.Char(
        related="employee_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    manager_name = fields.Char(
        related="employee_id.parent_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        string="Line Manager",
    )

    case_owner_user_id = fields.Many2one(
        "res.users",
        string="Case Owner",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    investigator_user_id = fields.Many2one(
        "res.users",
        string="Investigator",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    hrbp_user_id = fields.Many2one(
        "res.users",
        string="HRBP / Employee Relations",
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    legal_user_id = fields.Many2one(
        "res.users",
        string="Legal / IR Reviewer",
        ondelete="restrict",
        tracking=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("reported", "Reported"),
            ("investigation", "Under Investigation"),
            ("hearing", "Hearing"),
            ("decision", "Decision"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="reported",
        readonly=True,
        tracking=True,
        index=True,
    )

    reported_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        copy=False,
        index=True,
    )
    reported_by_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )
    incident_date = fields.Datetime(
        required=True,
        tracking=True,
        index=True,
    )
    incident_location = fields.Char(
        tracking=True,
        index=True,
    )
    source_type = fields.Selection(
        [
            ("manager_report", "Manager Report"),
            ("hr_observation", "HR / IR Observation"),
            ("audit", "Audit / Compliance Finding"),
            ("complaint", "Employee / Third-party Complaint"),
            ("security", "Security Incident"),
            ("other", "Other"),
        ],
        required=True,
        default="manager_report",
        tracking=True,
        index=True,
    )
    allegation_summary = fields.Text(
        required=True,
        tracking=True,
    )
    chronology = fields.Html(
        string="Incident Chronology",
        sanitize=True,
        tracking=True,
    )
    witnesses_text = fields.Text(
        string="Witnesses / Contact References",
        tracking=True,
        help=(
            "Minimum-necessary witness names/references. "
            "Do not store unrelated sensitive personal data."
        ),
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_disc_case_evidence_rel",
        "case_id",
        "attachment_id",
        string="Incident / Investigation Evidence",
        copy=False,
    )

    policy_reference = fields.Char(
        string="Policy / Rule Reference",
        tracking=True,
        index=True,
        help=(
            "Reference to the applicable PnP/SOP/rule. Kept as a soft reference "
            "so Discipline does not take ownership of those modules."
        ),
    )
    violation_code = fields.Char(
        string="Violation Classification Code",
        tracking=True,
        index=True,
    )
    violation_category = fields.Selection(
        [
            ("attendance", "Attendance / Time"),
            ("conduct", "Conduct / Behaviour"),
            ("performance", "Performance / Duty"),
            ("safety", "Safety / Security"),
            ("confidentiality", "Confidentiality / Data"),
            ("fraud", "Fraud / Integrity"),
            ("harassment", "Harassment / Workplace Respect"),
            ("policy", "Policy / Procedure Breach"),
            ("other", "Other"),
        ],
        required=True,
        default="conduct",
        tracking=True,
        index=True,
    )
    severity = fields.Selection(
        [
            ("minor", "Minor"),
            ("moderate", "Moderate"),
            ("serious", "Serious"),
            ("critical", "Critical"),
        ],
        required=True,
        default="moderate",
        tracking=True,
        index=True,
    )
    violation_weight = fields.Integer(
        string="Violation Weight",
        required=True,
        default=lambda self: self._severity_default_weight("moderate"),
        tracking=True,
        help="Configured governance weight from 0 to 100; it is not an automatic guilt score.",
    )
    prior_case_count = fields.Integer(
        compute="_compute_prior_case_count",
        string="Prior Closed Cases",
    )
    repeat_offense = fields.Boolean(
        compute="_compute_prior_case_count",
        search="_search_repeat_offense",
        string="Repeat Offense Indicator",
    )

    investigation_started_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    investigation_due_date = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    investigation_questions = fields.Text(
        tracking=True,
        help="Interview/question plan for the investigator.",
    )
    investigation_findings = fields.Html(
        sanitize=True,
        tracking=True,
    )
    investigation_recommendation = fields.Text(
        tracking=True,
    )
    evidence_assessment = fields.Selection(
        [
            ("insufficient", "Insufficient"),
            ("mixed", "Mixed / Inconclusive"),
            ("supported", "Allegation Supported"),
            ("not_supported", "Allegation Not Supported"),
        ],
        tracking=True,
    )

    hearing_scheduled_at = fields.Datetime(
        tracking=True,
        index=True,
    )
    hearing_due_date = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    hearing_location = fields.Char(
        tracking=True,
    )
    hearing_attendee_names = fields.Text(
        string="Hearing Attendees",
        tracking=True,
    )
    hearing_minutes = fields.Html(
        sanitize=True,
        tracking=True,
    )
    employee_statement = fields.Html(
        sanitize=True,
        tracking=True,
    )
    witness_statement = fields.Html(
        sanitize=True,
        tracking=True,
    )
    hearing_recommendation = fields.Text(
        tracking=True,
    )
    hearing_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_disc_case_hearing_rel",
        "case_id",
        "attachment_id",
        string="Hearing Attachments",
        copy=False,
    )

    decision_due_date = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    final_disposition = fields.Selection(
        [
            ("pending", "Pending Decision"),
            ("no_action", "No Disciplinary Action"),
            ("coaching", "Coaching / Informal Resolution"),
            ("sanction", "Formal Sanction"),
            ("unfounded", "Allegation Not Substantiated"),
            ("other", "Other Resolution"),
        ],
        required=True,
        default="pending",
        tracking=True,
        index=True,
    )
    decision_summary = fields.Html(
        sanitize=True,
        tracking=True,
    )
    decision_rationale = fields.Html(
        sanitize=True,
        tracking=True,
    )

    appeal_state = fields.Selection(
        [
            ("none", "No Appeal"),
            ("submitted", "Appeal Submitted"),
            ("review", "Under Appeal Review"),
            ("upheld", "Decision Upheld"),
            ("modified", "Decision Modified"),
            ("overturned", "Decision Overturned"),
        ],
        required=True,
        default="none",
        readonly=True,
        tracking=True,
        index=True,
    )
    appeal_submitted_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    appeal_due_date = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    appeal_reason = fields.Text(
        tracking=True,
    )
    appeal_panel_user_ids = fields.Many2many(
        "res.users",
        "onehr_disc_case_appeal_panel_rel",
        "case_id",
        "user_id",
        string="Appeal Review Panel",
        tracking=True,
    )
    appeal_review_notes = fields.Html(
        sanitize=True,
        tracking=True,
    )
    appeal_outcome_summary = fields.Html(
        sanitize=True,
        tracking=True,
    )
    appeal_decided_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    appeal_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_disc_case_appeal_rel",
        "case_id",
        "attachment_id",
        string="Appeal Attachments",
        copy=False,
    )

    sanction_ids = fields.One2many(
        "onehr.discipline.sanction",
        "case_id",
        string="Sanctions / Decisions",
        readonly=True,
    )
    sanction_count = fields.Integer(
        compute="_compute_sanction_metrics",
    )
    approved_sanction_count = fields.Integer(
        compute="_compute_sanction_metrics",
    )
    executed_sanction_count = fields.Integer(
        compute="_compute_sanction_metrics",
    )
    active_sanction_type = fields.Char(
        compute="_compute_sanction_metrics",
        string="Current Sanction",
    )

    closed_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    closed_by_name = fields.Char(
        readonly=True,
        copy=False,
    )
    retention_until = fields.Date(
        readonly=True,
        copy=False,
        index=True,
    )
    closure_note = fields.Text(
        tracking=True,
    )
    resolution_days = fields.Float(
        compute="_compute_resolution_days",
        store=True,
        string="Resolution Days",
    )

    stage_due_date = fields.Date(
        compute="_compute_stage_sla",
        store=True,
        index=True,
    )
    sla_overdue = fields.Boolean(
        compute="_compute_stage_sla",
        search="_search_sla_overdue",
    )
    days_overdue = fields.Integer(
        compute="_compute_stage_sla",
    )

    appraisal_reference = fields.Char(
        readonly=True,
        copy=False,
        index=True,
    )
    appraisal_cycle_code = fields.Char(
        readonly=True,
        copy=False,
    )
    appraisal_final_score = fields.Float(
        readonly=True,
        copy=False,
    )
    appraisal_final_rating = fields.Char(
        readonly=True,
        copy=False,
    )
    appraisal_improvement_areas = fields.Text(
        readonly=True,
        copy=False,
    )
    appraisal_refreshed_at = fields.Datetime(
        readonly=True,
        copy=False,
    )

    _IMMUTABLE_IDENTITY_FIELDS = {
        "reference",
        "company_id",
        "employee_id",
        "reported_at",
        "reported_by_id",
    }
    _ACTION_ONLY_FIELDS = {
        "state",
        "investigation_started_at",
        "investigation_due_date",
        "hearing_due_date",
        "decision_due_date",
        "appeal_state",
        "appeal_submitted_at",
        "appeal_due_date",
        "appeal_decided_at",
        "closed_at",
        "closed_by_name",
        "retention_until",
        "appraisal_reference",
        "appraisal_cycle_code",
        "appraisal_final_score",
        "appraisal_final_rating",
        "appraisal_improvement_areas",
        "appraisal_refreshed_at",
    }
    _ASSIGNMENT_FIELDS = {
        "case_owner_user_id",
        "investigator_user_id",
        "hrbp_user_id",
        "legal_user_id",
        "appeal_panel_user_ids",
    }
    _REPORT_AND_CLASSIFICATION_FIELDS = {
        "name",
        "branch_scope_key",
        "incident_date",
        "incident_location",
        "source_type",
        "allegation_summary",
        "chronology",
        "policy_reference",
        "violation_code",
        "violation_category",
        "severity",
        "violation_weight",
    }
    _INVESTIGATION_FIELDS = {
        "investigation_questions",
        "investigation_findings",
        "investigation_recommendation",
        "evidence_assessment",
        "evidence_attachment_ids",
        "witnesses_text",
    }
    _HEARING_FIELDS = {
        "hearing_scheduled_at",
        "hearing_location",
        "hearing_attendee_names",
        "hearing_minutes",
        "employee_statement",
        "witness_statement",
        "hearing_recommendation",
        "hearing_attachment_ids",
    }
    _DECISION_FIELDS = {
        "final_disposition",
        "decision_summary",
        "decision_rationale",
        "closure_note",
    }
    _APPEAL_FIELDS = {
        "appeal_reason",
        "appeal_review_notes",
        "appeal_outcome_summary",
        "appeal_attachment_ids",
    }

    @api.model
    def _config_int(self, key, default):
        raw = self.env["ir.config_parameter"].get_param(key)
        try:
            return int(raw) if raw not in (None, "", False) else int(default)
        except (TypeError, ValueError):
            return int(default)

    @api.model
    def _severity_default_weight(self, severity):
        defaults = {
            "minor": ("onehr_discipline.weight_minor", 20),
            "moderate": ("onehr_discipline.weight_moderate", 45),
            "serious": ("onehr_discipline.weight_serious", 70),
            "critical": ("onehr_discipline.weight_critical", 100),
        }
        key, fallback = defaults.get(
            severity or "moderate",
            defaults["moderate"],
        )
        return self._config_int(key, fallback)

    @api.onchange("severity")
    def _onchange_severity_weight(self):
        if self.severity:
            self.violation_weight = self._severity_default_weight(
                self.severity
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_investigator(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("reference", "New") == "New":
                vals["reference"] = (
                    self.env["ir.sequence"].next_by_code(
                        "onehr.discipline.case"
                    )
                    or "New"
                )
            severity = vals.get("severity") or "moderate"
            vals.setdefault(
                "violation_weight",
                self._severity_default_weight(severity),
            )
            vals.setdefault("case_owner_user_id", self.env.user.id)
            vals.setdefault("investigator_user_id", self.env.user.id)
            vals["state"] = "reported"
            vals["appeal_state"] = "none"
            vals["reported_at"] = fields.Datetime.now()
            vals["reported_by_id"] = self.env.user.id
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        require_investigator(self)
        requested = set(vals)

        if requested.intersection(self._IMMUTABLE_IDENTITY_FIELDS):
            raise AccessError(
                _("Case identity and reporting evidence are immutable after creation.")
            )
        if requested.intersection(self._ACTION_ONLY_FIELDS):
            raise AccessError(
                _("Case lifecycle, SLA and integration evidence change only through governed actions.")
            )

        for case in self:
            if case.state in ("closed", "cancelled"):
                raise AccessError(
                    _("Closed/cancelled discipline cases are historical records and cannot be edited.")
                )

            if requested.intersection(self._ASSIGNMENT_FIELDS):
                if not (is_manager(self.env) or is_legal(self.env)):
                    raise AccessError(
                        _("Case responsibility assignments require Discipline Manager or Legal / IR authority.")
                    )

            if not (is_hrbp(self.env) or is_manager(self.env) or is_legal(self.env)):
                if (
                    case.investigator_user_id != self.env.user
                    or requested
                    - (
                        self._INVESTIGATION_FIELDS
                        | self._HEARING_FIELDS
                    )
                ):
                    raise AccessError(
                        _(
                            "An Investigator may update only assigned investigation/hearing evidence. "
                            "Case classification, decision and governance fields require HRBP or higher authority."
                        )
                    )

            if requested.intersection(
                self._REPORT_AND_CLASSIFICATION_FIELDS
            ):
                if case.state not in ("reported", "investigation"):
                    raise AccessError(
                        _(
                            "Incident and violation classification are locked once the Hearing stage begins."
                        )
                    )

            if requested.intersection(self._INVESTIGATION_FIELDS):
                if case.state not in ("reported", "investigation"):
                    raise AccessError(
                        _("Investigation evidence is locked after the Hearing stage begins.")
                    )

            if requested.intersection(self._HEARING_FIELDS):
                if case.state not in ("investigation", "hearing"):
                    raise AccessError(
                        _("Hearing evidence may be prepared only during Investigation/Hearing.")
                    )

            if requested.intersection(self._DECISION_FIELDS):
                if case.state != "decision":
                    raise AccessError(
                        _("Decision fields may be changed only while the case is in Decision.")
                    )
                locked_sanctions = case.sanction_ids.filtered(
                    lambda sanction: sanction.state
                    in ("approval", "approved", "executed")
                )
                corrective_appeal = (
                    is_legal(self.env)
                    and case.appeal_state
                    in ("modified", "overturned")
                )
                if locked_sanctions and not corrective_appeal:
                    raise AccessError(
                        _(
                            "Case decision evidence is locked once a sanction enters approval. "
                            "Only Legal / IR may record a corrective decision after a Modified/Overturned appeal."
                        )
                    )

            if requested.intersection(self._APPEAL_FIELDS):
                if case.state != "decision":
                    raise AccessError(
                        _("Appeal evidence is maintained only while the case is in Decision.")
                    )
                if case.appeal_state in (
                    "upheld",
                    "modified",
                    "overturned",
                ):
                    raise AccessError(
                        _("Finalized appeal evidence is immutable.")
                    )
                if (
                    case.appeal_state in ("submitted", "review")
                    and "appeal_reason" in requested
                ):
                    raise AccessError(
                        _("Appeal Reason is immutable after the appeal is recorded.")
                    )

        return super().write(vals)

    def _write_action(self, values):
        """Internal lifecycle write.

        This calls the parent ORM implementation directly. A client-supplied
        context key therefore cannot bypass Discipline lifecycle guards.
        """
        return super(OneHRDisciplineCase, self).write(values)

    @api.constrains("violation_weight")
    def _check_violation_weight(self):
        for case in self:
            if not 0 <= case.violation_weight <= 100:
                raise ValidationError(
                    _("Violation Weight must be between 0 and 100.")
                )

    @api.constrains(
        "company_id",
        "employee_id",
        "case_owner_user_id",
        "investigator_user_id",
        "hrbp_user_id",
        "legal_user_id",
        "appeal_panel_user_ids",
    )
    def _check_company_scope(self):
        for case in self:
            if case.employee_id.company_id != case.company_id:
                raise ValidationError(
                    _("Employee and discipline case company must match.")
                )
            users = (
                case.case_owner_user_id
                | case.investigator_user_id
                | case.hrbp_user_id
                | case.legal_user_id
                | case.appeal_panel_user_ids
            )
            if any(
                case.company_id not in user.company_ids
                for user in users
            ):
                raise ValidationError(
                    _("Every assigned Discipline user must be allowed in the case company.")
                )

    @api.constrains("incident_date", "reported_at")
    def _check_incident_timeline(self):
        for case in self:
            if (
                case.incident_date
                and case.reported_at
                and case.incident_date > fields.Datetime.now()
            ):
                raise ValidationError(
                    _("Incident Date cannot be in the future.")
                )

    @api.depends("employee_id", "company_id", "reported_at")
    def _compute_prior_case_count(self):
        for case in self:
            if not case.employee_id:
                case.prior_case_count = 0
                case.repeat_offense = False
                continue
            count = self.search_count(
                [
                    ("id", "!=", case.id),
                    ("employee_id", "=", case.employee_id.id),
                    ("company_id", "=", case.company_id.id),
                    ("state", "=", "closed"),
                    ("reported_at", "<", case.reported_at or fields.Datetime.now()),
                ]
            )
            case.prior_case_count = count
            case.repeat_offense = bool(count)

    @api.model
    def _search_repeat_offense(self, operator, value):
        """Translate the dynamic Repeat Offense flag into a searchable ID domain.

        Repeat Offense is intentionally not stored because it depends on the
        existence and reporting date of *other* closed cases for the same
        employee/company. Storing it would become stale when sibling case
        history changes. This search method preserves the exact compute
        semantics while satisfying Odoo Search View requirements.
        """
        if operator not in ("=", "!=") or value not in (True, False, 1, 0):
            raise ValidationError(
                _(
                    "Repeat Offense supports only boolean '=' / '!=' searches."
                )
            )

        candidates = self.search(
            [
                ("employee_id", "!=", False),
                ("reported_at", "!=", False),
            ],
            order="company_id, employee_id, reported_at, id",
        )

        earliest_closed_at = {}
        repeat_case_ids = []

        for case in candidates:
            key = (case.company_id.id, case.employee_id.id)
            first_closed_at = earliest_closed_at.get(key)

            # The compute contract uses strict reported_at '<' comparison.
            # Cases reported at exactly the same instant are not treated as prior.
            if first_closed_at and first_closed_at < case.reported_at:
                repeat_case_ids.append(case.id)

            if case.state == "closed":
                if (
                    not first_closed_at
                    or case.reported_at < first_closed_at
                ):
                    earliest_closed_at[key] = case.reported_at

        requested_true = (
            (operator == "=" and bool(value))
            or (operator == "!=" and not bool(value))
        )
        return [
            (
                "id",
                "in" if requested_true else "not in",
                repeat_case_ids,
            )
        ]

    @api.depends("sanction_ids.state", "sanction_ids.sanction_type")
    def _compute_sanction_metrics(self):
        for case in self:
            approved = case.sanction_ids.filtered(
                lambda sanction: sanction.state in ("approved", "executed")
            )
            executed = case.sanction_ids.filtered(
                lambda sanction: sanction.state == "executed"
            )
            latest = approved.sorted(
                key=lambda sanction: (
                    sanction.decision_date or fields.Date.today(),
                    sanction.id,
                ),
                reverse=True,
            )[:1]
            case.sanction_count = len(case.sanction_ids)
            case.approved_sanction_count = len(approved)
            case.executed_sanction_count = len(executed)
            case.active_sanction_type = (
                dict(
                    self.env["onehr.discipline.sanction"]._fields[
                        "sanction_type"
                    ].selection
                ).get(latest.sanction_type)
                if latest
                else False
            )

    @api.depends("reported_at", "closed_at")
    def _compute_resolution_days(self):
        for case in self:
            if case.reported_at and case.closed_at:
                elapsed = (
                    fields.Datetime.to_datetime(case.closed_at)
                    - fields.Datetime.to_datetime(case.reported_at)
                )
                case.resolution_days = max(
                    0.0,
                    elapsed.total_seconds() / 86400.0,
                )
            else:
                case.resolution_days = 0.0

    @api.depends(
        "state",
        "investigation_due_date",
        "hearing_due_date",
        "decision_due_date",
        "appeal_state",
        "appeal_due_date",
    )
    def _compute_stage_sla(self):
        today = fields.Date.context_today(self)
        for case in self:
            due_date = False
            if case.appeal_state in ("submitted", "review"):
                due_date = case.appeal_due_date
            elif case.state == "investigation":
                due_date = case.investigation_due_date
            elif case.state == "hearing":
                due_date = case.hearing_due_date
            elif case.state == "decision":
                due_date = case.decision_due_date

            case.stage_due_date = due_date
            case.sla_overdue = bool(
                due_date
                and due_date < today
                and case.state not in ("closed", "cancelled")
            )
            case.days_overdue = (
                (today - due_date).days
                if due_date and due_date < today
                else 0
            )

    @api.model
    def _search_sla_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        overdue_domain = [
            ("state", "not in", ["closed", "cancelled"]),
            ("stage_due_date", "<", today),
        ]
        if (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        ):
            return overdue_domain
        return [
            "|",
            ("state", "in", ["closed", "cancelled"]),
            "|",
            ("stage_due_date", "=", False),
            ("stage_due_date", ">=", today),
        ]

    def _require_assigned_investigator_or_hrbp(self):
        require_investigator(self)
        for case in self:
            if (
                case.investigator_user_id != self.env.user
                and not (
                    is_hrbp(self.env)
                    or is_manager(self.env)
                    or is_legal(self.env)
                )
            ):
                raise AccessError(
                    _("Only the assigned Investigator or HRBP/Manager/Legal may perform this case action.")
                )

    def action_start_investigation(self):
        self._require_assigned_investigator_or_hrbp()
        for case in self:
            if case.state != "reported":
                raise UserError(
                    _("Only a Reported case can start Investigation.")
                )
            if not case.allegation_summary or not case.incident_date:
                raise UserError(
                    _("Incident Date and Allegation Summary are required before Investigation.")
                )
            due = fields.Date.context_today(case) + timedelta(
                days=case._config_int(
                    "onehr_discipline.default_investigation_sla_days",
                    7,
                )
            )
            case._write_action(
                {
                    "state": "investigation",
                    "investigation_started_at": fields.Datetime.now(),
                    "investigation_due_date": due,
                }
            )
            case._schedule_stage_activity(
                case.investigator_user_id,
                _("Discipline investigation due"),
                due,
            )
        return display_notification(
            _("Case moved to Under Investigation."),
            notification_type="info",
        )

    def action_move_to_hearing(self):
        self._require_assigned_investigator_or_hrbp()
        for case in self:
            if case.state != "investigation":
                raise UserError(
                    _("Only a case Under Investigation can move to Hearing.")
                )
            missing = []
            if not case.investigation_findings:
                missing.append(_("Investigation Findings"))
            if not case.investigation_recommendation:
                missing.append(_("Investigation Recommendation"))
            if not case.evidence_assessment:
                missing.append(_("Evidence Assessment"))
            if not case.hearing_scheduled_at:
                missing.append(_("Hearing Scheduled At"))
            if missing:
                raise UserError(
                    _("Hearing blocked. Complete: %s")
                    % ", ".join(missing)
                )
            due = fields.Date.context_today(case) + timedelta(
                days=case._config_int(
                    "onehr_discipline.default_hearing_sla_days",
                    5,
                )
            )
            case._write_action(
                {
                    "state": "hearing",
                    "hearing_due_date": due,
                }
            )
            target_user = (
                case.hrbp_user_id
                or case.case_owner_user_id
            )
            case._schedule_stage_activity(
                target_user,
                _("Discipline hearing due"),
                due,
            )
        return display_notification(
            _("Case moved to Hearing."),
            notification_type="info",
        )

    def action_move_to_decision(self):
        require_hrbp(self)
        for case in self:
            if case.state != "hearing":
                raise UserError(
                    _("Only a case in Hearing can move to Decision.")
                )
            missing = []
            if not case.hearing_minutes:
                missing.append(_("Hearing Minutes"))
            if not case.employee_statement:
                missing.append(_("Employee Statement"))
            if not case.hearing_recommendation:
                missing.append(_("Hearing Recommendation"))
            if missing:
                raise UserError(
                    _("Decision stage blocked. Complete: %s")
                    % ", ".join(missing)
                )
            due = fields.Date.context_today(case) + timedelta(
                days=case._config_int(
                    "onehr_discipline.default_decision_sla_days",
                    5,
                )
            )
            case._write_action(
                {
                    "state": "decision",
                    "decision_due_date": due,
                }
            )
            target_user = (
                case.legal_user_id
                or case.hrbp_user_id
                or case.case_owner_user_id
            )
            case._schedule_stage_activity(
                target_user,
                _("Discipline decision due"),
                due,
            )
        return display_notification(
            _("Case moved to Decision."),
            notification_type="info",
        )

    def action_create_sanction(self):
        require_hrbp(self)
        self.ensure_one()
        if self.state != "decision":
            raise UserError(
                _("A sanction/decision record can be created only in the Decision stage.")
            )
        sanction = self.env["onehr.discipline.sanction"].create(
            {
                "case_id": self.id,
                "sanction_type": (
                    "no_action"
                    if self.final_disposition
                    in ("no_action", "unfounded")
                    else "written_warning"
                ),
                "decision_basis": (
                    self.decision_summary
                    or self.hearing_recommendation
                    or self.investigation_recommendation
                ),
            }
        )
        return open_record_action(
            name=_("Disciplinary Sanction / Decision"),
            res_model="onehr.discipline.sanction",
            res_id=sanction.id,
        )

    def action_record_appeal(self):
        require_hrbp(self)
        for case in self:
            if case.state != "decision":
                raise UserError(
                    _("An appeal can be recorded only while the case is in Decision.")
                )
            if case.appeal_state != "none":
                raise UserError(
                    _("An appeal has already been recorded for this case.")
                )
            if not case.appeal_reason:
                raise UserError(
                    _("Enter the employee's Appeal Reason before recording the appeal.")
                )
            due = fields.Date.context_today(case) + timedelta(
                days=case._config_int(
                    "onehr_discipline.default_appeal_sla_days",
                    7,
                )
            )
            case._write_action(
                {
                    "appeal_state": "submitted",
                    "appeal_submitted_at": fields.Datetime.now(),
                    "appeal_due_date": due,
                }
            )
            target_user = (
                case.legal_user_id
                or case.case_owner_user_id
            )
            case._schedule_stage_activity(
                target_user,
                _("Discipline appeal review due"),
                due,
            )
        return display_notification(
            _("Employee appeal recorded."),
            notification_type="info",
        )

    def action_start_appeal_review(self):
        require_legal(self)
        for case in self:
            if case.appeal_state != "submitted":
                raise UserError(
                    _("Only a Submitted appeal can enter review.")
                )
            case._write_action({"appeal_state": "review"})
        return display_notification(
            _("Appeal moved to Legal / IR review."),
            notification_type="info",
        )

    def action_uphold_appeal(self):
        require_legal(self)
        return self._resolve_appeal("upheld")

    def action_modify_appeal(self):
        require_legal(self)
        return self._resolve_appeal("modified")

    def action_overturn_appeal(self):
        require_legal(self)
        return self._resolve_appeal("overturned")

    def _resolve_appeal(self, outcome):
        for case in self:
            if case.appeal_state not in ("submitted", "review"):
                raise UserError(
                    _("Only a Submitted/Under Review appeal can be finalized.")
                )
            if not case.appeal_outcome_summary:
                raise UserError(
                    _("Appeal Outcome Summary is required before finalization.")
                )
            case._write_action(
                {
                    "appeal_state": outcome,
                    "appeal_decided_at": fields.Datetime.now(),
                }
            )
        return display_notification(_("Appeal decision recorded."))

    def action_close_case(self):
        require_manager(self)
        for case in self:
            if case.state != "decision":
                raise UserError(
                    _("Only a case in Decision can be Closed.")
                )
            if case.appeal_state in ("submitted", "review"):
                raise UserError(
                    _("Resolve the pending appeal before closing the case.")
                )
            if not case.decision_summary:
                raise UserError(
                    _("Decision Summary is required before closure.")
                )
            if case.final_disposition == "pending":
                raise UserError(
                    _("Select a Final Disposition before closure.")
                )
            if case.final_disposition == "sanction":
                formal_executed = case.sanction_ids.filtered(
                    lambda sanction: (
                        sanction.state == "executed"
                        and sanction.sanction_type != "no_action"
                    )
                )
                if not formal_executed:
                    raise UserError(
                        _(
                            "Formal Sanction closure requires at least one non-No-Action "
                            "sanction to be executed/issued."
                        )
                    )

            retention = fields.Date.context_today(case) + relativedelta(
                years=case._config_int(
                    "onehr_discipline.default_retention_years",
                    7,
                )
            )
            case._write_action(
                {
                    "state": "closed",
                    "closed_at": fields.Datetime.now(),
                    "closed_by_name": self.env.user.name,
                    "retention_until": retention,
                }
            )
        return display_notification(
            _("Discipline case closed; investigation, decision and appeal history are retained.")
        )

    def action_cancel_case(self):
        require_legal(self)
        for case in self:
            if case.state in ("closed", "cancelled"):
                raise UserError(
                    _("Closed/Cancelled cases cannot be cancelled again.")
                )
            if case.executed_sanction_count:
                raise UserError(
                    _("A case with an executed sanction cannot be cancelled.")
                )
            case._write_action(
                {
                    "state": "cancelled",
                    "closed_at": fields.Datetime.now(),
                    "closed_by_name": self.env.user.name,
                }
            )
        return display_notification(
            _("Case cancelled; existing evidence remains retained."),
            notification_type="warning",
        )

    def _schedule_stage_activity(self, user, summary, due_date):
        self.ensure_one()
        if not user or not due_date:
            return False
        todo = self.env.ref("mail.mail_activity_data_todo")
        existing = self.activity_ids.filtered(
            lambda activity: (
                activity.activity_type_id == todo
                and activity.user_id == user
                and activity.summary == summary
                and activity.date_deadline == due_date
            )
        )
        if not existing:
            self.activity_schedule(
                todo.id,
                user_id=user.id,
                date_deadline=due_date,
                summary=summary,
                note=_(
                    "Case %s — %s"
                ) % (self.reference, self.name),
            )
        return True

    def action_print_case_outcome(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_discipline.action_report_discipline_case_outcome"
        ).report_action(self)

    def action_print_hearing_summons(self):
        self.ensure_one()
        if not self.hearing_scheduled_at:
            raise UserError(
                _("Schedule the hearing before printing a Hearing Summons.")
            )
        return self.env.ref(
            "onehr_discipline.action_report_discipline_hearing_summons"
        ).report_action(self)

    def action_print_hearing_minutes(self):
        self.ensure_one()
        if not self.hearing_minutes:
            raise UserError(
                _("Hearing Minutes have not been recorded.")
            )
        return self.env.ref(
            "onehr_discipline.action_report_discipline_hearing_minutes"
        ).report_action(self)

    def action_open_sanctions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sanctions / Decisions — %s") % self.reference,
            "res_model": "onehr.discipline.sanction",
            "view_mode": "list,form",
            "domain": [("case_id", "=", self.id)],
            "context": {"default_case_id": self.id},
        }

    @api.model
    def _cron_discipline_sla(self):
        today = fields.Date.context_today(self)
        cases = self.search(
            [
                ("state", "not in", ["closed", "cancelled"]),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        for case in cases:
            due = case.stage_due_date
            if not due or due > today + timedelta(days=2):
                continue
            if case.appeal_state in ("submitted", "review"):
                user = case.legal_user_id or case.case_owner_user_id
                summary = _("Discipline appeal review due")
            elif case.state == "investigation":
                user = case.investigator_user_id
                summary = _("Discipline investigation due")
            elif case.state == "hearing":
                user = case.hrbp_user_id or case.case_owner_user_id
                summary = _("Discipline hearing due")
            else:
                user = (
                    case.legal_user_id
                    or case.hrbp_user_id
                    or case.case_owner_user_id
                )
                summary = _("Discipline decision due")
            case._schedule_stage_activity(user, summary, due)
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unstarted_report(self):
        require_legal(self)
        for case in self:
            if (
                case.state != "reported"
                or case.sanction_ids
                or case.investigation_started_at
            ):
                raise UserError(
                    _(
                        "Only an unstarted Reported case with no sanction/investigation history may be deleted."
                    )
                )
