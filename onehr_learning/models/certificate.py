import base64
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action
from .authority_helpers import require_learning_manager, require_learning_officer


class OneHRLearningCertificate(models.Model):
    """Issued learning/certification evidence with expiry governance."""

    _name = "onehr.learning.certificate"
    _description = "OneHR Learning Certificate"
    _inherit = ["onehr.mixin.audit"]
    _order = "issue_date desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_learning_certificate_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_learning_certificate_evidence_controlled"

    name = fields.Char(
        string="Certificate No.",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    enrollment_id = fields.Many2one(
        "onehr.learning.enrollment",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    session_id = fields.Many2one(
        "onehr.learning.session",
        related="enrollment_id.session_id",
        store=True,
        readonly=True,
        index=True,
    )
    course_id = fields.Many2one(
        "onehr.learning.course",
        related="enrollment_id.course_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="enrollment_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="enrollment_id.employee_id",
        store=True,
        readonly=True,
        index=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    employee_name = fields.Char(
        related="enrollment_id.employee_name",
        store=True,
        readonly=True,
        index=True,
    )
    employee_number = fields.Char(
        related="enrollment_id.employee_number",
        store=True,
        readonly=True,
        index=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("valid", "Valid"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    issue_date = fields.Date(readonly=True, copy=False, index=True)
    valid_from = fields.Date(readonly=True, copy=False, index=True)
    valid_to = fields.Date(readonly=True, copy=False, index=True)
    reminder_date = fields.Date(readonly=True, copy=False, index=True)
    last_reminder_at = fields.Datetime(readonly=True, copy=False)
    issued_at = fields.Datetime(readonly=True, copy=False)
    issued_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    revoked_at = fields.Datetime(readonly=True, copy=False)
    revoked_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    revocation_reason = fields.Text(tracking=True)

    days_to_expiry = fields.Integer(compute="_compute_expiry_status")
    expiry_status = fields.Selection(
        [
            ("none", "No Expiry"),
            ("valid", "Valid"),
            ("due", "Due Soon"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        compute="_compute_expiry_status",
    )

    # Soft Document integration evidence.
    document_target_model = fields.Char(readonly=True, copy=False)
    document_target_res_id = fields.Integer(readonly=True, copy=False)
    document_target_label = fields.Char(readonly=True, copy=False)
    document_version_res_id = fields.Integer(readonly=True, copy=False)

    _certificate_number_unique = models.Constraint(
        "unique(name)",
        "Learning Certificate number must be unique.",
    )
    _certificate_enrollment_unique = models.Constraint(
        "unique(enrollment_id)",
        "Each Learning Enrollment may issue only one certificate.",
    )

    @api.depends("state", "valid_to", "course_id.certificate_reminder_days")
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.state == "revoked":
                record.days_to_expiry = 0
                record.expiry_status = "revoked"
            elif not record.valid_to:
                record.days_to_expiry = 0
                record.expiry_status = "none"
            else:
                record.days_to_expiry = (record.valid_to - today).days
                if record.state == "expired" or record.valid_to < today:
                    record.expiry_status = "expired"
                elif record.days_to_expiry <= record.course_id.certificate_reminder_days:
                    record.expiry_status = "due"
                else:
                    record.expiry_status = "valid"

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("Learning Certificates must be created in Draft."))
            enrollment = self.env["onehr.learning.enrollment"].browse(
                vals.get("enrollment_id")
            ).exists()
            if not enrollment:
                raise ValidationError(_("A valid Learning Enrollment is required."))
            if enrollment.state != "passed":
                raise ValidationError(_("A Certificate may be created only for a Passed Enrollment."))
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.learning.certificate"
                ) or _("New")
            prepared.append(vals)
        return super().create(prepared)

    def _write_governed(self, values):
        return super(OneHRLearningCertificate, self).write(values)

    def write(self, values):
        require_learning_officer(self)
        values = dict(values)
        state_evidence = {
            "state", "issue_date", "valid_from", "valid_to", "reminder_date",
            "last_reminder_at", "issued_at", "issued_by_id",
            "revoked_at", "revoked_by_id",
        }
        integration_evidence = {
            "document_target_model", "document_target_res_id",
            "document_target_label", "document_version_res_id",
        }
        if state_evidence & set(values) and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Certificate lifecycle evidence changes only through governed actions."))
        if integration_evidence & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Certificate Document integration evidence is server-controlled."))
        if any(record.state in {"expired", "revoked"} for record in self):
            editable = {"revocation_reason"}
            if set(values) - editable and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Expired/Revoked certificate evidence is frozen."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_certificate_evidence(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft" or record.document_target_res_id:
                raise AccessError(_("Issued/integrated Learning Certificates cannot be deleted."))

    def action_issue(self):
        require_learning_officer(self)
        today = fields.Date.context_today(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a Draft Certificate can be issued."))
            if record.enrollment_id.state != "passed":
                raise UserError(_("Enrollment must still be Passed before certificate issue."))
            months = record.course_id.certificate_validity_months
            valid_to = today + relativedelta(months=months) if months else False
            reminder_date = (
                valid_to - relativedelta(days=record.course_id.certificate_reminder_days)
                if valid_to
                else False
            )
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {
                    "state": "valid",
                    "issue_date": today,
                    "valid_from": today,
                    "valid_to": valid_to,
                    "reminder_date": reminder_date,
                    "issued_at": fields.Datetime.now(),
                    "issued_by_id": self.env.user.id,
                }
            )
            record.log_business_action(_("Learning Certificate issued."))
        return True

    def action_revoke(self):
        require_learning_manager(self)
        for record in self:
            if record.state not in {"valid", "expired"}:
                raise UserError(_("Only an issued Certificate can be revoked."))
            if not (record.revocation_reason or "").strip():
                raise UserError(_("Enter a Revocation Reason before revoking the Certificate."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {
                    "state": "revoked",
                    "revoked_at": fields.Datetime.now(),
                    "revoked_by_id": self.env.user.id,
                }
            )
            record.log_business_action(
                _("Learning Certificate revoked: %s", record.revocation_reason)
            )
        return True

    def action_print_certificate(self):
        self.ensure_one()
        require_learning_officer(self)
        if self.state not in {"valid", "expired"}:
            raise UserError(_("Only issued Certificates can be printed."))
        return self.env.ref(
            "onehr_learning.action_report_learning_certificate"
        ).report_action(self)

    def action_push_to_document(self):
        """Soft integration that preserves Document's own authority and version model."""
        self.ensure_one()
        require_learning_officer(self)
        if self.state not in {"valid", "expired"}:
            raise UserError(_("Issue the Learning Certificate before sending it to Document."))
        if self.document_target_res_id:
            raise UserError(_("Certificate has already been sent to OneHR Document."))
        if "onehr.document" not in self.env.registry.models:
            raise UserError(_("OneHR Document is not installed."))

        document_group = self.env.ref(
            "onehr_document.group_onehr_document_officer",
            raise_if_not_found=False,
        )
        if not document_group or document_group not in self.env.user.group_ids:
            raise AccessError(
                _("Sending a certificate to Document requires OneHR Document Officer authority.")
            )

        code = (self.course_id.certificate_document_category_code or "").strip().upper()
        if not code:
            raise UserError(_("Configure Certificate Document Category Code on the Course."))

        Category = self.env["onehr.document.category"]
        category = Category.search(
            [
                ("code", "=", code),
                ("active", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            order="company_id desc, id desc",
        ).filtered(lambda item: item.is_effective_on(self.issue_date))
        if len(category) != 1:
            raise UserError(
                _("Document Category code '%s' must resolve to exactly one effective category.", code)
            )
        category = category[0]

        pdf_content, report_type = self.env["ir.actions.report"]._render_qweb_pdf(
            "onehr_learning.action_report_learning_certificate",
            self.ids,
        )
        if report_type != "pdf":
            raise UserError(_("Certificate PDF rendering is unavailable in the current runtime mode."))

        source_model = self.env["ir.model"].search(
            [("model", "=", self._name)],
            limit=1,
        )
        document = self.env["onehr.document"].create(
            {
                "name": _("Learning Certificate %(number)s", number=self.name),
                "category_id": category.id,
                "company_id": self.company_id.id,
                "employee_id": self.employee_id.id,
                "responsible_user_id": self.env.user.id,
                "source_model_id": source_model.id,
                "source_res_id": self.id,
                "valid_from": self.valid_from,
                "valid_to": self.valid_to,
            }
        )
        version = self.env["onehr.document.version"].create(
            {
                "document_id": document.id,
                "effective_from": self.valid_from,
                "effective_to": self.valid_to,
                "issue_date": self.issue_date,
                "expiry_date": self.valid_to,
                "file_data": base64.b64encode(pdf_content),
                "file_name": f"{self.name}.pdf",
                "mimetype": "application/pdf",
            }
        )
        version.action_issue()
        document.action_activate()

        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "document_target_model": document._name,
                "document_target_res_id": document.id,
                "document_target_label": document.display_name,
                "document_version_res_id": version.id,
            }
        )
        self.log_business_action(
            _("Certificate sent to OneHR Document: %s", document.display_name)
        )
        return display_notification(_("Certificate stored in OneHR Document."))

    def action_open_document(self):
        self.ensure_one()
        require_learning_officer(self)
        if not self.document_target_res_id or "onehr.document" not in self.env.registry.models:
            raise UserError(_("No available OneHR Document integration record exists."))
        return open_record_action(
            name=self.document_target_label or _("Certificate Document"),
            res_model="onehr.document",
            res_id=self.document_target_res_id,
        )

    @api.model
    def _cron_process_certificate_expiry(self):
        today = fields.Date.context_today(self)
        certificates = self.search(
            [("state", "=", "valid"), ("valid_to", "!=", False)]
        )
        todo = self.env.ref("mail.mail_activity_data_todo")
        for record in certificates:
            if record.valid_to < today:
                record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                    {"state": "expired"}
                )
                record.log_business_action(_("Learning Certificate expired automatically."))
                continue
            if (
                record.reminder_date
                and record.reminder_date <= today
                and not record.last_reminder_at
            ):
                record.activity_schedule(
                    todo.id,
                    user_id=record.responsible_user_id.id,
                    summary=_("Learning Certificate Renewal Due"),
                    note=_(
                        "%(certificate)s for %(employee)s expires on %(date)s.",
                        certificate=record.name,
                        employee=record.employee_name,
                        date=fields.Date.to_string(record.valid_to),
                    ),
                )
                record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                    {"last_reminder_at": fields.Datetime.now()}
                )
        return True
