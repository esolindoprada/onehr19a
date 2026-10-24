
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .authority_helpers import (
    display_notification,
    is_jd_admin,
    require_jd_admin,
    require_jd_editor,
)


class OneHRJobDescription(models.Model):
    _name = "onehr.jd"
    _description = "OneHR Job Description"
    _inherit = ["onehr.mixin.audit"]
    _order = "is_template desc, code, name"

    _jd_code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Job Description code must be unique per company.",
    )
    _jd_position_company_uniq = models.Constraint(
        "UNIQUE(position_id, company_id)",
        "A position can have only one Job Description master per company.",
    )

    _GOVERNANCE_CONTEXT = "onehr_jd_governance_write"

    name = fields.Char(
        string="Job Description Title",
        required=True,
        translate=True,
        tracking=True,
        index=True,
    )
    code = fields.Char(
        string="JD Reference",
        required=True,
        default="New",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    is_template = fields.Boolean(
        string="Job-Family Template",
        default=False,
        tracking=True,
        index=True,
        help="Templates are reusable JD definitions for a job family and are not mapped "
             "directly to one position.",
    )

    position_id = fields.Many2one(
        "onehr.position",
        string="Position",
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    position_code = fields.Char(
        related="position_id.code",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    position_name = fields.Char(
        related="position_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="position_id.job_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    job_name = fields.Char(
        related="position_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="position_id.department_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    department_name = fields.Char(
        related="position_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    grade_id = fields.Many2one(
        "onehr.grade",
        related="position_id.grade_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    grade_name = fields.Char(
        related="position_id.grade_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    job_family_id = fields.Many2one(
        "onehr.job.family",
        string="Job Family",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Required for job-family templates. Position JDs inherit the family "
             "from the position's canonical hr.job when available.",
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    job_family_name = fields.Char(
        related="job_family_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    reviewer_user_ids = fields.Many2many(
        "res.users",
        "onehr_jd_reviewer_rel",
        "jd_id",
        "user_id",
        string="Reviewers",
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
        help="Optional review routing. The security group remains authoritative.",
    )
    approver_user_ids = fields.Many2many(
        "res.users",
        "onehr_jd_approver_rel",
        "jd_id",
        "user_id",
        string="Approvers",
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
        help="Optional approval matrix for this JD/template. When populated, "
             "approval/publication is restricted to assigned approvers or JD Admin.",
    )

    version_ids = fields.One2many(
        "onehr.jd.version",
        "jd_id",
        string="Versions",
    )
    latest_version_id = fields.Many2one(
        "onehr.jd.version",
        compute="_compute_version_metrics",
        store=True,
        readonly=True,
        string="Latest Version",
    )
    current_version_id = fields.Many2one(
        "onehr.jd.version",
        compute="_compute_version_metrics",
        store=True,
        readonly=True,
        string="Current Published Version",
    )
    version_count = fields.Integer(
        compute="_compute_version_metrics",
        store=True,
    )
    published_version_count = fields.Integer(
        compute="_compute_version_metrics",
        store=True,
    )
    lifecycle_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("approved", "Approved"),
            ("published", "Published"),
        ],
        compute="_compute_version_metrics",
        store=True,
        string="JD Status",
        index=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    coverage_state = fields.Selection(
        [
            ("unpublished", "Unpublished"),
            ("covered", "Published / Covered"),
        ],
        compute="_compute_version_metrics",
        store=True,
        index=True,
    )
    coverage_score = fields.Float(
        compute="_compute_version_metrics",
        store=True,
        string="Coverage %",
    )
    published_at = fields.Datetime(
        compute="_compute_version_metrics",
        store=True,
        readonly=True,
    )
    review_due_date = fields.Date(
        compute="_compute_version_metrics",
        store=True,
        readonly=True,
        index=True,
    )
    version_age_days = fields.Integer(
        readonly=True,
        string="Current Version Age (Days)",
        help="Daily governance metric refreshed by the JD scheduler.",
    )
    review_overdue = fields.Boolean(
        readonly=True,
        index=True,
        help="Daily governance flag maintained from the current published version.",
    )
    notes = fields.Html(
        string="Governance Notes",
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_jd_editor(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code", "New") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "onehr.jd"
                ) or "New"

            position_id = vals.get("position_id")
            if position_id:
                position = self.env["onehr.position"].browse(position_id)
                if position.job_id.onehr_job_family_id:
                    vals.setdefault(
                        "job_family_id",
                        position.job_id.onehr_job_family_id.id,
                    )
            prepared.append(vals)

        records = super().create(prepared)
        records._refresh_governance_metrics()
        return records

    def write(self, vals):
        if self.env.context.get(self._GOVERNANCE_CONTEXT):
            return super().write(vals)

        require_jd_editor(self)

        identity_fields = {
            "company_id",
            "is_template",
            "position_id",
            "job_family_id",
        }
        for record in self:
            if (
                record.current_version_id
                and identity_fields.intersection(vals)
            ):
                raise AccessError(
                    _(
                        "Published JD identity is frozen. Create a replacement JD "
                        "under controlled governance instead of rewriting history."
                    )
                )

        vals = dict(vals)
        if vals.get("position_id"):
            position = self.env["onehr.position"].browse(vals["position_id"])
            if position.job_id.onehr_job_family_id:
                vals["job_family_id"] = position.job_id.onehr_job_family_id.id
        return super().write(vals)

    @api.depends(
        "version_ids.version_no",
        "version_ids.state",
        "version_ids.is_current",
        "version_ids.published_at",
        "version_ids.review_due_date",
    )
    def _compute_version_metrics(self):
        for record in self:
            versions = record.version_ids
            latest = versions.sorted(
                key=lambda version: (version.version_no, version.create_date or fields.Datetime.now())
            )[-1:] if versions else versions
            current = versions.filtered(
                lambda version: version.state == "published" and version.is_current
            )[:1]

            record.latest_version_id = latest
            record.current_version_id = current
            record.version_count = len(versions)
            record.published_version_count = len(
                versions.filtered(lambda version: version.state == "published")
            )
            record.lifecycle_state = (
                latest.state if latest else "draft"
            )
            record.coverage_state = "covered" if current else "unpublished"
            record.coverage_score = 100.0 if current else 0.0
            record.published_at = current.published_at if current else False
            record.review_due_date = current.review_due_date if current else False

    @api.constrains(
        "is_template",
        "position_id",
        "job_family_id",
        "company_id",
        "active",
    )
    def _check_identity_contract(self):
        for record in self:
            if record.is_template:
                if record.position_id:
                    raise ValidationError(
                        _("A job-family JD template cannot be mapped to a position.")
                    )
                if not record.job_family_id:
                    raise ValidationError(
                        _("A job-family JD template requires a Job Family.")
                    )
                duplicate_template = self.search(
                    [
                        ("id", "!=", record.id),
                        ("company_id", "=", record.company_id.id),
                        ("is_template", "=", True),
                        ("job_family_id", "=", record.job_family_id.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if duplicate_template:
                    raise ValidationError(
                        _("Only one active JD template is allowed per Job Family and company.")
                    )
            elif not record.position_id:
                raise ValidationError(
                    _("A non-template Job Description requires a Position.")
                )

            if (
                record.position_id
                and record.position_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _("Position and Job Description must belong to the same company.")
                )

            if (
                record.job_family_id
                and record.job_family_id.company_id
                and record.job_family_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _("Job Family and Job Description must belong to the same company.")
                )

            position_family = (
                record.position_id.job_id.onehr_job_family_id
                if record.position_id
                else False
            )
            if (
                position_family
                and record.job_family_id
                and record.job_family_id != position_family
            ):
                raise ValidationError(
                    _("Job Family must match the canonical Position / Job mapping.")
                )

    @api.onchange("position_id")
    def _onchange_position_id(self):
        for record in self:
            if (
                record.position_id
                and record.position_id.job_id.onehr_job_family_id
            ):
                record.job_family_id = record.position_id.job_id.onehr_job_family_id

    def _refresh_governance_metrics(self):
        today = fields.Date.context_today(self)
        for record in self:
            current = record.current_version_id
            age_days = 0
            overdue = False
            if current and current.published_at:
                published_date = fields.Datetime.to_datetime(
                    current.published_at
                ).date()
                age_days = max(0, (today - published_date).days)
            if current and current.review_due_date:
                overdue = current.review_due_date < today

            record.with_context(
                **{self._GOVERNANCE_CONTEXT: True}
            ).write(
                {
                    "version_age_days": age_days,
                    "review_overdue": overdue,
                }
            )
        return True

    def _require_assigned_approver(self):
        for record in self:
            if (
                record.approver_user_ids
                and self.env.user not in record.approver_user_ids
                and not is_jd_admin(self.env)
            ):
                raise AccessError(
                    _("You are not assigned as an approver for %s.") % record.display_name
                )

    def action_create_new_version(self):
        require_jd_editor(self)
        self.ensure_one()

        in_flight = self.version_ids.filtered(
            lambda version: version.state in ("draft", "review", "approved")
        )
        if in_flight:
            return {
                "type": "ir.actions.act_window",
                "name": _("Open In-Flight JD Version"),
                "res_model": "onehr.jd.version",
                "res_id": in_flight.sorted("version_no")[-1].id,
                "view_mode": "form",
            }

        previous = self.current_version_id or self.latest_version_id
        values = {
            "jd_id": self.id,
            "effective_from": fields.Date.context_today(self),
            "change_reason": _("Periodic JD review"),
        }
        if previous:
            values.update(previous._copy_content_values())
            values["change_summary"] = _(
                "New version created from %s for controlled review."
            ) % previous.display_name

        version = self.env["onehr.jd.version"].create(values)
        return {
            "type": "ir.actions.act_window",
            "name": _("Job Description Version"),
            "res_model": "onehr.jd.version",
            "res_id": version.id,
            "view_mode": "form",
        }

    def action_generate_position_jds(self):
        require_jd_editor(self)
        self.ensure_one()
        if not self.is_template:
            raise UserError(_("This action is available only on a JD template."))
        source = self.current_version_id
        if not source:
            raise UserError(
                _("Publish the template before generating position Job Descriptions.")
            )

        positions = self.env["onehr.position"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
                ("job_id.onehr_job_family_id", "=", self.job_family_id.id),
                ("status", "not in", ("closed",)),
            ]
        )
        created = self.browse()
        for position in positions:
            existing = self.search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("position_id", "=", position.id),
                ],
                limit=1,
            )
            if existing:
                continue

            jd = self.create(
                {
                    "name": position.name,
                    "company_id": self.company_id.id,
                    "position_id": position.id,
                    "job_family_id": self.job_family_id.id,
                    "reviewer_user_ids": [
                        Command.set(self.reviewer_user_ids.ids)
                    ],
                    "approver_user_ids": [
                        Command.set(self.approver_user_ids.ids)
                    ],
                }
            )
            version_values = {
                "jd_id": jd.id,
                "effective_from": fields.Date.context_today(self),
                "change_summary": _(
                    "Initial draft generated from job-family template %s."
                ) % self.code,
                "change_reason": _("Template-based JD creation"),
            }
            version_values.update(source._copy_content_values())
            self.env["onehr.jd.version"].create(version_values)
            created |= jd

        return display_notification(
            _("%s position Job Description(s) generated.") % len(created)
        )

    def action_sync_from_job_family_template(self):
        require_jd_editor(self)
        self.ensure_one()
        if self.is_template:
            raise UserError(_("Templates cannot synchronize from another template."))
        if not self.job_family_id:
            raise UserError(_("The Job Description has no Job Family mapping."))
        if self.version_ids.filtered(
            lambda version: version.state in ("draft", "review", "approved")
        ):
            raise UserError(
                _("Finish the current in-flight version before synchronizing a template.")
            )

        template = self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("is_template", "=", True),
                ("job_family_id", "=", self.job_family_id.id),
                ("active", "=", True),
                ("current_version_id", "!=", False),
            ],
            limit=1,
        )
        if not template:
            raise UserError(
                _("No active published JD template exists for this Job Family.")
            )

        source = template.current_version_id
        values = {
            "jd_id": self.id,
            "effective_from": fields.Date.context_today(self),
            "change_summary": _(
                "Draft synchronized from Job Family template %s."
            ) % template.code,
            "change_reason": _("Job-family template synchronization"),
        }
        values.update(source._copy_content_values())
        version = self.env["onehr.jd.version"].create(values)
        return {
            "type": "ir.actions.act_window",
            "name": _("Synchronized JD Version"),
            "res_model": "onehr.jd.version",
            "res_id": version.id,
            "view_mode": "form",
        }

    def action_open_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("JD Versions — %s") % self.display_name,
            "res_model": "onehr.jd.version",
            "view_mode": "list,form,calendar,pivot,graph",
            "domain": [("jd_id", "=", self.id)],
            "context": {"default_jd_id": self.id},
        }

    def action_open_current_version(self):
        self.ensure_one()
        if not self.current_version_id:
            raise UserError(_("This Job Description has no published current version."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Current Job Description"),
            "res_model": "onehr.jd.version",
            "res_id": self.current_version_id.id,
            "view_mode": "form",
        }

    def action_open_position(self):
        self.ensure_one()
        if not self.position_id:
            raise UserError(_("A template is not mapped to a Position."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Position"),
            "res_model": "onehr.position",
            "res_id": self.position_id.id,
            "view_mode": "form",
        }

    def action_print_current_jd(self):
        self.ensure_one()
        if not self.current_version_id:
            raise UserError(_("Publish a Job Description version before printing."))
        return self.env.ref(
            "onehr_job_description.action_report_jd_document"
        ).report_action(self.current_version_id)

    def action_archive_governed(self):
        require_jd_admin(self)
        self.write({"active": False})
        return display_notification(
            _("Job Description archived."),
            notification_type="warning",
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_without_history(self):
        require_jd_admin(self)
        for record in self:
            if record.version_ids.filtered(
                lambda version: version.state in ("approved", "published")
            ):
                raise UserError(
                    _("Job Descriptions with approved/published history must be archived, not deleted.")
                )

    @api.model
    def _cron_refresh_governance_metrics(self):
        today = fields.Date.context_today(self)
        records = self.search(
            [
                ("active", "=", True),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        records._refresh_governance_metrics()

        todo = self.env.ref("mail.mail_activity_data_todo")
        approver_group = self.env.ref(
            "onehr_job_description.group_onehr_jd_approver"
        )
        for record in records.filtered(
            lambda jd: jd.current_version_id and jd.review_due_date
        ):
            days = (record.review_due_date - today).days
            if not 0 <= days <= 14:
                continue

            users = record.approver_user_ids or approver_group.users.filtered(
                lambda user: record.company_id in user.company_ids
            )
            for user in users:
                duplicate = record.activity_ids.filtered(
                    lambda activity: (
                        activity.activity_type_id == todo
                        and activity.user_id == user
                        and activity.date_deadline == record.review_due_date
                    )
                )
                if duplicate:
                    continue
                record.activity_schedule(
                    todo.id,
                    user_id=user.id,
                    date_deadline=record.review_due_date,
                    summary=_("Job Description review due"),
                    note=_("Review current published JD %s.") % record.display_name,
                )
        return True

