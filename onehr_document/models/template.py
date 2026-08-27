import hashlib
import re
from datetime import date

from markupsafe import escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import (
    open_record_action,
    open_records_action,
    require_document_manager,
)


TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")

ALLOWED_TEMPLATE_TOKENS = {
    "employee.name",
    "employee.onehr_employee_number",
    "employee.work_email",
    "company.name",
    "category.name",
    "source.display_name",
    "current_date",
    "effective_from",
    "effective_to",
    "expiry_date",
    "document.name",
    "document.number",
}


def _extract_tokens(text):
    return sorted(set(TOKEN_RE.findall(text or "")))


def _safe_value(value):
    if value in (None, False):
        return ""
    if isinstance(value, date):
        return fields.Date.to_string(value)
    return str(value)


def _render_restricted_tokens(text, values):
    """Render a deliberately bounded Jinja-like variable contract.

    Stored templates are content, not executable code. Unknown variables are a
    hard error and every substituted value is HTML-escaped.
    """
    unknown = set(_extract_tokens(text)) - set(values)
    if unknown:
        raise ValidationError(
            _("Unknown or unavailable document template variables: %s", ", ".join(sorted(unknown)))
        )

    def replace(match):
        return str(escape(_safe_value(values.get(match.group(1)))))

    return TOKEN_RE.sub(replace, text or "")


