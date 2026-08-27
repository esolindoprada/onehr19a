from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .authority_helpers import (
    notification,
    open_record,
    require_sop_admin,
    require_sop_editor,
)


class OneHRSOP(models.Model):
    _name = "onehr.sop"
    _description = "OneHR Standard Operating Procedure"
    _inherit = ["onehr.mixin.audit"]
    _order = "code desc, name"

    _sop_code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "SOP reference must be unique per company.",
    )

    _METRIC_CONTEXT = "onehr_sop_metric_write"

    name = fields.Char(
        string="SOP Title",
        required=True,
        translate=True,
        tracking=True,
        index=True,
    )
    code = fields.Char(
        string="SOP Reference",
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
        tracking=True,
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True, index=True)
    owner_user_id = fields.Many2one(
        "res.users",
        string="SOP Owner",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    owner_name = fields.Char(
        related="owner_user_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        string="SOP Owner",
    )

    document_category_id = fields.Many2one(
        "onehr.document.category",
        string="Archive Document Category",
        ondelete="restrict",
        tracking=True,
        domain="[('active', '=', True)]",
        groups="onehr_sop.group_onehr_sop_editor",
        help="Published SOP versions are archived to OneHR Document when this category is configured.",
    )
    archive_document_id = fields.Many2one(
        "onehr.document",
        string="SOP Archive",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="onehr_sop.group_onehr_sop_editor",
    )

    reviewer_user_ids = fields.Many2many(
        "res.users",
        "onehr_sop_reviewer_rel",
        "sop_id",
        "user_id",
        string="Reviewers",
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    approver_user_ids = fields.Many2many(
        "res.users",
        "onehr_sop_approver_rel",
        "sop_id",
        "user_id",
        string="Approvers",
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
        help="When populated, only assigned SOP Approvers or SOP Admin may approve/publish.",
    )

    review_interval_months = fields.Integer(
        default=12,
        required=True,
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    retention_years = fields.Integer(
        default=7,
        required=True,
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    ack_reminder_days = fields.Integer(
        string="Acknowledgement Reminder After (Days)",
        default=7,
        required=True,
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    publication_template_id = fields.Many2one(
        "mail.template",
        string="Publication Template",
        ondelete="restrict",
        default=lambda self: self.env.ref(
            "onehr_sop.mail_template_sop_publication",
            raise_if_not_found=False,
        ),
        groups="onehr_sop.group_onehr_sop_editor",
    )
    reminder_template_id = fields.Many2one(
        "mail.template",
        string="Acknowledgement Reminder Template",
        ondelete="restrict",
        default=lambda self: self.env.ref(
            "onehr_sop.mail_template_sop_ack_reminder",
            raise_if_not_found=False,
        ),
        groups="onehr_sop.group_onehr_sop_editor",
    )
    auto_email_reminders = fields.Boolean(
        default=False,
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
        help="When enabled, the daily governance scheduler queues reminder emails for pending acknowledgements.",
    )

    version_ids = fields.One2many(
        "onehr.sop.version",
        "sop_id",
        string="Versions",
    )
    latest_version_id = fields.Many2one(
        "onehr.sop.version",
        compute="_compute_version_summary",
        store=True,
        readonly=True,
    )
    current_version_id = fields.Many2one(
        "onehr.sop.version",
        compute="_compute_version_summary",
        store=True,
        readonly=True,
        string="Current Published Version",
        index=True,
    )
    version_count = fields.Integer(
        compute="_compute_version_summary",
        store=True,
    )
    lifecycle_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("approved", "Approved"),
            ("published", "Published"),
            ("obsolete", "Obsolete"),
        ],
        compute="_compute_version_summary",
        store=True,
        readonly=True,
        index=True,
    )

    current_ack_count = fields.Integer(
        compute="_compute_current_compliance",
        store=True,
        string="Audience",
    )
    current_acknowledged_count = fields.Integer(
        compute="_compute_current_compliance",
        store=True,
        string="Acknowledged",
    )
    current_pending_count = fields.Integer(
        compute="_compute_current_compliance",
        store=True,
        string="Pending",
    )
    current_ack_rate = fields.Float(
        compute="_compute_current_compliance",
        store=True,
        string="Acknowledgement %",
    )
    days_to_90_ack = fields.Float(
        compute="_compute_current_compliance",
        store=True,
        string="Days to 90% Ack",
    )
    current_review_due_date = fields.Date(
        compute="_compute_current_compliance",
        store=True,
        string="Review Due",
        index=True,
    )
    review_overdue = fields.Boolean(
        compute="_compute_current_compliance",
        store=True,
        index=True,
    )
    notes = fields.Html(
        string="Governance Notes",
        tracking=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_sop_editor(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code", "New") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("onehr.sop") or "New"
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._METRIC_CONTEXT):
            return super().write(vals)

        require_sop_editor(self)
        protected_identity = {"company_id", "document_category_id"}
        if protected_identity.intersection(vals):
            for record in self:
                if record.version_ids.filtered(
                    lambda version: version.state in ("approved", "published", "obsolete")
                ):
                    raise AccessError(
                        _(
                            "Company and archive category are frozen after governed SOP history exists."
                        )
                    )
        return super().write(vals)

    @api.depends(
        "version_ids.version_no",
        "version_ids.state",
        "version_ids.is_current",
        "version_ids.published_at",
    )
    def _compute_version_summary(self):
        for record in self:
            versions = record.version_ids
            latest = versions.sorted(
                key=lambda version: (
                    version.version_no,
                    version.create_date or fields.Datetime.now(),
                )
            )[-1:] if versions else versions
            current = versions.filtered(
                lambda version: version.state == "published" and version.is_current
            )[:1]

            record.latest_version_id = latest
            record.current_version_id = current
            record.version_count = len(versions)
            record.lifecycle_state = (
                current.state
                if current
                else (latest.state if latest else "draft")
            )

    @api.depends(
        "current_version_id",
        "current_version_id.ack_count",
        "current_version_id.acknowledged_count",
        "current_version_id.pending_count",
        "current_version_id.ack_rate",
        "current_version_id.days_to_90_ack",
        "current_version_id.review_due_date",
    )
    def _compute_current_compliance(self):
        today = fields.Date.context_today(self)
        for record in self:
            current = record.current_version_id
            record.current_ack_count = current.ack_count if current else 0
            record.current_acknowledged_count = (
                current.acknowledged_count if current else 0
            )
            record.current_pending_count = current.pending_count if current else 0
            record.current_ack_rate = current.ack_rate if current else 0.0
            record.days_to_90_ack = current.days_to_90_ack if current else 0.0
            record.current_review_due_date = (
                current.review_due_date if current else False
            )
            record.review_overdue = bool(
                current
                and current.review_due_date
                and current.review_due_date < today
            )

    @api.constrains(
        "company_id",
        "owner_user_id",
        "reviewer_user_ids",
        "approver_user_ids",
        "document_category_id",
    )
    def _check_governance_scope(self):
        for record in self:
            if record.company_id not in record.owner_user_id.company_ids:
                raise ValidationError(
                    _("The SOP Owner must be allowed in the SOP company.")
                )
            outside_reviewers = record.reviewer_user_ids.filtered(
                lambda user: record.company_id not in user.company_ids
            )
            outside_approvers = record.approver_user_ids.filtered(
                lambda user: record.company_id not in user.company_ids
            )
            if outside_reviewers or outside_approvers:
                raise ValidationError(
                    _("All reviewers and approvers must be allowed in the SOP company.")
                )
            if (
                record.document_category_id
                and record.document_category_id.company_id
                and record.document_category_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _("The archive document category must belong to the SOP company or be global.")
                )

    @api.constrains(
        "review_interval_months",
        "retention_years",
        "ack_reminder_days",
    )
    def _check_governance_numbers(self):
        for record in self:
            if record.review_interval_months < 1:
                raise ValidationError(_("Review interval must be at least one month."))
            if record.retention_years < 1:
                raise ValidationError(_("Retention must be at least one year."))
            if record.ack_reminder_days < 1:
                raise ValidationError(
                    _("Acknowledgement reminder interval must be at least one day.")
                )

    def _require_assigned_approver(self):
        from .authority_helpers import is_sop_admin

        for record in self:
            if (
                record.approver_user_ids
                and self.env.user not in record.approver_user_ids
                and not is_sop_admin(self.env)
            ):
                raise AccessError(
                    _("You are not assigned as an approver for %s.") % record.display_name
                )

    def _default_review_due_date(self, effective_from=None):
        self.ensure_one()
        effective_from = fields.Date.to_date(
            effective_from or fields.Date.context_today(self)
        )
        return effective_from + relativedelta(months=self.review_interval_months)

    def action_create_new_version(self):
        require_sop_editor(self)
        self.ensure_one()

        in_flight = self.version_ids.filtered(
            lambda version: version.state in ("draft", "review", "approved")
        )
        if in_flight:
            return open_record(
                name=_("SOP Version"),
                res_model="onehr.sop.version",
                res_id=in_flight.sorted("version_no")[-1].id,
            )

        source = self.current_version_id or self.latest_version_id
        effective_from = fields.Date.context_today(self)
        values = {
            "sop_id": self.id,
            "effective_from": effective_from,
            "review_due_date": self._default_review_due_date(effective_from),
        }
        if source:
            values.update(source._copy_content_values())
            values["change_summary"] = _(
                "Controlled successor created from version %s."
            ) % source.version_no
            values["change_reason"] = _("Periodic or controlled SOP revision")

        version = self.env["onehr.sop.version"].create(values)
        return open_record(
            name=_("SOP Version"),
            res_model="onehr.sop.version",
            res_id=version.id,
        )

    def action_open_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("SOP Versions — %s") % self.display_name,
            "res_model": "onehr.sop.version",
            "view_mode": "list,form,calendar",
            "domain": [("sop_id", "=", self.id)],
            "context": {"default_sop_id": self.id},
        }

    def action_open_current_version(self):
        self.ensure_one()
        if not self.current_version_id:
            raise UserError(_("This SOP has no current Published version."))
        return open_record(
            name=_("Published SOP"),
            res_model="onehr.sop.version",
            res_id=self.current_version_id.id,
        )

    def action_open_acknowledgements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Acknowledgements — %s") % self.display_name,
            "res_model": "onehr.sop.ack",
            "view_mode": "list,pivot,graph,form",
            "domain": [("sop_id", "=", self.id)],
        }

    def action_open_archive_document(self):
        require_sop_editor(self)
        self.ensure_one()
        if not self.archive_document_id:
            raise UserError(_("No OneHR Document archive exists for this SOP yet."))
        return open_record(
            name=_("SOP Archive"),
            res_model="onehr.document",
            res_id=self.archive_document_id.id,
        )

    def action_print_current_sop(self):
        self.ensure_one()
        if not self.current_version_id:
            raise UserError(_("Publish an SOP version before printing."))
        return self.env.ref("onehr_sop.action_report_sop_document").report_action(
            self.current_version_id
        )

    def action_archive_master(self):
        require_sop_admin(self)
        self.write({"active": False})
        return notification(
            _("SOP master archived. Published/obsolete version history was preserved."),
            notification_type="warning",
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_without_governed_history(self):
        require_sop_admin(self)
        for record in self:
            if record.version_ids.filtered(
                lambda version: version.state in ("approved", "published", "obsolete")
            ):
                raise UserError(
                    _("SOPs with governed history must be archived, not deleted.")
                )

    @api.model
    def _cron_sop_governance(self):
        today = fields.Date.context_today(self)
        deadline = today + relativedelta(days=30)
        records = self.search(
            [
                ("active", "=", True),
                ("company_id", "in", self.env.companies.ids),
                ("current_version_id", "!=", False),
            ]
        )
        todo = self.env.ref("mail.mail_activity_data_todo")

        for sop in records:
            version = sop.current_version_id
            if version.review_due_date and version.review_due_date <= deadline:
                users = sop.approver_user_ids or sop.reviewer_user_ids or sop.owner_user_id
                for user in users:
                    existing = sop.activity_ids.filtered(
                        lambda activity: (
                            activity.activity_type_id == todo
                            and activity.user_id == user
                            and activity.date_deadline == version.review_due_date
                            and activity.summary == _("SOP periodic review due")
                        )
                    )
                    if not existing:
                        sop.activity_schedule(
                            todo.id,
                            user_id=user.id,
                            date_deadline=version.review_due_date,
                            summary=_("SOP periodic review due"),
                            note=_(
                                "Review current SOP %s version %s."
                            ) % (sop.code, version.version_no),
                        )

            if version.state == "published":
                version._send_ack_reminders(from_cron=True)
        return True
