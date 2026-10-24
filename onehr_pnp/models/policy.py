
import hashlib
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .authority_helpers import (
    display_notification,
    is_pnp_admin,
    is_pnp_compliance,
    open_record_action,
    require_pnp_admin,
    require_pnp_compliance,
    require_pnp_owner,
)


class OneHRPolicy(models.Model):
    """Controlled policy/procedure version.

    Each row is one governed version. The policy code is stable across versions;
    version_no and previous_policy_id preserve the change history without creating
    an unapproved fourth persistent PnP model.
    """

    _name = "onehr.policy"
    _description = "OneHR Policy / Procedure"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "policy_code desc, version_no desc, id desc"

    _policy_code_version_company_uniq = models.Constraint(
        "UNIQUE(policy_code, version_no, company_id)",
        "Policy code and version must be unique per company.",
    )

    _ACTION_CONTEXT = "onehr_pnp_policy_action_write"
    _PUBLISH_ACK_CONTEXT = "onehr_pnp_publish_ack_creation"

    name = fields.Char(
        string="Policy / Procedure Title",
        required=True,
        translate=True,
        tracking=True,
        index=True,
    )
    policy_code = fields.Char(
        string="Policy Reference",
        required=True,
        default="New",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    version_no = fields.Integer(
        string="Version",
        required=True,
        default=1,
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    policy_type = fields.Selection(
        [
            ("policy", "Policy"),
            ("procedure", "Procedure"),
            ("guideline", "Guideline"),
            ("standard", "Standard"),
            ("code_of_conduct", "Code of Conduct"),
        ],
        required=True,
        default="policy",
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
    active = fields.Boolean(default=True, tracking=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approval", "Approval"),
            ("approved", "Approved"),
            ("published", "Published"),
            ("review", "Review"),
            ("archived", "Archived"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
        index=True,
    )
    is_current = fields.Boolean(
        string="Current Effective Version",
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    owner_user_id = fields.Many2one(
        "res.users",
        string="Policy Owner",
        required=True,
        default=lambda self: self._default_policy_owner(),
        ondelete="restrict",
        tracking=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    owner_name = fields.Char(
        related="owner_user_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        string="Policy Owner",
        index=True,
    )
    compliance_user_ids = fields.Many2many(
        "res.users",
        "onehr_pnp_policy_compliance_user_rel",
        "policy_id",
        "user_id",
        string="Compliance Watchers",
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
        help="Compliance users receiving policy review activities. Approval routing remains owned by OneHR Workflow Approval.",
    )

    previous_policy_id = fields.Many2one(
        "onehr.policy",
        string="Previous Version",
        ondelete="restrict",
        readonly=True,
        copy=False,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    successor_policy_ids = fields.One2many(
        "onehr.policy",
        "previous_policy_id",
        string="Successor Versions",
        readonly=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )

    effective_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    effective_to = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    review_due_date = fields.Date(
        required=True,
        tracking=True,
        index=True,
    )
    retention_until = fields.Date(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    review_interval_months = fields.Integer(
        required=True,
        default=12,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    ack_reminder_days = fields.Integer(
        required=True,
        default=7,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    retention_years = fields.Integer(
        required=True,
        default=7,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )

    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("normal", "Normal"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="normal",
        required=True,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
        help="Structured input to OneHR Workflow Approval routing.",
    )
    branch_scope_key = fields.Char(
        string="Optional Branch / Site Scope Key",
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
        help="Soft extension key. onehr_multicompany_branch may resolve it without becoming a hard dependency.",
    )

    target_all_employees = fields.Boolean(
        string="All Active Employees in Company",
        default=False,
        tracking=True,
    )
    target_department_ids = fields.Many2many(
        "hr.department",
        "onehr_pnp_policy_department_rel",
        "policy_id",
        "department_id",
        string="Target Departments / Units",
        tracking=True,
        check_company=True,
    )
    target_job_ids = fields.Many2many(
        "hr.job",
        "onehr_pnp_policy_job_rel",
        "policy_id",
        "job_id",
        string="Target Jobs / Roles",
        tracking=True,
        check_company=True,
    )
    target_employee_ids = fields.Many2many(
        "hr.employee",
        "onehr_pnp_policy_employee_rel",
        "policy_id",
        "employee_id",
        string="Specific Employees",
        tracking=True,
        check_company=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )

    has_specific_employee_targets = fields.Boolean(
        compute="_compute_has_specific_employee_targets",
        store=True,
        compute_sudo=True,
        readonly=True,
        string="Has Specific Employee Targets",
        help="Privacy-safe indicator used by owner-side validation without exposing employee identities.",
    )

    acknowledgement_required = fields.Boolean(
        default=True,
        tracking=True,
    )
    evidence_required = fields.Boolean(
        default=False,
        tracking=True,
    )
    evidence_due_days = fields.Integer(
        default=14,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )

    purpose = fields.Html(
        tracking=True,
        sanitize=True,
        translate=True,
    )
    scope = fields.Html(
        tracking=True,
        sanitize=True,
        translate=True,
    )
    policy_statement = fields.Html(
        string="Policy / Procedure",
        tracking=True,
        sanitize=True,
        translate=True,
    )
    responsibilities = fields.Html(
        tracking=True,
        sanitize=True,
        translate=True,
    )
    controls = fields.Html(
        string="Controls / Compliance Requirements",
        tracking=True,
        sanitize=True,
        translate=True,
    )
    exceptions = fields.Html(
        string="Exceptions / Escalation",
        tracking=True,
        sanitize=True,
        translate=True,
    )
    references = fields.Html(
        string="References / Related Documents",
        tracking=True,
        sanitize=True,
        translate=True,
    )
    change_summary = fields.Text(
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
        help="Mandatory for version 2 and later.",
    )
    supporting_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_pnp_policy_attachment_rel",
        "policy_id",
        "attachment_id",
        string="Supporting Files / Annexes",
        copy=True,
        tracking=True,
        help=(
            "Draft/reference annexes attached to the policy version. "
            "The immutable published archive remains owned by OneHR Document."
        ),
    )
    related_sop_references = fields.Char(
        string="Related SOP References",
        tracking=True,
        help="Comma-separated OneHR SOP codes. This remains a soft runtime integration; SOP ownership is not duplicated in PnP.",
    )

    document_category_id = fields.Many2one(
        "onehr.document.category",
        string="Archive Document Category",
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True)]",
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    archive_document_id = fields.Many2one(
        "onehr.document",
        string="Document Archive",
        ondelete="restrict",
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    archive_document_version_id = fields.Many2one(
        "onehr.document.version",
        string="Archived Policy Snapshot",
        ondelete="restrict",
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )

    last_approval_request_id = fields.Many2one(
        "onehr.approval.request",
        string="Latest Finalized Approval",
        ondelete="restrict",
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    approval_finalized_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    approved_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    approved_by_name = fields.Char(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    published_at = fields.Datetime(
        readonly=True,
        copy=False,
        index=True,
    )
    published_by_name = fields.Char(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    review_started_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    archived_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    archived_by_name = fields.Char(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    content_fingerprint = fields.Char(
        readonly=True,
        copy=False,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )

    ack_ids = fields.One2many(
        "onehr.policy.ack",
        "policy_id",
        string="Acknowledgements",
        readonly=True,
    )
    evidence_ids = fields.One2many(
        "onehr.policy.evidence",
        "policy_id",
        string="Compliance Evidence",
        readonly=True,
    )

    audience_count = fields.Integer(
        compute="_compute_compliance_metrics",
        store=True,
    )
    acknowledged_count = fields.Integer(
        compute="_compute_compliance_metrics",
        store=True,
    )
    pending_ack_count = fields.Integer(
        compute="_compute_compliance_metrics",
        store=True,
    )
    acknowledgement_rate = fields.Float(
        compute="_compute_compliance_metrics",
        store=True,
        string="Acknowledgement %",
    )
    verified_evidence_count = fields.Integer(
        compute="_compute_compliance_metrics",
        store=True,
    )
    evidence_covered_employee_count = fields.Integer(
        compute="_compute_compliance_metrics",
        store=True,
        string="Employees with Verified Evidence",
    )
    evidence_coverage_rate = fields.Float(
        compute="_compute_compliance_metrics",
        store=True,
        string="Evidence Coverage %",
    )
    review_overdue = fields.Boolean(
        compute="_compute_review_status",
        search="_search_review_overdue",
    )
    version_count = fields.Integer(
        compute="_compute_version_count",
    )

    publication_template_id = fields.Many2one(
        "mail.template",
        string="Publication Template",
        ondelete="restrict",
        default=lambda self: self.env.ref(
            "onehr_pnp.mail_template_policy_publication",
            raise_if_not_found=False,
        ),
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    reminder_template_id = fields.Many2one(
        "mail.template",
        string="Acknowledgement Reminder Template",
        ondelete="restrict",
        default=lambda self: self.env.ref(
            "onehr_pnp.mail_template_policy_ack_reminder",
            raise_if_not_found=False,
        ),
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    auto_email_reminders = fields.Boolean(
        default=False,
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )

    _DEFINITION_FIELDS = {
        "name",
        "policy_type",
        "company_id",
        "effective_from",
        "review_due_date",
        "review_interval_months",
        "ack_reminder_days",
        "retention_years",
        "risk_level",
        "branch_scope_key",
        "target_all_employees",
        "target_department_ids",
        "target_job_ids",
        "target_employee_ids",
        "acknowledgement_required",
        "evidence_required",
        "evidence_due_days",
        "purpose",
        "scope",
        "policy_statement",
        "responsibilities",
        "controls",
        "exceptions",
        "references",
        "change_summary",
        "supporting_attachment_ids",
        "related_sop_references",
        "document_category_id",
    }

    @api.model
    def _default_policy_owner(self):
        raw = self.env["ir.config_parameter"].get_param(
            "onehr_pnp.default_owner_user_id"
        )
        try:
            user_id = int(raw or 0)
        except (TypeError, ValueError):
            user_id = 0

        user = self.env["res.users"].browse(user_id).exists()
        if (
            user
            and self.env.company in user.company_ids
            and user.has_group("onehr_pnp.group_onehr_pnp_owner")
        ):
            return user
        return self.env.user

    @api.model
    def _config_int(self, key, default):
        raw = self.env["ir.config_parameter"].get_param(key)
        try:
            value = int(raw) if raw not in (None, "", False) else int(default)
        except (TypeError, ValueError):
            value = int(default)
        return value

    @api.model
    def _default_document_category(self):
        raw = self.env["ir.config_parameter"].get_param(
            "onehr_pnp.default_document_category_id"
        )
        try:
            category_id = int(raw or 0)
        except (TypeError, ValueError):
            category_id = 0
        return self.env["onehr.document.category"].browse(category_id).exists()

    @api.model_create_multi
    def create(self, vals_list):
        require_pnp_owner(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("policy_code", "New") == "New":
                vals["policy_code"] = (
                    self.env["ir.sequence"].next_by_code("onehr.policy") or "New"
                )

            vals.setdefault(
                "review_interval_months",
                self._config_int("onehr_pnp.default_review_months", 12),
            )
            vals.setdefault(
                "ack_reminder_days",
                self._config_int("onehr_pnp.default_ack_reminder_days", 7),
            )
            vals.setdefault(
                "retention_years",
                self._config_int("onehr_pnp.default_retention_years", 7),
            )

            effective_from = fields.Date.to_date(
                vals.get("effective_from") or fields.Date.context_today(self)
            )
            vals["effective_from"] = effective_from
            if not vals.get("review_due_date"):
                vals["review_due_date"] = effective_from + relativedelta(
                    months=vals["review_interval_months"]
                )

            if not vals.get("document_category_id"):
                category = self._default_document_category()
                if category:
                    vals["document_category_id"] = category.id

            vals["state"] = "draft"
            vals["is_current"] = False
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)

        require_pnp_owner(self)
        requested = set(vals)

        lifecycle_fields = {
            "policy_code",
            "version_no",
            "state",
            "is_current",
            "previous_policy_id",
            "effective_to",
            "retention_until",
            "last_approval_request_id",
            "approval_finalized_at",
            "approved_at",
            "approved_by_name",
            "published_at",
            "published_by_name",
            "review_started_at",
            "archived_at",
            "archived_by_name",
            "content_fingerprint",
            "archive_document_id",
            "archive_document_version_id",
        }
        if lifecycle_fields.intersection(requested):
            raise AccessError(
                _("Policy lifecycle/history fields change only through governed actions.")
            )

        for policy in self:
            if (
                policy.state not in ("draft", "rejected")
                and self._DEFINITION_FIELDS.intersection(requested)
            ):
                raise AccessError(
                    _(
                        "Policy definition, content and audience are locked after submission. "
                        "Create a controlled successor version for changes."
                    )
                )
        return super().write(vals)

    @api.depends("target_employee_ids")
    def _compute_has_specific_employee_targets(self):
        for policy in self:
            policy.has_specific_employee_targets = bool(
                policy.target_employee_ids
            )

    @api.depends(
        "ack_ids.state",
        "evidence_ids.state",
        "evidence_ids.evidence_scope",
        "evidence_ids.employee_id",
        "evidence_ids.unit_department_id",
    )
    def _compute_compliance_metrics(self):
        for policy in self:
            acknowledgements = policy.ack_ids
            acknowledged = acknowledgements.filtered(
                lambda ack: ack.state == "acknowledged"
            )
            pending = acknowledgements.filtered(
                lambda ack: ack.state == "pending"
            )
            verified = policy.evidence_ids.filtered(
                lambda evidence: evidence.state == "verified"
            )
            covered_employee_ids = set()
            for evidence in verified:
                if evidence.evidence_scope == "employee" and evidence.employee_id:
                    covered_employee_ids.add(evidence.employee_id.id)
                elif (
                    evidence.evidence_scope == "unit"
                    and evidence.unit_department_id
                ):
                    covered_employee_ids.update(
                        acknowledgements.filtered(
                            lambda ack: ack.department_id
                            == evidence.unit_department_id
                        ).mapped("employee_id").ids
                    )
                elif evidence.evidence_scope == "policy":
                    covered_employee_ids.update(
                        acknowledgements.mapped("employee_id").ids
                    )

            policy.audience_count = len(acknowledgements)
            policy.acknowledged_count = len(acknowledged)
            policy.pending_ack_count = len(pending)
            if acknowledgements:
                policy.acknowledgement_rate = (
                    len(acknowledged) * 100.0 / len(acknowledgements)
                    if policy.acknowledgement_required
                    else 100.0
                )
            else:
                policy.acknowledgement_rate = 0.0

            policy.verified_evidence_count = len(verified)
            policy.evidence_covered_employee_count = len(covered_employee_ids)
            if acknowledgements:
                policy.evidence_coverage_rate = (
                    len(covered_employee_ids) * 100.0 / len(acknowledgements)
                    if policy.evidence_required
                    else 100.0
                )
            else:
                policy.evidence_coverage_rate = 0.0

    def _compute_review_status(self):
        today = fields.Date.context_today(self)
        for policy in self:
            policy.review_overdue = bool(
                policy.is_current
                and policy.state in ("published", "review")
                and policy.review_due_date
                and policy.review_due_date < today
            )

    @api.model
    def _search_review_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        due_domain = [
            ("is_current", "=", True),
            ("state", "in", ["published", "review"]),
            ("review_due_date", "<", today),
        ]
        if (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        ):
            return due_domain
        return [
            "|",
            ("is_current", "=", False),
            "|",
            ("state", "not in", ["published", "review"]),
            "|",
            ("review_due_date", "=", False),
            ("review_due_date", ">=", today),
        ]

    def _compute_version_count(self):
        for policy in self:
            policy.version_count = self.search_count(
                [
                    ("policy_code", "=", policy.policy_code),
                    ("company_id", "=", policy.company_id.id),
                ]
            )

    @api.constrains(
        "effective_from",
        "effective_to",
        "review_due_date",
    )
    def _check_dates(self):
        for policy in self:
            if (
                policy.effective_to
                and policy.effective_to < policy.effective_from
            ):
                raise ValidationError(
                    _("Effective To cannot be earlier than Effective From.")
                )
            if policy.review_due_date < policy.effective_from:
                raise ValidationError(
                    _("Review Due Date cannot be earlier than Effective From.")
                )

    @api.constrains(
        "review_interval_months",
        "ack_reminder_days",
        "retention_years",
        "evidence_due_days",
    )
    def _check_governance_numbers(self):
        for policy in self:
            if policy.review_interval_months < 1:
                raise ValidationError(_("Review interval must be at least one month."))
            if policy.ack_reminder_days < 1:
                raise ValidationError(
                    _("Acknowledgement reminder interval must be at least one day.")
                )
            if policy.retention_years < 1:
                raise ValidationError(_("Retention must be at least one year."))
            if policy.evidence_due_days < 0:
                raise ValidationError(_("Evidence due days cannot be negative."))

    @api.constrains(
        "target_all_employees",
        "target_department_ids",
        "target_job_ids",
        "target_employee_ids",
        "company_id",
    )
    def _check_audience_scope(self):
        for policy in self:
            if policy.target_all_employees and (
                policy.target_department_ids
                or policy.target_job_ids
                or policy.target_employee_ids
            ):
                raise ValidationError(
                    _(
                        "When All Active Employees is selected, remove specific department, job and employee targets."
                    )
                )

            if any(
                department.company_id
                and department.company_id != policy.company_id
                for department in policy.target_department_ids
            ):
                raise ValidationError(
                    _("Every target department must belong to the policy company.")
                )
            if any(
                job.company_id and job.company_id != policy.company_id
                for job in policy.target_job_ids
            ):
                raise ValidationError(
                    _("Every target job must belong to the policy company.")
                )
            if any(
                employee.company_id != policy.company_id
                for employee in policy.target_employee_ids
            ):
                raise ValidationError(
                    _("Every target employee must belong to the policy company.")
                )

    @api.constrains(
        "owner_user_id",
        "compliance_user_ids",
        "company_id",
        "document_category_id",
    )
    def _check_governance_scope(self):
        for policy in self:
            if policy.company_id not in policy.owner_user_id.company_ids:
                raise ValidationError(
                    _("Policy Owner must be allowed in the policy company.")
                )
            if any(
                policy.company_id not in user.company_ids
                for user in policy.compliance_user_ids
            ):
                raise ValidationError(
                    _("Compliance Watchers must be allowed in the policy company.")
                )
            if (
                policy.document_category_id
                and policy.document_category_id.company_id
                and policy.document_category_id.company_id != policy.company_id
            ):
                raise ValidationError(
                    _("Archive Document Category must be global or belong to the policy company.")
                )

    @api.constrains("is_current", "state", "policy_code", "company_id")
    def _check_single_current_version(self):
        for policy in self.filtered("is_current"):
            if policy.state not in ("published", "review"):
                raise ValidationError(
                    _("Only Published or Review policy versions can be current.")
                )
            duplicate = self.search(
                [
                    ("id", "!=", policy.id),
                    ("policy_code", "=", policy.policy_code),
                    ("company_id", "=", policy.company_id.id),
                    ("is_current", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Only one current version is allowed for the same policy code and company.")
                )

    def _write_action(self, values):
        return self.with_context(
            **{self._ACTION_CONTEXT: True}
        ).write(values)

    def _resolve_audience_employees(self):
        self.ensure_one()
        Employee = self.env["hr.employee"]
        domain = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ]
        if self.target_all_employees:
            return Employee.search(domain)

        employees = self.target_employee_ids.filtered("active")
        if self.target_department_ids:
            employees |= Employee.search(
                domain
                + [("department_id", "in", self.target_department_ids.ids)]
            )
        if self.target_job_ids:
            employees |= Employee.search(
                domain + [("job_id", "in", self.target_job_ids.ids)]
            )
        return employees.filtered(
            lambda employee: employee.company_id == self.company_id
        )

    def _required_content_missing(self):
        self.ensure_one()
        required = [
            ("purpose", _("Purpose")),
            ("scope", _("Scope")),
            ("policy_statement", _("Policy / Procedure")),
            ("responsibilities", _("Responsibilities")),
            ("controls", _("Controls / Compliance Requirements")),
            ("references", _("References / Related Documents")),
        ]
        missing = [
            label
            for field_name, label in required
            if not self[field_name]
        ]
        if not (
            self.target_all_employees
            or self.target_department_ids
            or self.target_job_ids
            or self.has_specific_employee_targets
            or self.branch_scope_key
        ):
            missing.append(_("Publication Audience"))
        if self.version_no > 1 and not self.change_summary:
            missing.append(_("Change Summary"))
        return missing

    def _content_fingerprint_payload(self):
        self.ensure_one()
        values = [
            self.policy_code or "",
            str(self.version_no),
            self.policy_type or "",
            str(self.effective_from or ""),
            str(self.review_due_date or ""),
            self.risk_level or "",
            self.branch_scope_key or "",
            self.purpose or "",
            self.scope or "",
            self.policy_statement or "",
            self.responsibilities or "",
            self.controls or "",
            self.exceptions or "",
            self.references or "",
            self.change_summary or "",
            ",".join(map(str, sorted(self.supporting_attachment_ids.ids))),
            self.related_sop_references or "",
            str(bool(self.target_all_employees)),
            ",".join(map(str, sorted(self.target_department_ids.ids))),
            ",".join(map(str, sorted(self.target_job_ids.ids))),
            ",".join(map(str, sorted(self.target_employee_ids.ids))),
            str(bool(self.acknowledgement_required)),
            str(bool(self.evidence_required)),
            str(self.evidence_due_days),
        ]
        return "\n---\n".join(values).encode("utf-8")

    def _calculate_fingerprint(self):
        self.ensure_one()
        return hashlib.sha256(
            self._content_fingerprint_payload()
        ).hexdigest()

    def _approval_payload(self):
        self.ensure_one()
        return {
            "policy_reference": self.policy_code,
            "version": self.version_no,
            "title": self.name,
            "policy_type": self.policy_type,
            "company_id": self.company_id.id,
            "owner": self.owner_name,
            "effective_from": str(self.effective_from or ""),
            "review_due_date": str(self.review_due_date or ""),
            "risk_level": self.risk_level,
            "acknowledgement_required": bool(self.acknowledgement_required),
            "evidence_required": bool(self.evidence_required),
        }

    def _approval_branch_scope_key(self):
        self.ensure_one()
        return self.branch_scope_key or False

    def _approval_rule_context(self):
        self.ensure_one()
        context = super()._approval_rule_context()
        context.update(
            {
                "company_id": self.company_id.id,
                "branch_scope_key": self._approval_branch_scope_key(),
                "document_type": f"onehr.policy.{self.policy_type}",
                "risk_level": self.risk_level,
                "manager_user_ids": [],
                "approver_user_ids_by_key": {
                    "policy_compliance": self.compliance_user_ids.ids,
                },
                "extra": {
                    "policy_type": self.policy_type,
                    "acknowledgement_required": bool(
                        self.acknowledgement_required
                    ),
                    "evidence_required": bool(self.evidence_required),
                },
            }
        )
        return context

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        return self.state in ("approval", "rejected", "draft")

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        now = fields.Datetime.now()

        if self.state != "approval":
            raise UserError(
                _("Policy approval finalized while the policy is not in Approval state.")
            )

        if decision == "approve":
            self._write_action(
                {
                    "state": "approved",
                    "last_approval_request_id": request.id,
                    "approval_finalized_at": now,
                    "approved_at": now,
                    "approved_by_name": self.env.user.name,
                    "content_fingerprint": self._calculate_fingerprint(),
                }
            )
        elif decision == "reject":
            self._write_action(
                {
                    "state": "rejected",
                    "last_approval_request_id": request.id,
                    "approval_finalized_at": now,
                    "approved_at": False,
                    "approved_by_name": False,
                    "content_fingerprint": False,
                }
            )
        else:
            raise ValidationError(_("Unsupported policy approval decision."))

        return True

    def action_preview_audience(self):
        require_pnp_compliance(self)
        self.ensure_one()
        employees = self._resolve_audience_employees()
        linked = employees.filtered("user_id")
        return display_notification(
            _(
                "%s active employee(s) resolved; %s have linked OneHR users for online acknowledgement."
            )
            % (len(employees), len(linked)),
            notification_type="info",
        )

    def action_submit_policy_approval(self):
        require_pnp_owner(self)
        self.ensure_one()

        if self.state not in ("draft", "rejected"):
            raise UserError(
                _("Only Draft or Rejected policy versions can be submitted.")
            )
        if not self.env.su and self.owner_user_id != self.env.user:
            raise AccessError(
                _(
                    "Only the assigned Policy Owner may submit this version. "
                    "Reassign the owner in Draft when responsibility changes."
                )
            )

        missing = self._required_content_missing()
        if missing:
            raise UserError(
                _("Approval blocked. Complete: %s") % ", ".join(missing)
            )

        active_requests = self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", self._name),
                ("source_res_id", "=", self.id),
                ("state", "in", ["draft", "submitted", "pending"]),
            ],
            limit=1,
        )
        if active_requests:
            raise UserError(
                _("An active OneHR approval request already exists for this policy version.")
            )

        self._write_action(
            {
                "state": "approval",
                "content_fingerprint": False,
            }
        )
        return self.action_submit_for_approval()

    def action_return_to_draft(self):
        require_pnp_compliance(self)
        for policy in self:
            if policy.state not in ("rejected", "approved"):
                raise UserError(
                    _("Only Rejected or not-yet-published Approved policies can return to Draft.")
                )
            if policy.archive_document_version_id or policy.ack_ids:
                raise UserError(
                    _("Policy publication evidence exists; create a successor version instead.")
                )
            policy._write_action(
                {
                    "state": "draft",
                    "last_approval_request_id": False,
                    "approval_finalized_at": False,
                    "approved_at": False,
                    "approved_by_name": False,
                    "content_fingerprint": False,
                }
            )
        return display_notification(
            _("Policy returned to Draft."),
            notification_type="warning",
        )

    def _archive_html(self):
        self.ensure_one()
        return "".join(
            [
                f"<h2>{self.policy_code} — {self.name}</h2>",
                f"<p><strong>Version:</strong> {self.version_no}</p>",
                f"<p><strong>Type:</strong> {self.policy_type}</p>",
                f"<p><strong>Effective:</strong> {self.effective_from}</p>",
                f"<p><strong>Review Due:</strong> {self.review_due_date}</p>",
                "<h3>Purpose</h3>",
                self.purpose or "<p>Not specified.</p>",
                "<h3>Scope</h3>",
                self.scope or "<p>Not specified.</p>",
                "<h3>Policy / Procedure</h3>",
                self.policy_statement or "<p>Not specified.</p>",
                "<h3>Responsibilities</h3>",
                self.responsibilities or "<p>Not specified.</p>",
                "<h3>Controls / Compliance Requirements</h3>",
                self.controls or "<p>Not specified.</p>",
                "<h3>Exceptions / Escalation</h3>",
                self.exceptions or "<p>Not specified.</p>",
                "<h3>References / Related Documents</h3>",
                self.references or "<p>Not specified.</p>",
            ]
        )

    def _ensure_document_archive(self):
        self.ensure_one()
        if not self.document_category_id:
            raise UserError(
                _("Configure an Archive Document Category before publication.")
            )
        if (
            self.document_category_id.sensitivity == "restricted"
            and not self.env.user.has_group(
                "onehr_document.group_onehr_document_compliance"
            )
        ):
            raise UserError(
                _(
                    "Restricted archive categories require explicit OneHR Document Compliance authority. "
                    "Choose an Internal/Confidential category or publish under approved Document Compliance authority."
                )
            )

        document = self.archive_document_id
        if not document and self.previous_policy_id:
            document = self.previous_policy_id.archive_document_id

        if not document:
            source_model = self.env["ir.model"].search(
                [("model", "=", self._name)],
                limit=1,
            )
            if not source_model:
                raise UserError(_("The OneHR Policy model registry entry was not found."))

            document = self.env["onehr.document"].create(
                {
                    "name": f"{self.policy_code} — {self.name}",
                    "category_id": self.document_category_id.id,
                    "company_id": self.company_id.id,
                    "responsible_user_id": self.env.user.id,
                    "source_model_id": source_model.id,
                    "source_res_id": self.id,
                    "valid_from": self.effective_from,
                    "keywords": (
                        f"Policy, PnP, {self.policy_code}, {self.policy_type}"
                    ),
                }
            )

        archive_version = self.env["onehr.document.version"].create(
            {
                "document_id": document.id,
                "effective_from": self.effective_from,
                "rendered_subject": (
                    f"{self.policy_code} — {self.name} / V{self.version_no}"
                ),
                "rendered_content_html": self._archive_html(),
            }
        )
        archive_version.action_issue()
        return document, archive_version

    def _generate_acknowledgements(self):
        self.ensure_one()
        if self.ack_ids:
            raise UserError(
                _("Acknowledgement audience evidence already exists for this policy version.")
            )

        employees = self._resolve_audience_employees()
        if self.branch_scope_key and not employees:
            raise UserError(
                _(
                    "This policy uses a Branch / Site Scope Key but no audience was resolved. "
                    "Install/configure the branch extension or add an explicit department/job/employee audience."
                )
            )
        if not employees:
            raise UserError(
                _("Publication audience resolves to no active employees.")
            )

        due_date = fields.Date.context_today(self) + timedelta(
            days=self.ack_reminder_days
        )
        vals_list = [
            {
                "policy_id": self.id,
                "employee_id": employee.id,
                "due_date": due_date,
            }
            for employee in employees
        ]
        return self.env["onehr.policy.ack"].with_context(
            **{self._PUBLISH_ACK_CONTEXT: True}
        ).create(vals_list)

    def _supersede_previous_current(self):
        self.ensure_one()
        previous_current = self.search(
            [
                ("id", "!=", self.id),
                ("policy_code", "=", self.policy_code),
                ("company_id", "=", self.company_id.id),
                ("is_current", "=", True),
            ]
        )
        for previous in previous_current:
            values = {
                "state": "archived",
                "is_current": False,
                "archived_at": fields.Datetime.now(),
                "archived_by_name": self.env.user.name,
            }
            if not previous.effective_to:
                if self.effective_from > previous.effective_from:
                    values["effective_to"] = (
                        self.effective_from - timedelta(days=1)
                    )
                else:
                    values["effective_to"] = previous.effective_from
            previous._write_action(values)

            if (
                previous.archive_document_version_id
                and previous.archive_document_version_id.state
                not in ("archived", "superseded")
            ):
                previous.archive_document_version_id.action_archive()

    def action_publish(self):
        require_pnp_compliance(self)
        for policy in self:
            if policy.state != "approved":
                raise UserError(_("Only Approved policy versions can be Published."))

            if (
                not policy.last_approval_request_id
                or policy.last_approval_request_id.state != "approved"
                or policy.last_approval_request_id.final_decision != "approve"
            ):
                raise UserError(
                    _("A finalized approved OneHR Workflow request is required before publication.")
                )

            current_fingerprint = policy._calculate_fingerprint()
            if (
                not policy.content_fingerprint
                or policy.content_fingerprint != current_fingerprint
            ):
                raise UserError(
                    _(
                        "Policy content/audience changed after approval. Return to Draft and obtain approval again."
                    )
                )

            document, archive_version = policy._ensure_document_archive()
            policy._generate_acknowledgements()
            policy._supersede_previous_current()

            retention_until = policy.effective_from + relativedelta(
                years=policy.retention_years
            )
            policy._write_action(
                {
                    "state": "published",
                    "is_current": True,
                    "retention_until": retention_until,
                    "archive_document_id": document.id,
                    "archive_document_version_id": archive_version.id,
                    "published_at": fields.Datetime.now(),
                    "published_by_name": self.env.user.name,
                }
            )

            policy.onehr_mark_approval_executed(
                policy.last_approval_request_id
            )
            policy._schedule_ack_activities()

        return display_notification(
            _("Policy published; archive snapshot and employee compliance assignments were created.")
        )

    def _schedule_ack_activities(self):
        todo = self.env.ref("mail.mail_activity_data_todo")
        for policy in self:
            for ack in policy.ack_ids.filtered(
                lambda item: item.state == "pending" and item.employee_user_id
            ):
                existing = ack.activity_ids.filtered(
                    lambda activity: (
                        activity.activity_type_id == todo
                        and activity.user_id == ack.employee_user_id
                        and activity.summary == _("Policy acknowledgement")
                    )
                )
                if not existing:
                    ack.activity_schedule(
                        todo.id,
                        user_id=ack.employee_user_id.id,
                        date_deadline=ack.due_date,
                        summary=_("Policy acknowledgement"),
                        note=_(
                            "Read and acknowledge %s version %s."
                        ) % (policy.policy_code, policy.version_no),
                    )

    def action_start_review(self):
        require_pnp_compliance(self)
        for policy in self:
            if policy.state != "published" or not policy.is_current:
                raise UserError(
                    _("Only the current Published policy can enter Review.")
                )
            policy._write_action(
                {
                    "state": "review",
                    "review_started_at": fields.Datetime.now(),
                }
            )
        return display_notification(
            _("Policy entered periodic Review."),
            notification_type="info",
        )

    def action_complete_review_no_change(self):
        require_pnp_compliance(self)
        for policy in self:
            if policy.state != "review" or not policy.is_current:
                raise UserError(_("Only a current policy in Review can be renewed unchanged."))
            next_due = fields.Date.context_today(policy) + relativedelta(
                months=policy.review_interval_months
            )
            policy._write_action(
                {
                    "state": "published",
                    "review_due_date": next_due,
                    "review_started_at": False,
                }
            )
            policy.message_post(
                body=_(
                    "Periodic review completed with no controlled-content change. "
                    "Next review due: %s."
                )
                % next_due
            )
        return display_notification(_("Periodic review completed; policy remains Published."))

    def action_create_revision(self):
        # Revision copies the complete approved audience, including optional
        # employee-specific targets. Compliance authority prevents a Policy Owner
        # from bypassing PII field restrictions while preserving the version scope.
        require_pnp_compliance(self)
        self.ensure_one()
        if self.state not in ("published", "review"):
            raise UserError(
                _("A controlled revision starts from a Published or Review policy version.")
            )

        existing = self.search(
            [
                ("previous_policy_id", "=", self.id),
                ("state", "in", ["draft", "approval", "approved", "rejected"]),
            ],
            order="version_no desc, id desc",
            limit=1,
        )
        if existing:
            return open_record_action(
                name=_("Policy Revision"),
                res_model=self._name,
                res_id=existing.id,
            )

        values = {
            "name": self.name,
            "policy_code": self.policy_code,
            "version_no": self.version_no + 1,
            "policy_type": self.policy_type,
            "company_id": self.company_id.id,
            "owner_user_id": self.owner_user_id.id,
            "compliance_user_ids": [Command.set(self.compliance_user_ids.ids)],
            "previous_policy_id": self.id,
            "effective_from": fields.Date.context_today(self),
            "review_interval_months": self.review_interval_months,
            "ack_reminder_days": self.ack_reminder_days,
            "retention_years": self.retention_years,
            "risk_level": self.risk_level,
            "branch_scope_key": self.branch_scope_key,
            "target_all_employees": self.target_all_employees,
            "target_department_ids": [Command.set(self.target_department_ids.ids)],
            "target_job_ids": [Command.set(self.target_job_ids.ids)],
            "target_employee_ids": [Command.set(self.target_employee_ids.ids)],
            "acknowledgement_required": self.acknowledgement_required,
            "evidence_required": self.evidence_required,
            "evidence_due_days": self.evidence_due_days,
            "purpose": self.purpose,
            "scope": self.scope,
            "policy_statement": self.policy_statement,
            "responsibilities": self.responsibilities,
            "controls": self.controls,
            "exceptions": self.exceptions,
            "references": self.references,
            "change_summary": _(
                "Controlled revision from version %s."
            )
            % self.version_no,
            "supporting_attachment_ids": [
                Command.set(self.supporting_attachment_ids.ids)
            ],
            "related_sop_references": self.related_sop_references,
            "document_category_id": self.document_category_id.id,
            "archive_document_id": self.archive_document_id.id,
            "publication_template_id": self.publication_template_id.id,
            "reminder_template_id": self.reminder_template_id.id,
            "auto_email_reminders": self.auto_email_reminders,
        }
        revision = self.create(values)
        return open_record_action(
            name=_("Policy Revision"),
            res_model=self._name,
            res_id=revision.id,
        )

    def action_archive(self):
        require_pnp_compliance(self)
        for policy in self:
            if policy.state not in ("published", "review"):
                raise UserError(
                    _("Only Published or Review policy versions can be Archived.")
                )
            values = {
                "state": "archived",
                "is_current": False,
                "archived_at": fields.Datetime.now(),
                "archived_by_name": self.env.user.name,
            }
            if not policy.effective_to:
                values["effective_to"] = max(
                    policy.effective_from,
                    fields.Date.context_today(policy),
                )
            policy._write_action(values)
            if (
                policy.archive_document_version_id
                and policy.archive_document_version_id.state
                not in ("archived", "superseded")
            ):
                policy.archive_document_version_id.action_archive()
        return display_notification(
            _("Policy archived; version, acknowledgement and evidence history were preserved."),
            notification_type="warning",
        )

    def action_open_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Policy Version History — %s") % self.policy_code,
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [
                ("policy_code", "=", self.policy_code),
                ("company_id", "=", self.company_id.id),
            ],
            "context": {"create": False},
        }

    def action_open_acknowledgements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Policy Acknowledgements — %s") % self.display_name,
            "res_model": "onehr.policy.ack",
            "view_mode": "list,pivot,graph,form",
            "domain": [("policy_id", "=", self.id)],
        }

    def action_open_evidence(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Policy Evidence — %s") % self.display_name,
            "res_model": "onehr.policy.evidence",
            "view_mode": "list,pivot,graph,form",
            "domain": [("policy_id", "=", self.id)],
        }

    def action_open_archive_document(self):
        require_pnp_compliance(self)
        self.ensure_one()
        if not self.archive_document_id:
            raise UserError(_("No OneHR Document archive exists yet."))
        return open_record_action(
            name=_("Policy Document Archive"),
            res_model="onehr.document",
            res_id=self.archive_document_id.id,
        )

    def action_open_archive_snapshot(self):
        require_pnp_compliance(self)
        self.ensure_one()
        if not self.archive_document_version_id:
            raise UserError(_("No archived policy snapshot exists yet."))
        return open_record_action(
            name=_("Archived Policy Snapshot"),
            res_model="onehr.document.version",
            res_id=self.archive_document_version_id.id,
        )

    def action_open_related_sops(self):
        self.ensure_one()
        if not self.related_sop_references:
            raise UserError(_("No related OneHR SOP references are configured."))
        if not self.env.registry.get("onehr.sop"):
            raise UserError(
                _("OneHR SOP is not installed. Policy references remain unchanged.")
            )

        codes = [
            code.strip()
            for code in self.related_sop_references.replace(";", ",").split(",")
            if code.strip()
        ]
        sops = self.env["onehr.sop"].search(
            [
                ("code", "in", codes),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Related SOPs"),
            "res_model": "onehr.sop",
            "view_mode": "list,form",
            "domain": [("id", "in", sops.ids)],
        }

    def action_print_policy(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_pnp.action_report_onehr_policy"
        ).report_action(self)

    def action_print_compliance(self):
        require_pnp_compliance(self)
        self.ensure_one()
        return self.env.ref(
            "onehr_pnp.action_report_onehr_policy_compliance"
        ).report_action(self)

    def action_queue_publication_notice(self):
        require_pnp_compliance(self)
        self.ensure_one()
        if self.state not in ("published", "review"):
            raise UserError(_("Publication notices require a Published/Review policy."))
        if not self.publication_template_id:
            raise UserError(_("Configure a publication template first."))

        queued = 0
        for ack in self.ack_ids.filtered(
            lambda item: item.state == "pending" and item.employee_id.work_email
        ):
            self.publication_template_id.send_mail(
                ack.id,
                force_send=False,
            )
            queued += 1
        return display_notification(
            _("%s publication email(s) queued.") % queued
        )

    def _send_ack_reminders(self, *, from_cron=False):
        if not from_cron:
            require_pnp_compliance(self)

        today = fields.Date.context_today(self)
        queued = 0
        todo = self.env.ref("mail.mail_activity_data_todo")

        for policy in self:
            if policy.state not in ("published", "review"):
                continue
            template = policy.reminder_template_id

            for ack in policy.ack_ids.filtered(
                lambda item: item.state == "pending"
            ):
                if ack.last_reminder_at:
                    last_date = fields.Datetime.to_datetime(
                        ack.last_reminder_at
                    ).date()
                else:
                    last_date = (
                        fields.Datetime.to_datetime(policy.published_at).date()
                        if policy.published_at
                        else today
                    )
                if today < last_date + timedelta(
                    days=policy.ack_reminder_days
                ):
                    continue

                if ack.employee_user_id:
                    existing = ack.activity_ids.filtered(
                        lambda activity: (
                            activity.activity_type_id == todo
                            and activity.user_id == ack.employee_user_id
                            and activity.summary in (
                                _("Policy acknowledgement"),
                                _("Policy acknowledgement reminder"),
                            )
                        )
                    )
                    if not existing:
                        ack.activity_schedule(
                            todo.id,
                            user_id=ack.employee_user_id.id,
                            date_deadline=today,
                            summary=_("Policy acknowledgement reminder"),
                            note=_(
                                "Acknowledgement remains pending for %s version %s."
                            )
                            % (policy.policy_code, policy.version_no),
                        )

                if (
                    policy.auto_email_reminders
                    and template
                    and ack.employee_id.work_email
                ):
                    template.send_mail(ack.id, force_send=False)
                    queued += 1

                ack.with_context(
                    onehr_pnp_ack_action=True
                ).write(
                    {
                        "last_reminder_at": fields.Datetime.now(),
                        "reminder_count": ack.reminder_count + 1,
                    }
                )
        return queued

    def action_send_ack_reminders(self):
        queued = self._send_ack_reminders(from_cron=False)
        return display_notification(
            _("%s acknowledgement reminder email(s) queued; activities refreshed.")
            % queued,
            notification_type="info",
        )

    @api.model
    def _cron_policy_governance(self):
        today = fields.Date.context_today(self)
        review_window = today + timedelta(days=30)
        todo = self.env.ref("mail.mail_activity_data_todo")

        policies = self.search(
            [
                ("is_current", "=", True),
                ("state", "in", ["published", "review"]),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        for policy in policies:
            if policy.review_due_date and policy.review_due_date <= review_window:
                users = (
                    policy.compliance_user_ids
                    or policy.owner_user_id
                )
                for user in users:
                    existing = policy.activity_ids.filtered(
                        lambda activity: (
                            activity.activity_type_id == todo
                            and activity.user_id == user
                            and activity.date_deadline == policy.review_due_date
                            and activity.summary == _("Policy periodic review due")
                        )
                    )
                    if not existing:
                        policy.activity_schedule(
                            todo.id,
                            user_id=user.id,
                            date_deadline=policy.review_due_date,
                            summary=_("Policy periodic review due"),
                            note=_(
                                "Review %s version %s."
                            )
                            % (policy.policy_code, policy.version_no),
                        )

            policy._send_ack_reminders(from_cron=True)
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unstarted_draft(self):
        require_pnp_admin(self)
        for policy in self:
            if (
                policy.state not in ("draft", "rejected")
                or policy.ack_ids
                or policy.evidence_ids
                or policy.archive_document_version_id
                or policy.onehr_approval_request_count
            ):
                raise UserError(
                    _(
                        "Only an unsubmitted Draft/Rejected policy with no approval/publication/compliance evidence may be deleted."
                    )
                )