class OneHRDocumentTemplate(models.Model):
    _name = "onehr.document.template"
    _description = "OneHR Document Template"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    description = fields.Text(translate=True)
    category_id = fields.Many2one(
        "onehr.document.category",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        index=True,
        ondelete="restrict",
        tracking=True,
        help="Leave empty only for a deliberately shared template.",
    )
    active = fields.Boolean(default=True, tracking=True)
    version_ids = fields.One2many(
        "onehr.document.template.version",
        "template_id",
        string="Template Versions",
    )
    version_count = fields.Integer(compute="_compute_counts", string="Versions")
    generated_document_count = fields.Integer(
        compute="_compute_counts",
        string="Generated Documents",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_document_manager(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            vals["code"] = (vals.get("code") or "").strip().upper()
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        require_document_manager(self.env)
        values = dict(vals)
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        if any(record.version_ids.filtered(lambda row: row.state == "active") for record in self):
            protected = {"category_id", "company_id", "valid_from"}
            if protected & set(values):
                raise AccessError(
                    _("Template identity cannot be rewritten after a version has been activated. Create a new template when the governing identity changes.")
                )
        return super().write(values)

    @api.constrains("code", "company_id", "valid_from", "valid_to", "active")
    def _check_unique_effective_template(self):
        for record in self.filtered("active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("active", "=", True)],
                _("Active document-template validity cannot overlap for the same code and company scope."),
            )

    @api.constrains("category_id", "company_id")
    def _check_category_scope(self):
        for record in self:
            if record.category_id.company_id and record.category_id.company_id != record.company_id:
                raise ValidationError(
                    _("A company-specific template must use a category from the same company scope.")
                )

    def _compute_counts(self):
        Document = self.env["onehr.document"]
        for record in self:
            record.version_count = len(record.version_ids)
            record.generated_document_count = Document.search_count(
                [("template_id", "=", record.id)]
            )

    def action_create_version(self):
        self.ensure_one()
        require_document_manager(self.env)
        latest = self.version_ids.sorted(lambda item: (item.version, item.id), reverse=True)[:1]
        values = {
            "template_id": self.id,
            "version": (latest.version if latest else 0) + 1,
            "state": "draft",
            "valid_from": fields.Date.context_today(self),
        }
        if latest:
            values.update(
                {
                    "subject_template": latest.subject_template,
                    "body_html": latest.body_html,
                    "filename_template": latest.filename_template,
                }
            )
        version = self.env["onehr.document.template.version"].create(values)
        return open_record_action(
            name=_("Template Version %s", version.version),
            res_model=version._name,
            res_id=version.id,
        )

    def action_open_versions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Template Versions — %s", self.display_name),
            res_model="onehr.document.template.version",
            domain=[("template_id", "=", self.id)],
            context={"default_template_id": self.id},
        )

    def action_open_generated_documents(self):
        self.ensure_one()
        return open_records_action(
            name=_("Generated Documents — %s", self.display_name),
            res_model="onehr.document",
            domain=[("template_id", "=", self.id)],
        )


class OneHRDocumentTemplateVersion(models.Model):
    _name = "onehr.document.template.version"
    _description = "OneHR Document Template Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "template_id, version desc, id desc"

    _unique_template_version = models.UniqueIndex("(template_id, version)")

    template_id = fields.Many2one(
        "onehr.document.template",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    version = fields.Integer(required=True, default=1, tracking=True)
    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        related="template_id.company_id",
        store=True,
        index=True,
    )
    category_id = fields.Many2one(
        related="template_id.category_id",
        store=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("retired", "Retired"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    subject_template = fields.Char(
        required=True,
        default="{{ employee.name }}",
        tracking=True,
        help="Restricted variable placeholders use {{ token }} syntax.",
    )
    body_html = fields.Html(
        required=True,
        sanitize=True,
        tracking=True,
        default="<p>Document for {{ employee.name }}</p>",
    )
    filename_template = fields.Char(
        default="{{ employee.onehr_employee_number }}-document.pdf",
        tracking=True,
    )
    variable_contract = fields.Char(
        compute="_compute_variable_contract",
        store=True,
        help="Detected variables. The engine rejects variables outside the approved contract.",
    )
    content_checksum = fields.Char(
        compute="_compute_content_checksum",
        store=True,
        readonly=True,
    )
    generated_version_count = fields.Integer(
        compute="_compute_generated_version_count",
        string="Generated Versions",
    )

    @api.depends("template_id.name", "version")
    def _compute_name(self):
        for record in self:
            record.name = _("%s / Version %s", record.template_id.name, record.version)

    @api.depends("subject_template", "body_html", "filename_template")
    def _compute_variable_contract(self):
        for record in self:
            tokens = set()
            for value in (
                record.subject_template,
                record.body_html,
                record.filename_template,
            ):
                tokens.update(_extract_tokens(value))
            record.variable_contract = ", ".join(sorted(tokens))

    @api.depends("subject_template", "body_html", "filename_template")
    def _compute_content_checksum(self):
        for record in self:
            payload = "\n".join(
                [
                    record.subject_template or "",
                    str(record.body_html or ""),
                    record.filename_template or "",
                ]
            )
            record.content_checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _compute_generated_version_count(self):
        Version = self.env["onehr.document.version"]
        for record in self:
            record.generated_version_count = Version.search_count(
                [("template_version_id", "=", record.id)]
            )

    @api.constrains("template_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("template_id", "=", record.template_id.id),
                    ("version", "=", record.version),
                ],
                limit=1,
            ):
                raise ValidationError(_("Template version number must be unique per template."))

    @api.constrains("template_id", "valid_from", "valid_to", "state")
    def _check_active_overlap(self):
        for record in self.filtered(lambda item: item.state == "active"):
            record._check_no_effective_overlap(
                ["template_id"],
                [("state", "=", "active")],
                _("Active template-version validity cannot overlap."),
            )

    def _validate_variable_contract(self):
        for record in self:
            tokens = set()
            for value in (record.subject_template, record.body_html, record.filename_template):
                tokens.update(_extract_tokens(value))
            unknown = tokens - ALLOWED_TEMPLATE_TOKENS
            if unknown:
                raise ValidationError(
                    _("Unsupported document template variables: %s", ", ".join(sorted(unknown)))
                )
        return True

    def action_activate(self):
        require_document_manager(self.env)
        self._validate_variable_contract()
        self.with_context(onehr_template_state_action=True).write({"state": "active"})
        return True

    def action_retire(self):
        require_document_manager(self.env)
        self.with_context(onehr_template_state_action=True).write({"state": "retired"})
        return True

    def action_create_successor(self):
        self.ensure_one()
        require_document_manager(self.env)
        return self.template_id.action_create_version()

    def write(self, vals):
        require_document_manager(self.env)
        frozen_fields = {
            "template_id",
            "version",
            "subject_template",
            "body_html",
            "filename_template",
            "valid_from",
        }
        if frozen_fields & set(vals) and any(record.state != "draft" for record in self):
            raise AccessError(
                _("Activated or retired template versions are immutable. Create a successor version instead.")
            )
        if "state" in vals and not self.env.context.get("onehr_template_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use the controlled template-version actions to change state."))
        return super().write(vals)

    def action_open_template(self):
        self.ensure_one()
        return open_record_action(
            name=self.template_id.display_name,
            res_model="onehr.document.template",
            res_id=self.template_id.id,
        )

    def action_open_generated_versions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Generated Document Versions — %s", self.display_name),
            res_model="onehr.document.version",
            domain=[("template_version_id", "=", self.id)],
        )

    def render_contract(self, values):
        """Return subject/body/filename after bounded token substitution."""
        self.ensure_one()
        self._validate_variable_contract()
        return {
            "subject": _render_restricted_tokens(self.subject_template, values),
            "body_html": _render_restricted_tokens(str(self.body_html or ""), values),
            "filename": _render_restricted_tokens(self.filename_template or "", values),
        }
