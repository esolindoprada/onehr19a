import base64
import hashlib
import mimetypes
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import (
    open_record_action,
    open_records_action,
    open_wizard_action,
    require_document_manager,
    require_document_officer,
    require_document_officer_or_compliance,
    source_record_from_pair,
)


DOCUMENT_STATES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("archived", "Archived"),
]

VERSION_STATES = [
    ("draft", "Draft"),
    ("issued", "Issued"),
    ("signature_pending", "Signature Pending"),
    ("signed", "Signed"),
    ("expired", "Expired"),
    ("archived", "Archived"),
    ("superseded", "Superseded"),
]


class OneHRDocument(models.Model):
    """Logical document header.

    Binary payload and issued facts live on immutable onehr.document.version
    records. Other OneHR domains should reference this header/version rather
    than copying attachments into domain-specific tables.
    """

    _name = "onehr.document"
    _description = "OneHR HR Document"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "document_number desc, id desc"

    _unique_document_number = models.UniqueIndex("(document_number)")

    document_number = fields.Char(
        required=True,
        readonly=True,
        default=lambda self: _("New"),
        copy=False,
        index=True,
        tracking=True,
    )
    name = fields.Char(required=True, tracking=True)
    category_id = fields.Many2one(
        "onehr.document.category",
        required=True,
        ondelete="restrict",
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
    employee_id = fields.Many2one(
        "hr.employee",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Optional employee owner. Business-owned documents may instead use a controlled source reference.",
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        string="Employee Number",
        readonly=True,
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    source_model_id = fields.Many2one(
        "ir.model",
        string="Source Model",
        ondelete="set null",
        tracking=True,
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    source_res_id = fields.Integer(
        string="Source Record ID",
        tracking=True,
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    source_display_name = fields.Char(
        readonly=True,
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    template_id = fields.Many2one(
        "onehr.document.template",
        ondelete="restrict",
        tracking=True,
        readonly=True,
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
        help="Template master used for generated documents. Upload-only documents may leave this empty.",
    )
    keywords = fields.Char(
        help="Search keywords without introducing a parallel tag master.",
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    state = fields.Selection(
        DOCUMENT_STATES,
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    version_ids = fields.One2many(
        "onehr.document.version",
        "document_id",
        string="Versions",
    )
    current_version_id = fields.Many2one(
        "onehr.document.version",
        compute="_compute_version_summary",
        string="Current Version",
    )
    version_count = fields.Integer(compute="_compute_version_summary", string="Versions")
    signed_version_count = fields.Integer(
        compute="_compute_version_summary",
        string="Signed",
    )
    expiring_version_count = fields.Integer(
        compute="_compute_version_summary",
        string="Expiring",
    )
    esign_transaction_count = fields.Integer(
        compute="_compute_esign_transaction_count",
        string="E-Sign Transactions",
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )

    @staticmethod
    def _validate_category_effective(category, as_of_date):
        if not category.active or not category.is_effective_on(as_of_date):
            raise ValidationError(
                _("The selected document category must be active and effective on the document date.")
            )

    def _validate_responsible_user(self, user, company, category):
        if not user or company not in user.company_ids:
            raise ValidationError(
                _("The Responsible User must be allowed to operate in the document company.")
            )
        if not user.has_group("onehr_document.group_onehr_document_officer"):
            raise AccessError(
                _("The Responsible User must have OneHR Document Officer access.")
            )
        if (
            category.sensitivity == "restricted"
            and not user.has_group("onehr_document.group_onehr_document_compliance")
        ):
            raise AccessError(
                _("Restricted documents require a Responsible User with explicit Document Compliance access in addition to operational access.")
            )

    @staticmethod
    def _validate_template_binding(template, category, company, as_of_date):
        if not template:
            return
        if template.category_id != category:
            raise ValidationError(_("The document template category must match the document category."))
        if template.company_id and template.company_id != company:
            raise ValidationError(_("The document template is not available in the document company."))
        if not template.active or not template.is_effective_on(as_of_date):
            raise ValidationError(_("The document template must be active and effective on the document date."))

    @api.model_create_multi
    def create(self, vals_list):
        require_document_officer(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            company = self.env["res.company"].browse(
                vals.get("company_id") or self.env.company.id
            ).exists()
            if not company:
                raise ValidationError(_("A valid document company is required."))
            vals["company_id"] = company.id

            category = self.env["onehr.document.category"].browse(
                vals.get("category_id")
            ).exists()
            if not category:
                raise ValidationError(_("A valid document category is required."))
            self._validate_category_company(category, company)
            document_date = fields.Date.to_date(
                vals.get("valid_from") or fields.Date.context_today(self)
            )
            vals["valid_from"] = document_date
            self._validate_category_effective(category, document_date)

            responsible = self.env["res.users"].browse(
                vals.get("responsible_user_id") or self.env.user.id
            ).exists()
            self._validate_responsible_user(responsible, company, category)
            vals["responsible_user_id"] = responsible.id

            template = self.env["onehr.document.template"].browse(
                vals.get("template_id")
            ).exists()
            self._validate_template_binding(
                template, category, company, document_date
            )

            employee = self.env["hr.employee"].browse(
                vals.get("employee_id")
            ).exists()
            if employee and employee.company_id != company:
                raise ValidationError(
                    _("The employee and document company must match when the document is created.")
                )

            source_model = self.env["ir.model"].browse(
                vals.get("source_model_id")
            ).exists()
            source = source_record_from_pair(
                self.env,
                source_model,
                vals.get("source_res_id"),
                require_read=True,
            )
            if source and source._name != "ir.model":
                vals["source_display_name"] = source.display_name

            if vals.get("document_number") in (None, False, "", _("New")):
                vals["document_number"] = (
                    self.env["ir.sequence"].next_by_code("onehr.document") or _("New")
                )
            prepared.append(vals)

        records = super().create(prepared)
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_("HR document created: %s", record.display_name),
                severity="high"
                if record.category_id.sensitivity == "restricted"
                else "medium",
                record=record,
                company=record.company_id,
                after={
                    "document_number": record.document_number,
                    "employee_id": record.employee_id.id,
                    "category_id": record.category_id.id,
                    "source_model": record.source_model_id.model,
                    "source_res_id": record.source_res_id,
                },
            )
        return records

    @staticmethod
    def _validate_category_company(category, company):
        if category.company_id and category.company_id != company:
            raise ValidationError(
                _("The selected category is not available in the document company.")
            )

    @api.constrains(
        "category_id",
        "company_id",
        "responsible_user_id",
        "template_id",
        "valid_from",
        "valid_to",
    )
    def _check_document_governance_scope(self):
        for record in self:
            self._validate_category_company(record.category_id, record.company_id)
            self._validate_category_effective(record.category_id, record.valid_from)
            self._validate_responsible_user(
                record.responsible_user_id,
                record.company_id,
                record.category_id,
            )
            self._validate_template_binding(
                record.template_id,
                record.category_id,
                record.company_id,
                record.valid_from,
            )

    @api.constrains("source_model_id", "source_res_id")
    def _check_source_pair(self):
        for record in self:
            if bool(record.source_model_id) != bool(record.source_res_id):
                raise ValidationError(
                    _("Source Model and Source Record ID must either both be set or both be empty.")
                )
            if record.source_res_id and record.source_res_id < 1:
                raise ValidationError(_("Source Record ID must be a positive integer."))

    def write(self, vals):
        require_document_officer(self.env)
        values = dict(vals)
        protected_after_versions = {
            "document_number",
            "company_id",
            "employee_id",
            "category_id",
            "source_model_id",
            "source_res_id",
            "template_id",
            "valid_from",
        }
        if protected_after_versions & set(values) and any(
            record.version_ids for record in self
        ):
            raise AccessError(
                _(
                    "Document ownership and governing identity cannot be rewritten "
                    "after a version exists. Create a new logical document instead."
                )
            )

        if "state" in values and not self.env.context.get("onehr_document_state_action"):
            if any(values["state"] != record.state for record in self):
                raise AccessError(
                    _("Use controlled document actions to change lifecycle state.")
                )

        if "category_id" in values or "company_id" in values:
            for record in self:
                category = self.env["onehr.document.category"].browse(
                    values.get("category_id", record.category_id.id)
                )
                company = self.env["res.company"].browse(
                    values.get("company_id", record.company_id.id)
                )
                self._validate_category_company(category, company)

        if "source_model_id" in values or "source_res_id" in values:
            # Single write() vals are shared by every record, so the same source
            # snapshot is valid only when this write explicitly changes the source.
            model = self.env["ir.model"].browse(
                values.get("source_model_id")
                or (self[:1].source_model_id.id if self else False)
            ).exists()
            res_id = values.get(
                "source_res_id",
                self[:1].source_res_id if self else False,
            )
            source = source_record_from_pair(
                self.env,
                model,
                res_id,
                require_read=True,
            )
            values["source_display_name"] = (
                source.display_name
                if source and source._name != "ir.model"
                else False
            )

        # Re-evaluate responsibility and temporal policy before ORM write.
        for record in self:
            category = self.env["onehr.document.category"].browse(
                values.get("category_id", record.category_id.id)
            )
            company = self.env["res.company"].browse(
                values.get("company_id", record.company_id.id)
            )
            responsible = self.env["res.users"].browse(
                values.get("responsible_user_id", record.responsible_user_id.id)
            )
            document_date = fields.Date.to_date(
                values.get("valid_from", record.valid_from)
            )
            template = self.env["onehr.document.template"].browse(
                values.get("template_id", record.template_id.id)
            )
            self._validate_category_company(category, company)
            self._validate_category_effective(category, document_date)
            self._validate_responsible_user(responsible, company, category)
            self._validate_template_binding(
                template, category, company, document_date
            )

        before = {
            record.id: {
                "name": record.name,
                "responsible_user_id": record.responsible_user_id.id,
                "keywords": record.keywords,
                "state": record.state,
            }
            for record in self
        }
        result = super().write(values)

        auditable = {"name", "responsible_user_id", "keywords"} & set(values)
        if auditable:
            for record in self:
                self.env["onehr.audit.log"]._log_event(
                    action="update",
                    summary=_("HR document metadata updated"),
                    severity="medium",
                    record=record,
                    company=record.company_id,
                    changed_fields=auditable,
                    before=before[record.id],
                    after={
                        "name": record.name,
                        "responsible_user_id": record.responsible_user_id.id,
                        "keywords": record.keywords,
                        "state": record.state,
                    },
                )
        return result

    def _compute_version_summary(self):
        today = fields.Date.context_today(self)
        warning_date = today + timedelta(days=30)
        for record in self:
            versions = record.version_ids
            active_versions = versions.filtered(
                lambda row: row.state not in ("archived", "superseded")
            ).sorted(lambda row: (row.version, row.id), reverse=True)
            record.current_version_id = active_versions[:1]
            record.version_count = len(versions)
            record.signed_version_count = len(
                versions.filtered(lambda row: row.state == "signed")
            )
            record.expiring_version_count = len(
                versions.filtered(
                    lambda row: row.expiry_date
                    and today <= row.expiry_date <= warning_date
                    and row.state not in ("expired", "archived", "superseded")
                )
            )

    def _compute_esign_transaction_count(self):
        can_read = self.env.is_superuser() or (
            self.env.user.has_group("onehr_document.group_onehr_document_officer")
            or self.env.user.has_group("onehr_document.group_onehr_document_compliance")
        )
        for record in self:
            if not can_read:
                record.esign_transaction_count = 0
                continue
            record.esign_transaction_count = sum(
                len(row.esign_transaction_ids) for row in record.version_ids
            )

    def action_activate(self):
        require_document_officer(self.env)
        self.with_context(onehr_document_state_action=True).write(
            {"state": "active"}
        )
        return True

    def action_archive(self):
        require_document_manager(self.env)
        self.with_context(onehr_document_state_action=True).write(
            {"state": "archived"}
        )
        return True

    def action_new_version(self):
        self.ensure_one()
        require_document_officer(self.env)
        latest_number = max(self.version_ids.mapped("version") or [0])
        version = self.env["onehr.document.version"].create(
            {
                "document_id": self.id,
                "version": latest_number + 1,
                "effective_from": fields.Date.context_today(self),
            }
        )
        return open_record_action(
            name=_("Document Version %s", version.version),
            res_model=version._name,
            res_id=version.id,
        )

    def action_generate_from_template(self):
        self.ensure_one()
        require_document_officer(self.env)
        return open_wizard_action(
            name=_("Generate Document from Template"),
            res_model="wizard.document.generate",
            context={
                "default_document_id": self.id,
                "default_template_id": self.template_id.id,
                "default_employee_id": self.employee_id.id,
                "default_category_id": self.category_id.id,
                "default_company_id": self.company_id.id,
                "default_source_model_id": self.source_model_id.id,
                "default_source_res_id": self.source_res_id,
                "default_document_name": self.name,
            },
        )

    def action_open_versions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Document Versions — %s", self.display_name),
            res_model="onehr.document.version",
            domain=[("document_id", "=", self.id)],
            context={"default_document_id": self.id},
        )

    def action_open_current_version(self):
        self.ensure_one()
        if not self.current_version_id:
            raise UserError(_("This document has no current version."))
        return open_record_action(
            name=self.current_version_id.display_name,
            res_model="onehr.document.version",
            res_id=self.current_version_id.id,
        )

    def action_open_employee(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_("This document is not employee-owned."))
        self.employee_id.check_access("read")
        return open_record_action(
            name=self.employee_id.display_name,
            res_model="hr.employee",
            res_id=self.employee_id.id,
        )

    def action_open_source(self):
        self.ensure_one()
        source = source_record_from_pair(
            self.env,
            self.source_model_id,
            self.source_res_id,
            require_read=True,
        )
        if not source or source._name == "ir.model":
            raise UserError(_("This document has no source business record."))
        return open_record_action(
            name=source.display_name,
            res_model=source._name,
            res_id=source.id,
        )

    def action_open_esign_transactions(self):
        self.ensure_one()
        require_document_officer_or_compliance(self.env)
        return open_records_action(
            name=_("E-Sign Transactions — %s", self.display_name),
            res_model="onehr.esign.transaction",
            domain=[("document_version_id.document_id", "=", self.id)],
        )


class OneHRDocumentVersion(models.Model):
    _name = "onehr.document.version"
    _description = "OneHR Document Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "document_id, version desc, id desc"

    _unique_document_version = models.UniqueIndex("(document_id, version)")

    document_id = fields.Many2one(
        "onehr.document",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    version = fields.Integer(required=True, default=1, tracking=True)
    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        related="document_id.company_id",
        store=True,
        index=True,
    )
    employee_id = fields.Many2one(
        related="document_id.employee_id",
        store=True,
        index=True,
    )
    category_id = fields.Many2one(
        related="document_id.category_id",
        store=True,
        index=True,
    )
    responsible_user_id = fields.Many2one(
        related="document_id.responsible_user_id",
        store=True,
        index=True,
    )
    template_version_id = fields.Many2one(
        "onehr.document.template.version",
        ondelete="restrict",
        index=True,
        readonly=True,
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    state = fields.Selection(
        VERSION_STATES,
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )

    # ED2 facts. `valid_from/valid_to` are inherited from the approved OneHR
    # effective-dated mixin; these operational names are explicit document facts.
    effective_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    effective_to = fields.Date(tracking=True, index=True)
    issue_date = fields.Date(tracking=True, index=True)
    expiry_date = fields.Date(tracking=True, index=True)
    grace_end_date = fields.Date(readonly=True, index=True)
    reminder_date = fields.Date(readonly=True, index=True)
    retention_due_date = fields.Date(readonly=True, index=True)
    last_reminder_at = fields.Datetime(readonly=True)
    reminder_activity_id = fields.Many2one(
        "mail.activity",
        readonly=True,
        ondelete="set null",
    )

    rendered_subject = fields.Char(readonly=True)
    rendered_content_html = fields.Html(sanitize=True, readonly=True)
    file_data = fields.Binary(
        attachment=True,
        string="Document File",
    )
    file_name = fields.Char()
    mimetype = fields.Char()
    file_checksum = fields.Char(readonly=True, index=True)

    issued_at = fields.Datetime(readonly=True)
    issued_by_id = fields.Many2one("res.users", readonly=True)
    signed_at = fields.Datetime(readonly=True)
    signed_by_id = fields.Many2one("res.users", readonly=True)
    expiry_reason = fields.Char(readonly=True)

    esign_transaction_ids = fields.One2many(
        "onehr.esign.transaction",
        "document_version_id",
        string="E-Sign Transactions",
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    esign_transaction_count = fields.Integer(
        compute="_compute_esign_transaction_count",
        string="E-Sign Transactions",
        groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance",
    )
    days_to_expiry = fields.Integer(compute="_compute_days_to_expiry")
    expiry_status = fields.Selection(
        [
            ("none", "No Expiry"),
            ("valid", "Valid"),
            ("due", "Due Soon"),
            ("grace", "Grace"),
            ("expired", "Expired"),
        ],
        compute="_compute_days_to_expiry",
    )

    @api.depends("document_id.document_number", "version")
    def _compute_name(self):
        for record in self:
            record.name = _(
                "%s / V%s",
                record.document_id.document_number,
                record.version,
            )

    @api.constrains("document_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("document_id", "=", record.document_id.id),
                    ("version", "=", record.version),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Document version number must be unique per document.")
                )

    @api.constrains(
        "effective_from",
        "effective_to",
        "expiry_date",
        "issue_date",
        "valid_from",
        "valid_to",
    )
    def _check_dates(self):
        for record in self:
            if record.effective_to and record.effective_to < record.effective_from:
                raise ValidationError(
                    _("Effective To must be on or after Effective From.")
                )
            if record.expiry_date and record.expiry_date < record.effective_from:
                raise ValidationError(
                    _("Expiry Date cannot be before Effective From.")
                )
            if (
                record.issue_date
                and record.expiry_date
                and record.expiry_date < record.issue_date
            ):
                raise ValidationError(
                    _("Expiry Date cannot be before Issue Date.")
                )
            if record.valid_from != record.effective_from:
                raise ValidationError(
                    _("Registry ED2 Valid From must match the document Effective From.")
                )
            if record.valid_to != record.effective_to:
                raise ValidationError(
                    _("Registry ED2 Valid To must match the document Effective To.")
                )

    @staticmethod
    def _prepare_binary_metadata(values):
        if "file_data" not in values:
            return
        encoded = values.get("file_data")
        if not encoded:
            values["file_checksum"] = False
            return
        try:
            raw = base64.b64decode(encoded)
        except Exception as exc:
            raise ValidationError(_("The uploaded document file is not valid base64 content.")) from exc
        values["file_checksum"] = hashlib.sha256(raw).hexdigest()
        if not values.get("mimetype") and values.get("file_name"):
            values["mimetype"] = (
                mimetypes.guess_type(values["file_name"])[0]
                or "application/octet-stream"
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_document_officer(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            self._prepare_binary_metadata(vals)
            document = self.env["onehr.document"].browse(
                vals.get("document_id")
            ).exists()
            if not document:
                raise ValidationError(
                    _("A valid logical document is required.")
                )
            if document.state == "archived":
                raise UserError(
                    _("New versions cannot be added to an archived document.")
                )

            if not vals.get("version"):
                latest_number = max(document.version_ids.mapped("version") or [0])
                vals["version"] = latest_number + 1

            category = document.category_id
            effective_from = fields.Date.to_date(
                vals.get("effective_from")
                or vals.get("valid_from")
                or fields.Date.context_today(self)
            )
            vals["effective_from"] = effective_from
            vals["valid_from"] = effective_from

            effective_to = fields.Date.to_date(
                vals.get("effective_to") or vals.get("valid_to")
            ) if (vals.get("effective_to") or vals.get("valid_to")) else False
            vals["effective_to"] = effective_to
            vals["valid_to"] = effective_to

            if not document.is_effective_on(effective_from):
                raise ValidationError(
                    _("The document version Effective From must fall inside the logical document validity.")
                )
            if document.valid_to and (not effective_to or effective_to > document.valid_to):
                raise ValidationError(
                    _("The document version Effective To must not exceed the logical document Valid To.")
                )
            if not category.active or not category.is_effective_on(effective_from):
                raise ValidationError(
                    _("The document category must be active and effective when the version becomes effective.")
                )

            template_version = self.env["onehr.document.template.version"].browse(
                vals.get("template_version_id")
            ).exists()
            if template_version:
                if not document.template_id or template_version.template_id != document.template_id:
                    raise ValidationError(
                        _("Template Version must belong to the logical document's governing Template.")
                    )
                if template_version.state != "active" or not template_version.is_effective_on(effective_from):
                    raise ValidationError(
                        _("Template Version must be active and effective when generated output is created.")
                    )

            if not vals.get("expiry_date") and category.default_validity_days:
                vals["expiry_date"] = effective_from + timedelta(
                    days=category.default_validity_days
                )

            expiry = (
                fields.Date.to_date(vals.get("expiry_date"))
                if vals.get("expiry_date")
                else False
            )
            if expiry:
                vals["reminder_date"] = expiry - timedelta(
                    days=category.default_reminder_days
                )
                vals["grace_end_date"] = expiry + timedelta(
                    days=category.default_grace_days
                )
                if category.retention_days_after_expiry:
                    vals["retention_due_date"] = expiry + timedelta(
                        days=category.retention_days_after_expiry
                    )
            prepared.append(vals)

        records = super().create(prepared)
        for record in records:
            if record.document_id.state == "draft":
                record.document_id.action_activate()
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_("Document version created: %s", record.display_name),
                severity="high"
                if record.category_id.sensitivity == "restricted"
                else "medium",
                record=record,
                company=record.company_id,
                after={
                    "document_id": record.document_id.id,
                    "version": record.version,
                    "state": record.state,
                    "template_version_id": record.template_version_id.id,
                },
            )
        return records

    def write(self, vals):
        require_document_officer(self.env)
        values = dict(vals)
        self._prepare_binary_metadata(values)

        # Keep Registry ED2 dates and domain-facing effective dates synchronized.
        if "effective_from" in values:
            values["valid_from"] = values["effective_from"]
        elif "valid_from" in values:
            values["effective_from"] = values["valid_from"]
        if "effective_to" in values:
            values["valid_to"] = values["effective_to"]
        elif "valid_to" in values:
            values["effective_to"] = values["valid_to"]

        immutable_fields = {
            "document_id",
            "version",
            "template_version_id",
            "effective_from",
            "effective_to",
            "valid_from",
            "valid_to",
            "issue_date",
            "expiry_date",
            "grace_end_date",
            "reminder_date",
            "retention_due_date",
            "rendered_subject",
            "rendered_content_html",
            "file_data",
            "file_name",
            "mimetype",
            "file_checksum",
        }
        if immutable_fields & set(values) and any(
            record.state != "draft" for record in self
        ):
            raise AccessError(
                _(
                    "Issued document versions are immutable. "
                    "Create a successor version instead."
                )
            )

        if (
            "state" in values
            and not self.env.context.get("onehr_document_version_state_action")
        ):
            if any(values["state"] != record.state for record in self):
                raise AccessError(
                    _("Use controlled document-version actions to change state.")
                )

        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_issued_history(self):
        if any(record.state != "draft" for record in self):
            raise AccessError(
                _("Issued document-version history cannot be deleted.")
            )

    def _compute_esign_transaction_count(self):
        can_read = self.env.is_superuser() or (
            self.env.user.has_group("onehr_document.group_onehr_document_officer")
            or self.env.user.has_group("onehr_document.group_onehr_document_compliance")
        )
        for record in self:
            record.esign_transaction_count = (
                len(record.esign_transaction_ids) if can_read else 0
            )

    @api.depends("expiry_date", "grace_end_date", "state")
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for record in self:
            if not record.expiry_date:
                record.days_to_expiry = 0
                record.expiry_status = "none"
                continue
            record.days_to_expiry = (record.expiry_date - today).days
            if record.state == "expired" or (
                record.grace_end_date and today > record.grace_end_date
            ):
                record.expiry_status = "expired"
            elif today > record.expiry_date:
                record.expiry_status = "grace"
            elif record.days_to_expiry <= 30:
                record.expiry_status = "due"
            else:
                record.expiry_status = "valid"

    def action_issue(self):
        require_document_officer(self.env)
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft versions can be issued."))
            if not record.file_data and not record.rendered_content_html:
                raise UserError(
                    _(
                        "Provide a generated body or uploaded file before "
                        "issuing the version."
                    )
                )
            record.with_context(
                onehr_document_version_state_action=True
            ).write(
                {
                    "state": "issued",
                    "issue_date": record.issue_date or today,
                    "issued_at": now,
                    "issued_by_id": self.env.user.id,
                }
            )
            self.env["onehr.audit.log"]._log_event(
                action="activate",
                summary=_("Document version issued: %s", record.display_name),
                severity="high"
                if record.category_id.sensitivity == "restricted"
                else "medium",
                record=record,
                company=record.company_id,
                changed_fields={"state"},
                after={"state": "issued", "issue_date": record.issue_date},
            )
        return True

    def action_request_signature(self):
        self.ensure_one()
        require_document_manager(self.env)
        if self.state not in ("issued", "signature_pending"):
            raise UserError(
                _(
                    "Only Issued or Signature Pending versions can request "
                    "e-signature."
                )
            )
        return open_wizard_action(
            name=_("Publish / Request Signature"),
            res_model="wizard.document.publish.sign",
            context={
                "default_document_id": self.document_id.id,
                "default_document_version_id": self.id,
                "default_signer_name": self.employee_id.name,
                "default_signer_email": self.employee_id.work_email,
            },
        )

    def action_mark_signed(self):
        require_document_manager(self.env)
        for record in self:
            if record.state not in ("issued", "signature_pending"):
                raise UserError(
                    _(
                        "Only Issued or Signature Pending versions can be "
                        "marked Signed."
                    )
                )
            record.with_context(
                onehr_document_version_state_action=True
            ).write(
                {
                    "state": "signed",
                    "signed_at": fields.Datetime.now(),
                    "signed_by_id": self.env.user.id,
                }
            )
            self.env["onehr.audit.log"]._log_event(
                action="other",
                summary=_(
                    "Document version marked signed: %s",
                    record.display_name,
                ),
                severity="high",
                record=record,
                company=record.company_id,
                changed_fields={"state"},
                after={"state": "signed"},
            )
        return True

    def action_expire(self):
        require_document_officer(self.env)
        for record in self.filtered(
            lambda item: item.state
            not in ("archived", "superseded", "expired")
        ):
            record.with_context(
                onehr_document_version_state_action=True
            ).write(
                {
                    "state": "expired",
                    "expiry_reason": _("Expired by controlled action"),
                }
            )
        return True

    def action_archive(self):
        require_document_manager(self.env)
        self.with_context(
            onehr_document_version_state_action=True
        ).write({"state": "archived"})
        return True

    def action_create_successor(self):
        self.ensure_one()
        require_document_officer(self.env)
        new_version = self.env["onehr.document.version"].create(
            {
                "document_id": self.document_id.id,
                "version": max(
                    self.document_id.version_ids.mapped("version") or [0]
                )
                + 1,
                "effective_from": fields.Date.context_today(self),
            }
        )
        if self.state not in ("archived", "superseded"):
            self.with_context(
                onehr_document_version_state_action=True
            ).write({"state": "superseded"})
        return open_record_action(
            name=new_version.display_name,
            res_model=self._name,
            res_id=new_version.id,
        )

    def action_print_pdf(self):
        self.ensure_one()
        self.check_access("read")
        return self.env.ref(
            "onehr_document.action_report_document_version"
        ).report_action(self)

    def action_store_pdf_snapshot(self):
        """Render the approved QWeb report and preserve the PDF on this version."""
        self.ensure_one()
        require_document_officer(self.env)
        if self.state != "draft":
            raise UserError(
                _("A PDF snapshot may only be stored while the version is Draft.")
            )
        pdf_content, report_type = self.env[
            "ir.actions.report"
        ]._render_qweb_pdf(
            "onehr_document.action_report_document_version",
            self.ids,
        )
        if report_type != "pdf":
            raise UserError(
                _(
                    "PDF rendering is unavailable in the current runtime mode. "
                    "Use Print PDF after normal server startup."
                )
            )
        file_name = (
            self.file_name
            or f"{self.document_id.document_number}-V{self.version}.pdf"
        )
        checksum = hashlib.sha256(pdf_content).hexdigest()
        self.write(
            {
                "file_data": base64.b64encode(pdf_content),
                "file_name": file_name,
                "mimetype": "application/pdf",
                "file_checksum": checksum,
            }
        )
        return True

    def action_schedule_expiry_reminder(self):
        require_document_officer(self.env)
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for record in self:
            if not record.expiry_date:
                raise UserError(
                    _(
                        "An Expiry Date is required before scheduling an "
                        "expiry reminder."
                    )
                )
            if record.reminder_activity_id:
                continue
            deadline = record.reminder_date or record.expiry_date
            activity = self.env["mail.activity"].create(
                {
                    "activity_type_id": activity_type.id,
                    "summary": _(
                        "Document expiry: %s",
                        record.document_id.name,
                    ),
                    "note": _(
                        "Review document version %s before expiry.",
                        record.display_name,
                    ),
                    "date_deadline": deadline,
                    "user_id": record.responsible_user_id.id,
                    "res_model_id": self.env["ir.model"]._get_id(self._name),
                    "res_id": record.id,
                }
            )
            record.reminder_activity_id = activity
            record.last_reminder_at = fields.Datetime.now()
        return True

    def action_open_document(self):
        self.ensure_one()
        return open_record_action(
            name=self.document_id.display_name,
            res_model="onehr.document",
            res_id=self.document_id.id,
        )

    def action_open_esign_transactions(self):
        self.ensure_one()
        require_document_officer_or_compliance(self.env)
        return open_records_action(
            name=_("E-Sign Transactions — %s", self.display_name),
            res_model="onehr.esign.transaction",
            domain=[("document_version_id", "=", self.id)],
            context={"default_document_version_id": self.id},
        )

    @api.model
    def _cron_process_expiry_and_reminders(self):
        """Daily governance job: remind, then mark definitively expired evidence."""
        today = fields.Date.context_today(self)
        due = self.search(
            [
                ("expiry_date", "!=", False),
                (
                    "state",
                    "in",
                    ["issued", "signature_pending", "signed"],
                ),
            ]
        )
        for record in due:
            if (
                record.reminder_date
                and record.reminder_date <= today <= record.expiry_date
                and not record.reminder_activity_id
            ):
                record.action_schedule_expiry_reminder()
            if record.grace_end_date and today > record.grace_end_date:
                record.with_context(
                    onehr_document_version_state_action=True
                ).write(
                    {
                        "state": "expired",
                        "expiry_reason": _(
                            "Automatically expired after grace period"
                        ),
                    }
                )
        return True
