import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..models.action_helpers import (
    open_record_action,
    require_document_officer,
    source_record_from_pair,
)


def _safe_filename(value):
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned[:180] or "onehr-document.pdf"


class WizardDocumentGenerate(models.TransientModel):
    _name = "wizard.document.generate"
    _description = "Generate OneHR Document"

    document_id = fields.Many2one("onehr.document", ondelete="cascade")
    template_id = fields.Many2one(
        "onehr.document.template",
        required=True,
        ondelete="cascade",
    )
    template_version_id = fields.Many2one(
        "onehr.document.template.version",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one("hr.employee", ondelete="cascade")
    category_id = fields.Many2one(
        "onehr.document.category",
        required=True,
        ondelete="cascade",
    )
    source_model_id = fields.Many2one("ir.model", ondelete="cascade")
    source_res_id = fields.Integer(string="Source Record ID")
    document_name = fields.Char(required=True)
    effective_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    effective_to = fields.Date()
    expiry_date = fields.Date()
    preview_subject = fields.Char(readonly=True)
    preview_html = fields.Html(readonly=True, sanitize=True)
    preview_filename = fields.Char(readonly=True)

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        today = fields.Date.context_today(self)
        versions = self.template_id.version_ids.filtered(
            lambda row: row.state == "active" and row.is_effective_on(today)
        ).sorted(lambda row: (row.version, row.id), reverse=True)
        self.template_version_id = versions[:1]
        self.category_id = self.template_id.category_id
        self.company_id = self.template_id.company_id or self.env.company
        self.document_name = self.template_id.name
        if (
            self.category_id.default_validity_days
            and not self.expiry_date
        ):
            self.expiry_date = today + timedelta(
                days=self.category_id.default_validity_days
            )

    @api.onchange("document_id")
    def _onchange_document_id(self):
        if self.document_id:
            self.company_id = self.document_id.company_id
            self.employee_id = self.document_id.employee_id
            self.category_id = self.document_id.category_id
            if self.document_id.template_id:
                self.template_id = self.document_id.template_id
            self.document_name = self.document_id.name
            self.source_model_id = self.document_id.source_model_id
            self.source_res_id = self.document_id.source_res_id

    def _validate_scope(self):
        self.ensure_one()
        require_document_officer(self.env)

        if self.template_version_id.template_id != self.template_id:
            raise ValidationError(
                _(
                    "Template Version must belong to the selected Template."
                )
            )
        if (
            self.template_version_id.state != "active"
            or not self.template_version_id.is_effective_on(
                self.effective_from
            )
        ):
            raise ValidationError(
                _(
                    "Template Version must be active and effective on the "
                    "generation date."
                )
            )
        if self.category_id != self.template_id.category_id:
            raise ValidationError(
                _(
                    "Document category must match the governing template "
                    "category."
                )
            )
        if (
            not self.template_id.active
            or not self.template_id.is_effective_on(self.effective_from)
        ):
            raise ValidationError(
                _("The Template must be active and effective on the generation date.")
            )
        if (
            not self.category_id.active
            or not self.category_id.is_effective_on(self.effective_from)
        ):
            raise ValidationError(
                _("The Document Category must be active and effective on the generation date.")
            )

        template_company = self.template_id.company_id
        if template_company and template_company != self.company_id:
            raise ValidationError(
                _("The selected template is not available in this company.")
            )
        if (
            self.employee_id
            and self.employee_id.company_id != self.company_id
        ):
            raise ValidationError(
                _(
                    "Employee and document company must match at "
                    "generation time."
                )
            )

        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(_("Effective To must be on or after Effective From."))
        if self.expiry_date and self.expiry_date < self.effective_from:
            raise ValidationError(_("Expiry Date cannot be before Effective From."))

        if self.document_id:
            if self.document_id.category_id != self.category_id or self.document_id.company_id != self.company_id:
                raise ValidationError(_("Existing document scope does not match the generation request."))
            if self.document_id.template_id and self.document_id.template_id != self.template_id:
                raise ValidationError(_("Existing document is governed by a different Template."))
            if self.document_id.version_ids and not self.document_id.template_id:
                raise ValidationError(
                    _("A document that already has versions cannot be retroactively bound to a Template. Generate a new logical document instead.")
                )
            if not self.document_id.is_effective_on(self.effective_from):
                raise ValidationError(_("Generation date must fall inside the logical document validity."))
            if self.document_id.valid_to and (not self.effective_to or self.effective_to > self.document_id.valid_to):
                raise ValidationError(_("Generated version validity must remain inside the logical document validity."))

        source_record_from_pair(
            self.env,
            self.source_model_id,
            self.source_res_id,
            require_read=True,
        )
        return True

    def _render_values(self, document=None):
        self.ensure_one()
        source = source_record_from_pair(
            self.env,
            self.source_model_id,
            self.source_res_id,
            require_read=True,
        )
        return {
            "employee.name": self.employee_id.name or "",
            "employee.onehr_employee_number": (
                self.employee_id.onehr_employee_number or ""
            ),
            "employee.work_email": self.employee_id.work_email or "",
            "company.name": self.company_id.name or "",
            "category.name": self.category_id.name or "",
            "source.display_name": (
                source.display_name
                if source and source._name != "ir.model"
                else ""
            ),
            "current_date": fields.Date.context_today(self),
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "expiry_date": self.expiry_date,
            "document.name": (
                document.name if document else self.document_name
            ),
            "document.number": (
                document.document_number if document else ""
            ),
        }

    def action_preview(self):
        self.ensure_one()
        self._validate_scope()
        rendered = self.template_version_id.render_contract(
            self._render_values()
        )
        self.write(
            {
                "preview_subject": rendered["subject"],
                "preview_html": rendered["body_html"],
                "preview_filename": _safe_filename(
                    rendered["filename"]
                ),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Document Preview"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_generate(self):
        self.ensure_one()
        self._validate_scope()

        document = self.document_id
        if not document:
            document = self.env["onehr.document"].create(
                {
                    "name": self.document_name,
                    "category_id": self.category_id.id,
                    "company_id": self.company_id.id,
                    "employee_id": self.employee_id.id,
                    "source_model_id": self.source_model_id.id,
                    "source_res_id": self.source_res_id,
                    "template_id": self.template_id.id,
                    "valid_from": self.effective_from,
                    "valid_to": self.effective_to,
                }
            )
        elif (
            document.category_id != self.category_id
            or document.company_id != self.company_id
        ):
            raise ValidationError(
                _(
                    "Existing document scope does not match the generation "
                    "request."
                )
            )

        if document and not document.template_id:
            # Binding is allowed only before the first version exists; _validate_scope
            # rejects retroactive rebinding of historical upload-only documents.
            document.write({"template_id": self.template_id.id})

        rendered = self.template_version_id.render_contract(
            self._render_values(document=document)
        )
        latest_version = max(
            document.version_ids.mapped("version") or [0]
        )
        version = self.env["onehr.document.version"].create(
            {
                "document_id": document.id,
                "version": latest_version + 1,
                "template_version_id": self.template_version_id.id,
                "effective_from": self.effective_from,
                "effective_to": self.effective_to,
                "expiry_date": self.expiry_date,
                "rendered_subject": rendered["subject"],
                "rendered_content_html": rendered["body_html"],
                "file_name": _safe_filename(rendered["filename"]),
                "mimetype": "application/pdf",
            }
        )

        # Runtime PDF rendering is deliberately separate from business
        # generation so post-install tests do not depend on wkhtmltopdf.
        if not self.env.context.get("onehr_document_skip_pdf_render"):
            version.action_store_pdf_snapshot()

        return open_record_action(
            name=version.display_name,
            res_model="onehr.document.version",
            res_id=version.id,
        )
