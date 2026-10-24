
import base64
import csv
import hashlib
import io
import math
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .authority_helpers import (
    notification,
    open_record,
    require_sop_approver,
    require_sop_editor,
)


class OneHRSOPVersion(models.Model):
    _name = "onehr.sop.version"
    _description = "OneHR SOP Version"
    _inherit = ["onehr.mixin.audit"]
    _order = "sop_id, version_no desc"

    _sop_version_uniq = models.Constraint(
        "UNIQUE(sop_id, version_no)",
        "SOP version number must be unique inside one SOP.",
    )

    _ACTION_CONTEXT = "onehr_sop_version_action_write"
    _ACK_CREATION_CONTEXT = "onehr_sop_publish_ack_creation"

    sop_id = fields.Many2one(
        "onehr.sop",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="sop_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=True,
        index=True,
        string="Version Reference",
    )
    version_no = fields.Integer(
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("approved", "Approved"),
            ("published", "Published"),
            ("obsolete", "Obsolete"),
        ],
        required=True,
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    is_current = fields.Boolean(
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    effective_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    effective_to = fields.Date(
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
        index=True,
    )

    purpose = fields.Html(
        string="Purpose",
        tracking=True,
        sanitize=True,
    )
    scope = fields.Html(
        string="Scope",
        tracking=True,
        sanitize=True,
    )
    definitions = fields.Html(
        string="Definitions / Terms",
        tracking=True,
        sanitize=True,
    )
    roles_responsibilities = fields.Html(
        string="Roles & Responsibilities",
        tracking=True,
        sanitize=True,
    )
    procedure_steps = fields.Html(
        string="Procedure / Work Instructions",
        tracking=True,
        sanitize=True,
    )
    controls = fields.Html(
        string="Controls / Quality Checks",
        tracking=True,
        sanitize=True,
    )
    records_evidence = fields.Html(
        string="Required Records / Evidence",
        tracking=True,
        sanitize=True,
    )
    training_requirements = fields.Html(
        string="Training / Competency Requirements",
        tracking=True,
        sanitize=True,
    )
    safety_notes = fields.Html(
        string="Safety / HSE / K3 Requirements",
        tracking=True,
        sanitize=True,
    )
    references = fields.Html(
        string="References / Related Documents",
        tracking=True,
        sanitize=True,
    )

    target_all_employees = fields.Boolean(
        string="All Active Employees in Company",
        default=False,
        tracking=True,
    )
    target_department_ids = fields.Many2many(
        "hr.department",
        "onehr_sop_ver_dept_rel",
        "version_id",
        "department_id",
        string="Target Units / Departments",
        tracking=True,
    )
    target_job_ids = fields.Many2many(
        "hr.job",
        "onehr_sop_ver_job_rel",
        "version_id",
        "job_id",
        string="Target Jobs / Roles",
        tracking=True,
    )
    target_employee_ids = fields.Many2many(
        "hr.employee",
        "onehr_sop_ver_emp_rel",
        "version_id",
        "employee_id",
        string="Specific Employees",
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
        help="Optional exceptions/additions to department and job publication scope.",
    )

    change_summary = fields.Text(
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
        help="Required for version 2 and later.",
    )
    change_reason = fields.Text(
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    reviewer_comments = fields.Html(
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    approval_comments = fields.Html(
        tracking=True,
        groups="onehr_sop.group_onehr_sop_approver",
    )

    submitted_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    submitted_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    approved_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    approved_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    published_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    published_at = fields.Datetime(
        readonly=True,
        copy=False,
        index=True,
    )
    obsolete_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    obsolete_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    content_fingerprint = fields.Char(
        readonly=True,
        copy=False,
        index=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )

    archive_document_version_id = fields.Many2one(
        "onehr.document.version",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="onehr_sop.group_onehr_sop_editor",
        string="Archived Document Version",
    )

    ack_ids = fields.One2many(
        "onehr.sop.ack",
        "version_id",
        string="Acknowledgements",
    )
    ack_count = fields.Integer(
        compute="_compute_ack_metrics",
        store=True,
        string="Audience",
    )
    acknowledged_count = fields.Integer(
        compute="_compute_ack_metrics",
        store=True,
        string="Acknowledged",
    )
    pending_count = fields.Integer(
        compute="_compute_ack_metrics",
        store=True,
        string="Pending",
    )
    ack_rate = fields.Float(
        compute="_compute_ack_metrics",
        store=True,
        string="Acknowledgement %",
    )
    reached_90_at = fields.Datetime(
        compute="_compute_ack_metrics",
        store=True,
        string="90% Reached At",
    )
    days_to_90_ack = fields.Float(
        compute="_compute_ack_metrics",
        store=True,
        string="Days to 90% Ack",
    )
    audience_user_ids = fields.Many2many(
        "res.users",
        "onehr_sop_ver_audience_rel",
        "version_id",
        "user_id",
        compute="_compute_audience_users",
        store=True,
        string="Published Audience Users",
        groups="onehr_sop.group_onehr_sop_editor",
    )

    previous_version_id = fields.Many2one(
        "onehr.sop.version",
        compute="_compute_previous_version",
        store=True,
        readonly=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    completeness_percent = fields.Float(
        compute="_compute_completeness",
        store=True,
        string="Content Completeness %",
    )
    review_overdue = fields.Boolean(
        compute="_compute_review_status",
        store=False,
    )

    export_file = fields.Binary(
        readonly=True,
        copy=False,
        attachment=False,
        groups="onehr_sop.group_onehr_sop_approver",
    )
    export_filename = fields.Char(
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_approver",
    )

    _CONTENT_FIELDS = {
        "effective_from",
        "review_due_date",
        "purpose",
        "scope",
        "definitions",
        "roles_responsibilities",
        "procedure_steps",
        "controls",
        "records_evidence",
        "training_requirements",
        "safety_notes",
        "references",
        "target_all_employees",
        "target_department_ids",
        "target_job_ids",
        "target_employee_ids",
        "change_summary",
        "change_reason",
    }
    _LIFECYCLE_FIELDS = {
        "state",
        "is_current",
        "effective_to",
        "retention_until",
        "submitted_by_id",
        "submitted_at",
        "approved_by_id",
        "approved_at",
        "published_by_id",
        "published_at",
        "obsolete_by_id",
        "obsolete_at",
        "content_fingerprint",
        "archive_document_version_id",
    }

    @api.depends("sop_id.code", "version_no")
    def _compute_name(self):
        for record in self:
            record.name = (
                _("%s / V%s") % (record.sop_id.code, record.version_no)
                if record.sop_id and record.version_no
                else _("SOP Version")
            )

    @api.depends("sop_id.version_ids.version_no", "version_no")
    def _compute_previous_version(self):
        for record in self:
            previous = record.sop_id.version_ids.filtered(
                lambda version: version.version_no < record.version_no
            )
            record.previous_version_id = (
                previous.sorted("version_no")[-1:] if previous else False
            )

    @api.depends(
        "purpose",
        "scope",
        "roles_responsibilities",
        "procedure_steps",
        "controls",
        "records_evidence",
        "training_requirements",
        "safety_notes",
        "references",
        "target_all_employees",
        "target_department_ids",
        "target_job_ids",
        "target_employee_ids",
    )
    def _compute_completeness(self):
        for record in self:
            checks = [
                bool(record.purpose),
                bool(record.scope),
                bool(record.roles_responsibilities),
                bool(record.procedure_steps),
                bool(record.controls),
                bool(record.records_evidence),
                bool(record.references),
                bool(
                    record.target_all_employees
                    or record.target_department_ids
                    or record.target_job_ids
                    or record.target_employee_ids
                ),
            ]
            record.completeness_percent = (
                sum(checks) * 100.0 / len(checks) if checks else 0.0
            )

    @api.depends(
        "ack_ids.state",
        "ack_ids.acknowledged_at",
        "published_at",
    )
    def _compute_ack_metrics(self):
        for record in self:
            acknowledgements = record.ack_ids
            acknowledged = acknowledgements.filtered(
                lambda ack: ack.state == "acknowledged"
            )
            total = len(acknowledgements)
            done = len(acknowledged)
            record.ack_count = total
            record.acknowledged_count = done
            record.pending_count = max(0, total - done)
            record.ack_rate = done * 100.0 / total if total else 0.0
            record.reached_90_at = False
            record.days_to_90_ack = 0.0

            if total and record.published_at and done >= math.ceil(total * 0.90):
                ordered = acknowledged.filtered("acknowledged_at").sorted(
                    key=lambda ack: ack.acknowledged_at
                )
                threshold_index = math.ceil(total * 0.90) - 1
                if len(ordered) > threshold_index:
                    reached_at = ordered[threshold_index].acknowledged_at
                    record.reached_90_at = reached_at
                    elapsed = reached_at - record.published_at
                    record.days_to_90_ack = elapsed.total_seconds() / 86400.0

    @api.depends("ack_ids.employee_user_id")
    def _compute_audience_users(self):
        for record in self:
            record.audience_user_ids = [
                Command.set(record.ack_ids.mapped("employee_user_id").ids)
            ]

    @api.depends("review_due_date", "state")
    def _compute_review_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.review_overdue = bool(
                record.state == "published"
                and record.review_due_date
                and record.review_due_date < today
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_sop_editor(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            sop = self.env["onehr.sop"].browse(vals.get("sop_id")).exists()
            if not sop:
                raise ValidationError(_("A valid SOP master is required."))

            in_flight = sop.version_ids.filtered(
                lambda version: version.state in ("draft", "review", "approved")
            )
            if in_flight:
                raise UserError(
                    _("Only one Draft/Review/Approved version is allowed per SOP.")
                )

            if not vals.get("version_no"):
                vals["version_no"] = max(sop.version_ids.mapped("version_no") or [0]) + 1

            effective_from = fields.Date.to_date(
                vals.get("effective_from") or fields.Date.context_today(self)
            )
            vals["effective_from"] = effective_from
            vals.setdefault(
                "review_due_date",
                sop._default_review_due_date(effective_from),
            )
            vals["state"] = "draft"
            vals["is_current"] = False
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)

        require_sop_editor(self)
        values = dict(vals)

        if self._LIFECYCLE_FIELDS.intersection(values):
            raise AccessError(
                _("SOP lifecycle evidence can change only through governed actions.")
            )

        for record in self:
            if (
                record.state in ("review", "approved", "published", "obsolete")
                and self._CONTENT_FIELDS.intersection(values)
            ):
                raise AccessError(
                    _(
                        "Submitted/approved/published SOP content and audience are locked. "
                        "Return an in-flight version to Draft or create a successor."
                    )
                )
        return super().write(values)

    @api.constrains("effective_from", "effective_to", "review_due_date")
    def _check_dates(self):
        for record in self:
            if record.effective_to and record.effective_to < record.effective_from:
                raise ValidationError(
                    _("Effective To cannot be earlier than Effective From.")
                )
            if record.review_due_date < record.effective_from:
                raise ValidationError(
                    _("Review Due Date cannot be earlier than Effective From.")
                )

    @api.constrains(
        "target_all_employees",
        "target_department_ids",
        "target_job_ids",
        "target_employee_ids",
        "company_id",
    )
    def _check_audience_company_scope(self):
        for record in self:
            if record.target_all_employees and (
                record.target_department_ids
                or record.target_job_ids
                or record.target_employee_ids
            ):
                raise ValidationError(
                    _(
                        "When All Active Employees is selected, remove specific department, job and employee targets."
                    )
                )

            wrong_departments = record.target_department_ids.filtered(
                lambda department: department.company_id
                and department.company_id != record.company_id
            )
            wrong_jobs = record.target_job_ids.filtered(
                lambda job: job.company_id and job.company_id != record.company_id
            )
            wrong_employees = record.target_employee_ids.filtered(
                lambda employee: employee.company_id != record.company_id
            )
            if wrong_departments or wrong_jobs or wrong_employees:
                raise ValidationError(
                    _("All publication targets must belong to the SOP company.")
                )

    @api.constrains("is_current", "state", "sop_id")
    def _check_single_current_version(self):
        for record in self.filtered("is_current"):
            if record.state != "published":
                raise ValidationError(
                    _("Only a Published SOP version can be current.")
                )
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("sop_id", "=", record.sop_id.id),
                    ("is_current", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Only one current Published version is allowed per SOP.")
                )

    def _write_lifecycle(self, values):
        return self.with_context(
            **{self._ACTION_CONTEXT: True}
        ).write(values)

    def _copy_content_values(self):
        self.ensure_one()
        scalar_fields = [
            "purpose",
            "scope",
            "definitions",
            "roles_responsibilities",
            "procedure_steps",
            "controls",
            "records_evidence",
            "training_requirements",
            "safety_notes",
            "references",
            "target_all_employees",
        ]
        values = {field_name: self[field_name] for field_name in scalar_fields}
        values.update(
            {
                "target_department_ids": [
                    Command.set(self.target_department_ids.ids)
                ],
                "target_job_ids": [Command.set(self.target_job_ids.ids)],
                "target_employee_ids": [
                    Command.set(self.target_employee_ids.ids)
                ],
            }
        )
        return values

    def _resolve_audience_employees(self):
        self.ensure_one()
        Employee = self.env["hr.employee"]
        base_domain = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ]
        if self.target_all_employees:
            return Employee.search(base_domain)

        employees = self.target_employee_ids.filtered("active")
        if self.target_department_ids:
            employees |= Employee.search(
                base_domain
                + [("department_id", "in", self.target_department_ids.ids)]
            )
        if self.target_job_ids:
            employees |= Employee.search(
                base_domain
                + [("job_id", "in", self.target_job_ids.ids)]
            )
        return employees.filtered(
            lambda employee: employee.company_id == self.company_id
        )

    def action_preview_audience(self):
        require_sop_editor(self)
        self.ensure_one()
        employees = self._resolve_audience_employees()
        linked = employees.filtered("user_id")
        return notification(
            _(
                "%s active employee(s) targeted; %s have a linked OneHR user and can acknowledge online."
            )
            % (len(employees), len(linked)),
            notification_type="info",
        )

    def _required_for_review(self):
        self.ensure_one()
        missing = []
        requirements = [
            ("purpose", _("Purpose")),
            ("scope", _("Scope")),
            ("roles_responsibilities", _("Roles & Responsibilities")),
            ("procedure_steps", _("Procedure / Work Instructions")),
            ("controls", _("Controls / Quality Checks")),
            ("records_evidence", _("Required Records / Evidence")),
            ("references", _("References / Related Documents")),
        ]
        for field_name, label in requirements:
            if not self[field_name]:
                missing.append(label)
        if not (
            self.target_all_employees
            or self.target_department_ids
            or self.target_job_ids
            or self.target_employee_ids
        ):
            missing.append(_("Publication Audience"))
        if self.version_no > 1 and not self.change_summary:
            missing.append(_("Change Summary"))
        return missing

    def _fingerprint_payload(self):
        self.ensure_one()
        values = [
            self.sop_id.code or "",
            str(self.version_no),
            str(self.effective_from or ""),
            str(self.review_due_date or ""),
            self.purpose or "",
            self.scope or "",
            self.definitions or "",
            self.roles_responsibilities or "",
            self.procedure_steps or "",
            self.controls or "",
            self.records_evidence or "",
            self.training_requirements or "",
            self.safety_notes or "",
            self.references or "",
            str(bool(self.target_all_employees)),
            ",".join(map(str, sorted(self.target_department_ids.ids))),
            ",".join(map(str, sorted(self.target_job_ids.ids))),
            ",".join(map(str, sorted(self.target_employee_ids.ids))),
            self.change_summary or "",
            self.change_reason or "",
        ]
        return "\n---\n".join(values).encode("utf-8")

    def _calculate_fingerprint(self):
        self.ensure_one()
        return hashlib.sha256(self._fingerprint_payload()).hexdigest()

    def _schedule_reviewer_activities(self):
        todo = self.env.ref("mail.mail_activity_data_todo")
        for record in self:
            users = record.sop_id.reviewer_user_ids or record.sop_id.approver_user_ids
            for user in users:
                existing = record.activity_ids.filtered(
                    lambda activity: (
                        activity.activity_type_id == todo
                        and activity.user_id == user
                        and activity.summary == _("Review SOP version")
                    )
                )
                if not existing:
                    record.activity_schedule(
                        todo.id,
                        user_id=user.id,
                        date_deadline=record.review_due_date,
                        summary=_("Review SOP version"),
                        note=_(
                            "Review %s version %s before approval."
                        ) % (record.sop_id.code, record.version_no),
                    )

    def action_submit_review(self):
        require_sop_editor(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft SOP versions can enter Review."))
            missing = record._required_for_review()
            if missing:
                raise UserError(
                    _("Review blocked. Complete: %s") % ", ".join(missing)
                )
            audience = record._resolve_audience_employees()
            if not audience:
                raise UserError(
                    _("The selected publication scope resolves to no active employees.")
                )
            record._write_lifecycle(
                {
                    "state": "review",
                    "submitted_by_id": self.env.user.id,
                    "submitted_at": fields.Datetime.now(),
                    "approved_by_id": False,
                    "approved_at": False,
                    "content_fingerprint": False,
                }
            )
            record._schedule_reviewer_activities()
        return notification(_("SOP submitted for Review."))

    def action_return_draft(self):
        require_sop_approver(self)
        self.mapped("sop_id")._require_assigned_approver()
        for record in self:
            if record.state not in ("review", "approved"):
                raise UserError(
                    _("Only Review or Approved SOP versions can return to Draft.")
                )
            if record.ack_ids:
                raise UserError(
                    _("A version with generated acknowledgement evidence cannot return to Draft.")
                )
            record._write_lifecycle(
                {
                    "state": "draft",
                    "approved_by_id": False,
                    "approved_at": False,
                    "content_fingerprint": False,
                }
            )
        return notification(
            _("SOP returned to Draft."),
            notification_type="warning",
        )

    def action_approve(self):
        require_sop_approver(self)
        self.mapped("sop_id")._require_assigned_approver()
        for record in self:
            if record.state != "review":
                raise UserError(_("Only Review SOP versions can be approved."))
            missing = record._required_for_review()
            if missing:
                raise UserError(
                    _("Approval blocked. Complete: %s") % ", ".join(missing)
                )
            audience = record._resolve_audience_employees()
            if not audience:
                raise UserError(_("Approval requires at least one active audience employee."))
            record._write_lifecycle(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_at": fields.Datetime.now(),
                    "content_fingerprint": record._calculate_fingerprint(),
                }
            )
        return notification(_("SOP approved."))

    def _archive_html(self):
        self.ensure_one()

        def section(title, body):
            return (
                f"<h3>{title}</h3>{body}"
                if body
                else f"<h3>{title}</h3><p>Not specified.</p>"
            )

        audience = []
        if self.target_all_employees:
            audience.append("All active employees in company")
        if self.target_department_ids:
            audience.append(
                "Departments: " + ", ".join(self.target_department_ids.mapped("name"))
            )
        if self.target_job_ids:
            audience.append("Jobs/Roles: " + ", ".join(self.target_job_ids.mapped("name")))
        if self.target_employee_ids:
            audience.append(
                "Specific employees: " + ", ".join(self.target_employee_ids.mapped("name"))
            )

        return "".join(
            [
                f"<h2>{self.sop_id.code} — {self.sop_id.name}</h2>",
                f"<p><strong>SOP Version:</strong> {self.version_no}</p>",
                f"<p><strong>Effective:</strong> {self.effective_from}</p>",
                f"<p><strong>Review Due:</strong> {self.review_due_date}</p>",
                f"<p><strong>Publication Scope:</strong> {'; '.join(audience)}</p>",
                section("Purpose", self.purpose),
                section("Scope", self.scope),
                section("Definitions / Terms", self.definitions),
                section("Roles & Responsibilities", self.roles_responsibilities),
                section("Procedure / Work Instructions", self.procedure_steps),
                section("Controls / Quality Checks", self.controls),
                section("Required Records / Evidence", self.records_evidence),
                section("Training / Competency Requirements", self.training_requirements),
                section("Safety / HSE / K3 Requirements", self.safety_notes),
                section("References / Related Documents", self.references),
            ]
        )

    def _ensure_document_archive(self):
        self.ensure_one()
        sop = self.sop_id
        if not sop.document_category_id:
            raise UserError(
                _(
                    "Configure an Archive Document Category on the SOP master before publication."
                )
            )

        category = sop.document_category_id
        if category.sensitivity == "restricted":
            raise UserError(
                _(
                    "Use an Internal or Confidential Document category for SOP archives. "
                    "Restricted categories require separate restricted-document authority."
                )
            )

        document = sop.archive_document_id
        if not document:
            source_model = self.env["ir.model"].search(
                [("model", "=", "onehr.sop")],
                limit=1,
            )
            if not source_model:
                raise UserError(_("The SOP model registry entry could not be resolved."))

            document = self.env["onehr.document"].create(
                {
                    "name": f"{sop.code} — {sop.name}",
                    "category_id": category.id,
                    "company_id": sop.company_id.id,
                    "responsible_user_id": self.env.user.id,
                    "source_model_id": source_model.id,
                    "source_res_id": sop.id,
                    "valid_from": self.effective_from,
                    "keywords": f"SOP, {sop.code}",
                }
            )
            sop.write({"archive_document_id": document.id})

        previous_archive = self.previous_version_id.archive_document_version_id
        archive_version = self.env["onehr.document.version"].create(
            {
                "document_id": document.id,
                "effective_from": self.effective_from,
                "rendered_subject": f"{sop.code} — {sop.name} / V{self.version_no}",
                "rendered_content_html": self._archive_html(),
            }
        )
        archive_version.action_issue()

        if previous_archive and previous_archive.state not in ("archived", "superseded"):
            previous_archive.action_archive()

        return archive_version

    def _generate_acknowledgements(self):
        self.ensure_one()
        if self.ack_ids:
            raise UserError(
                _("Acknowledgement evidence already exists for this SOP version.")
            )
        employees = self._resolve_audience_employees()
        if not employees:
            raise UserError(_("Publication scope contains no active employees."))

        values = [
            {
                "version_id": self.id,
                "employee_id": employee.id,
            }
            for employee in employees
        ]
        return self.env["onehr.sop.ack"].with_context(
            **{self._ACK_CREATION_CONTEXT: True}
        ).create(values)

    def action_publish(self):
        require_sop_approver(self)
        self.mapped("sop_id")._require_assigned_approver()

        for record in self:
            if record.state != "approved":
                raise UserError(_("Only Approved SOP versions can be published."))

            fingerprint = record._calculate_fingerprint()
            if (
                record.content_fingerprint
                and record.content_fingerprint != fingerprint
            ):
                raise UserError(
                    _("SOP content or audience changed after approval; return to Draft and re-approve.")
                )

            archive_version = record._ensure_document_archive()
            record._generate_acknowledgements()

            previous_current = record.sop_id.version_ids.filtered(
                lambda version: version.is_current and version.id != record.id
            )
            for previous in previous_current:
                previous_values = {
                    "state": "obsolete",
                    "is_current": False,
                    "obsolete_by_id": self.env.user.id,
                    "obsolete_at": fields.Datetime.now(),
                }
                if previous.effective_from:
                    if record.effective_from > previous.effective_from:
                        previous_values["effective_to"] = (
                            record.effective_from - timedelta(days=1)
                        )
                    elif record.effective_from == previous.effective_from:
                        previous_values["effective_to"] = previous.effective_from
                previous._write_lifecycle(previous_values)

            retention_until = record.effective_from + relativedelta(
                years=record.sop_id.retention_years
            )
            record._write_lifecycle(
                {
                    "state": "published",
                    "is_current": True,
                    "retention_until": retention_until,
                    "published_by_id": self.env.user.id,
                    "published_at": fields.Datetime.now(),
                    "content_fingerprint": fingerprint,
                    "archive_document_version_id": archive_version.id,
                }
            )
            record._schedule_publication_activities()

        return notification(_("SOP published and acknowledgement evidence generated."))

    def action_mark_obsolete(self):
        require_sop_approver(self)
        self.mapped("sop_id")._require_assigned_approver()
        today = fields.Date.context_today(self)

        for record in self:
            if record.state != "published":
                raise UserError(_("Only Published SOP versions can become Obsolete."))
            values = {
                "state": "obsolete",
                "is_current": False,
                "obsolete_by_id": self.env.user.id,
                "obsolete_at": fields.Datetime.now(),
            }
            if not record.effective_to:
                values["effective_to"] = max(record.effective_from, today)
            record._write_lifecycle(values)
            if (
                record.archive_document_version_id
                and record.archive_document_version_id.state
                not in ("archived", "superseded")
            ):
                record.archive_document_version_id.action_archive()

        return notification(
            _("SOP version marked Obsolete; history and acknowledgements were retained."),
            notification_type="warning",
        )

    def _schedule_publication_activities(self):
        todo = self.env.ref("mail.mail_activity_data_todo")
        for record in self:
            deadline = fields.Date.context_today(record) + timedelta(
                days=record.sop_id.ack_reminder_days
            )
            for ack in record.ack_ids.filtered(
                lambda item: item.state == "pending" and item.employee_user_id
            ):
                existing = ack.activity_ids.filtered(
                    lambda activity: (
                        activity.activity_type_id == todo
                        and activity.user_id == ack.employee_user_id
                        and activity.summary == _("Read & Agree — SOP")
                    )
                )
                if not existing:
                    ack.activity_schedule(
                        todo.id,
                        user_id=ack.employee_user_id.id,
                        date_deadline=deadline,
                        summary=_("Read & Agree — SOP"),
                        note=_(
                            "Read and acknowledge %s version %s."
                        ) % (record.sop_id.code, record.version_no),
                    )

    def action_send_publication_notice(self):
        require_sop_approver(self)
        for record in self:
            if record.state != "published":
                raise UserError(_("Publication notices require a Published SOP."))
            template = record.sop_id.publication_template_id
            if not template:
                raise UserError(_("Configure a publication notification template first."))
            queued = 0
            for ack in record.ack_ids.filtered(
                lambda item: item.state == "pending" and item.employee_id.work_email
            ):
                template.send_mail(ack.id, force_send=False)
                queued += 1
        return notification(_("%s publication email(s) queued.") % queued)

    def _send_ack_reminders(self, *, from_cron=False):
        if not from_cron:
            require_sop_approver(self)
        elif not self.env.is_superuser() and not self.env.user.has_group(
            "onehr_sop.group_onehr_sop_approver"
        ):
            raise AccessError(_("SOP reminder scheduler requires approved authority."))

        today = fields.Date.context_today(self)
        todo = self.env.ref("mail.mail_activity_data_todo")
        queued = 0
        for record in self:
            if record.state != "published" or not record.published_at:
                continue

            publish_date = fields.Datetime.to_datetime(record.published_at).date()
            if today < publish_date + timedelta(days=record.sop_id.ack_reminder_days):
                continue

            template = record.sop_id.reminder_template_id
            for ack in record.ack_ids.filtered(
                lambda item: item.state == "pending"
            ):
                last_date = (
                    fields.Datetime.to_datetime(ack.last_reminder_at).date()
                    if ack.last_reminder_at
                    else publish_date
                )
                next_due = last_date + timedelta(
                    days=record.sop_id.ack_reminder_days
                )
                if today < next_due:
                    continue

                if ack.employee_user_id:
                    duplicate = ack.activity_ids.filtered(
                        lambda activity: (
                            activity.activity_type_id == todo
                            and activity.user_id == ack.employee_user_id
                            and activity.summary in (
                                _("Read & Agree — SOP"),
                                _("SOP acknowledgement reminder"),
                            )
                        )
                    )
                    if not duplicate:
                        ack.activity_schedule(
                            todo.id,
                            user_id=ack.employee_user_id.id,
                            date_deadline=today,
                            summary=_("SOP acknowledgement reminder"),
                            note=_(
                                "Acknowledgement remains pending for %s version %s."
                            ) % (record.sop_id.code, record.version_no),
                        )

                if (
                    record.sop_id.auto_email_reminders
                    and template
                    and ack.employee_id.work_email
                ):
                    template.send_mail(ack.id, force_send=False)
                    queued += 1

                ack.with_context(
                    **{ack._ACTION_CONTEXT: True}
                ).write(
                    {
                        "last_reminder_at": fields.Datetime.now(),
                        "reminder_count": ack.reminder_count + 1,
                    }
                )
        return queued

    def action_send_ack_reminders(self):
        queued = self._send_ack_reminders(from_cron=False)
        return notification(
            _("%s acknowledgement reminder email(s) queued; activities were refreshed.") % queued,
            notification_type="info",
        )

    def action_export_ack_csv(self):
        require_sop_approver(self)
        self.ensure_one()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "SOP Reference",
                "SOP Title",
                "Version",
                "Employee Number",
                "Employee Name",
                "Department",
                "Job",
                "Status",
                "Published At",
                "Acknowledged At",
                "Acknowledged By",
                "Source",
            ]
        )
        for ack in self.ack_ids.sorted(
            key=lambda item: (
                item.department_name or "",
                item.employee_name or "",
            )
        ):
            writer.writerow(
                [
                    self.sop_id.code,
                    self.sop_id.name,
                    self.version_no,
                    ack.employee_number or "",
                    ack.employee_name or "",
                    ack.department_name or "",
                    ack.job_name or "",
                    ack.state,
                    self.published_at or "",
                    ack.acknowledged_at or "",
                    ack.acknowledged_by_name or "",
                    ack.acknowledgement_source or "",
                ]
            )

        encoded = base64.b64encode(buffer.getvalue().encode("utf-8-sig"))
        filename = f"{self.sop_id.code.replace('/', '_')}_V{self.version_no}_ack.csv"
        super(OneHRSOPVersion, self).write(
            {
                "export_file": encoded,
                "export_filename": filename,
            }
        )
        return notification(_("Acknowledgement audit CSV prepared."))

    def _own_acknowledgement(self):
        self.ensure_one()
        return self.ack_ids.filtered(
            lambda ack: ack.employee_user_id == self.env.user
        )[:1]

    def action_open_my_acknowledgement(self):
        self.ensure_one()
        ack = self._own_acknowledgement()
        if not ack:
            raise UserError(
                _("No acknowledgement assignment exists for your user on this SOP version.")
            )
        return open_record(
            name=_("My SOP Acknowledgement"),
            res_model="onehr.sop.ack",
            res_id=ack.id,
        )

    def action_acknowledge_my_sop(self):
        self.ensure_one()
        ack = self._own_acknowledgement()
        if not ack:
            raise AccessError(
                _("You are not in the acknowledgement audience for this SOP version.")
            )
        return ack.action_acknowledge()

    def action_open_version(self):
        self.ensure_one()
        return open_record(
            name=_("SOP Version"),
            res_model="onehr.sop.version",
            res_id=self.id,
        )

    def action_open_sop(self):
        self.ensure_one()
        return open_record(
            name=_("SOP"),
            res_model="onehr.sop",
            res_id=self.sop_id.id,
        )

    def action_open_previous_version(self):
        require_sop_editor(self)
        self.ensure_one()
        if not self.previous_version_id:
            raise UserError(_("This is the first SOP version."))
        return open_record(
            name=_("Previous SOP Version"),
            res_model="onehr.sop.version",
            res_id=self.previous_version_id.id,
        )

    def action_open_acknowledgements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Acknowledgements — %s") % self.display_name,
            "res_model": "onehr.sop.ack",
            "view_mode": "list,pivot,graph,form",
            "domain": [("version_id", "=", self.id)],
        }

    def action_open_archive_document(self):
        require_sop_editor(self)
        self.ensure_one()
        if not self.archive_document_version_id:
            raise UserError(_("This SOP version has no archived Document snapshot."))
        return open_record(
            name=_("Archived SOP Snapshot"),
            res_model="onehr.document.version",
            res_id=self.archive_document_version_id.id,
        )

    def action_print_sop(self):
        self.ensure_one()
        return self.env.ref("onehr_sop.action_report_sop_document").report_action(self)

    def action_print_compliance(self):
        require_sop_approver(self)
        self.ensure_one()
        return self.env.ref("onehr_sop.action_report_sop_compliance").report_action(self)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unsubmitted_draft(self):
        require_sop_editor(self)
        for record in self:
            if record.state != "draft" or record.ack_ids:
                raise UserError(
                    _("Only an unsubmitted Draft SOP version without acknowledgement evidence may be deleted.")
                )

