
import base64
import hashlib
import html
import io
import re
import zipfile
from datetime import timedelta
from xml.etree import ElementTree

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    require_jd_approver,
    require_jd_editor,
)


class OneHRJobDescriptionVersion(models.Model):
    _name = "onehr.jd.version"
    _description = "OneHR Job Description Version"
    _inherit = ["onehr.mixin.audit"]
    _order = "jd_id, version_no desc"

    _jd_version_number_uniq = models.Constraint(
        "UNIQUE(jd_id, version_no)",
        "Version number must be unique inside one Job Description.",
    )

    _ACTION_CONTEXT = "onehr_jd_version_action_write"

    jd_id = fields.Many2one(
        "onehr.jd",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="jd_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    name = fields.Char(
        compute="_compute_name",
        store=True,
        string="Version Reference",
        index=True,
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
        ],
        default="draft",
        required=True,
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

    position_code = fields.Char(
        related="jd_id.position_code",
        store=True,
        readonly=True,
        index=True,
    )
    position_name = fields.Char(
        related="jd_id.position_name",
        store=True,
        readonly=True,
        index=True,
    )
    job_name = fields.Char(
        related="jd_id.job_name",
        store=True,
        readonly=True,
        index=True,
    )
    department_name = fields.Char(
        related="jd_id.department_name",
        store=True,
        readonly=True,
        index=True,
    )
    job_family_name = fields.Char(
        related="jd_id.job_family_name",
        store=True,
        readonly=True,
        index=True,
    )
    is_template = fields.Boolean(
        related="jd_id.is_template",
        store=True,
        readonly=True,
        index=True,
    )

    effective_from = fields.Date(
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    effective_to = fields.Date(
        tracking=True,
        index=True,
    )
    review_due_date = fields.Date(
        default=lambda self: fields.Date.context_today(self) + timedelta(days=365),
        tracking=True,
        index=True,
    )

    purpose = fields.Html(
        string="Position Purpose",
        tracking=True,
    )
    key_responsibilities = fields.Html(
        string="Key Responsibilities",
        tracking=True,
    )
    kpi_expectations = fields.Html(
        string="KPI / Performance Expectations",
        tracking=True,
    )
    kpi_codes = fields.Text(
        string="KPI Codes / References",
        tracking=True,
    )
    competency_requirements = fields.Html(
        string="Competency Requirements",
        tracking=True,
    )
    competency_codes = fields.Text(
        string="Competency Codes / References",
        tracking=True,
    )
    qualification_requirements = fields.Html(
        string="Qualifications",
        tracking=True,
    )
    education_requirements = fields.Html(
        string="Education Requirements",
        tracking=True,
    )
    experience_requirements = fields.Html(
        string="Experience Requirements",
        tracking=True,
    )
    skills_requirements = fields.Html(
        string="Skills / Knowledge",
        tracking=True,
    )
    authority_scope = fields.Html(
        string="Authority / Decision Rights",
        tracking=True,
    )
    accountability = fields.Html(
        string="Accountabilities",
        tracking=True,
    )
    reporting_relationships = fields.Html(
        string="Reporting / Stakeholder Relationships",
        tracking=True,
    )
    working_conditions = fields.Html(
        string="Working Conditions",
        tracking=True,
    )

    hse_risk_level = fields.Selection(
        [
            ("none", "No Material HSE Risk"),
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="none",
        required=True,
        tracking=True,
        index=True,
        string="HSE / K3 Risk Level",
    )
    hse_risks = fields.Html(
        string="HSE / K3 Risks",
        tracking=True,
    )
    hse_controls = fields.Html(
        string="Required HSE / K3 Controls",
        tracking=True,
    )
    ppe_requirements = fields.Html(
        string="PPE Requirements",
        tracking=True,
    )

    source_file = fields.Binary(
        attachment=True,
        copy=False,
        string="External Source Document",
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    source_filename = fields.Char(
        copy=False,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    source_document_text = fields.Text(
        copy=False,
        readonly=True,
        groups="onehr_job_description.group_onehr_jd_editor",
        help="Text extracted from supported source documents for controlled manual migration.",
    )
    source_imported_at = fields.Datetime(
        copy=False,
        readonly=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_jd_version_attachment_rel",
        "version_id",
        "attachment_id",
        string="Supporting Evidence",
        copy=False,
        groups="onehr_job_description.group_onehr_jd_editor",
    )

    change_summary = fields.Text(
        tracking=True,
        help="Required for version 2 and later.",
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    change_reason = fields.Text(
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    reviewer_comments = fields.Html(
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    approval_comments = fields.Html(
        tracking=True,
        groups="onehr_job_description.group_onehr_jd_approver",
    )

    submitted_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        tracking=True,
    )
    submitted_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    published_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        tracking=True,
    )
    published_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    content_fingerprint = fields.Char(
        readonly=True,
        copy=False,
        index=True,
        help="SHA-256 evidence fingerprint captured on approval/publication.",
    )

    previous_version_id = fields.Many2one(
        "onehr.jd.version",
        compute="_compute_previous_version",
        store=True,
        readonly=True,
        groups="onehr_job_description.group_onehr_jd_editor",
    )
    completeness_percent = fields.Float(
        compute="_compute_completeness",
        store=True,
        string="Content Completeness %",
    )

    _CONTENT_FIELDS = {
        "effective_from",
        "effective_to",
        "review_due_date",
        "purpose",
        "key_responsibilities",
        "kpi_expectations",
        "kpi_codes",
        "competency_requirements",
        "competency_codes",
        "qualification_requirements",
        "education_requirements",
        "experience_requirements",
        "skills_requirements",
        "authority_scope",
        "accountability",
        "reporting_relationships",
        "working_conditions",
        "hse_risk_level",
        "hse_risks",
        "hse_controls",
        "ppe_requirements",
        "change_summary",
        "change_reason",
        "source_file",
        "source_filename",
        "source_document_text",
        "evidence_attachment_ids",
    }
    _LIFECYCLE_FIELDS = {
        "state",
        "is_current",
        "submitted_by_id",
        "submitted_at",
        "approved_by_id",
        "approved_at",
        "published_by_id",
        "published_at",
        "content_fingerprint",
    }

    @api.depends("jd_id.code", "version_no")
    def _compute_name(self):
        for record in self:
            record.name = (
                _("%s / V%s") % (record.jd_id.code, record.version_no)
                if record.jd_id and record.version_no
                else _("JD Version")
            )

    @api.depends("jd_id.version_ids.version_no", "version_no")
    def _compute_previous_version(self):
        for record in self:
            earlier = record.jd_id.version_ids.filtered(
                lambda version: version.version_no < record.version_no
            )
            record.previous_version_id = (
                earlier.sorted("version_no")[-1:] if earlier else False
            )

    @api.depends(
        "purpose",
        "key_responsibilities",
        "kpi_expectations",
        "competency_requirements",
        "qualification_requirements",
        "authority_scope",
        "working_conditions",
        "hse_risk_level",
        "hse_risks",
        "hse_controls",
    )
    def _compute_completeness(self):
        for record in self:
            checks = [
                bool(record.purpose),
                bool(record.key_responsibilities),
                bool(record.kpi_expectations),
                bool(record.competency_requirements),
                bool(record.qualification_requirements),
                bool(record.authority_scope),
                bool(record.working_conditions),
                bool(record.hse_risk_level),
            ]
            if record.hse_risk_level in ("medium", "high", "critical"):
                checks.extend(
                    [
                        bool(record.hse_risks),
                        bool(record.hse_controls),
                    ]
                )
            record.completeness_percent = (
                sum(checks) * 100.0 / len(checks)
                if checks
                else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_jd_editor(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            jd = self.env["onehr.jd"].browse(vals.get("jd_id"))
            if not jd:
                raise ValidationError(_("Job Description master is required."))

            in_flight = jd.version_ids.filtered(
                lambda version: version.state in ("draft", "review", "approved")
            )
            if in_flight:
                raise UserError(
                    _("Only one in-flight Draft/Review/Approved version is allowed per JD.")
                )

            if not vals.get("version_no"):
                vals["version_no"] = max(
                    jd.version_ids.mapped("version_no") or [0]
                ) + 1
            vals["state"] = "draft"
            vals["is_current"] = False
            prepared.append(vals)

        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)

        require_jd_editor(self)

        if self._LIFECYCLE_FIELDS.intersection(vals):
            raise AccessError(
                _("JD lifecycle evidence can change only through governed actions.")
            )

        for record in self:
            if (
                record.state in ("review", "approved", "published")
                and self._CONTENT_FIELDS.intersection(vals)
            ):
                raise AccessError(
                    _(
                        "Submitted/approved/published JD content is locked. "
                        "Return it to Draft or create a new version."
                    )
                )
        return super().write(vals)

    @api.constrains("effective_from", "effective_to", "review_due_date")
    def _check_effective_dates(self):
        for record in self:
            if (
                record.effective_from
                and record.effective_to
                and record.effective_to < record.effective_from
            ):
                raise ValidationError(
                    _("Effective To cannot be earlier than Effective From.")
                )
            if (
                record.review_due_date
                and record.effective_from
                and record.review_due_date < record.effective_from
            ):
                raise ValidationError(
                    _("Review Due Date cannot be earlier than Effective From.")
                )

    @api.constrains("is_current", "state", "jd_id")
    def _check_single_current_version(self):
        for record in self.filtered("is_current"):
            if record.state != "published":
                raise ValidationError(
                    _("Only a Published JD version can be the current version.")
                )
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("jd_id", "=", record.jd_id.id),
                    ("is_current", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Only one current published version is allowed per Job Description.")
                )

    def _write_lifecycle(self, values):
        return self.with_context(
            **{self._ACTION_CONTEXT: True}
        ).write(values)

    def _require_assigned_approver(self):
        self.mapped("jd_id")._require_assigned_approver()

    def _required_for_approval(self):
        self.ensure_one()
        missing = []
        requirements = [
            ("effective_from", _("Effective From")),
            ("review_due_date", _("Review Due Date")),
            ("purpose", _("Position Purpose")),
            ("key_responsibilities", _("Key Responsibilities")),
            ("kpi_expectations", _("KPI / Performance Expectations")),
            ("competency_requirements", _("Competency Requirements")),
            ("qualification_requirements", _("Qualifications")),
            ("authority_scope", _("Authority / Decision Rights")),
            ("working_conditions", _("Working Conditions")),
        ]
        for field_name, label in requirements:
            if not self[field_name]:
                missing.append(label)

        if self.hse_risk_level in ("medium", "high", "critical"):
            if not self.hse_risks:
                missing.append(_("HSE / K3 Risks"))
            if not self.hse_controls:
                missing.append(_("Required HSE / K3 Controls"))

        if self.version_no > 1 and not self.change_summary:
            missing.append(_("Change Summary"))
        return missing

    def _fingerprint_payload(self):
        self.ensure_one()
        values = [
            self.jd_id.code or "",
            str(self.version_no),
            str(self.effective_from or ""),
            str(self.review_due_date or ""),
            self.purpose or "",
            self.key_responsibilities or "",
            self.kpi_expectations or "",
            self.kpi_codes or "",
            self.competency_requirements or "",
            self.competency_codes or "",
            self.qualification_requirements or "",
            self.education_requirements or "",
            self.experience_requirements or "",
            self.skills_requirements or "",
            self.authority_scope or "",
            self.accountability or "",
            self.reporting_relationships or "",
            self.working_conditions or "",
            self.hse_risk_level or "",
            self.hse_risks or "",
            self.hse_controls or "",
            self.ppe_requirements or "",
            self.change_summary or "",
            self.change_reason or "",
        ]
        return "\n---\n".join(values).encode("utf-8")

    def _calculate_content_fingerprint(self):
        self.ensure_one()
        return hashlib.sha256(self._fingerprint_payload()).hexdigest()

    def _copy_content_values(self):
        self.ensure_one()
        field_names = [
            "purpose",
            "key_responsibilities",
            "kpi_expectations",
            "kpi_codes",
            "competency_requirements",
            "competency_codes",
            "qualification_requirements",
            "education_requirements",
            "experience_requirements",
            "skills_requirements",
            "authority_scope",
            "accountability",
            "reporting_relationships",
            "working_conditions",
            "hse_risk_level",
            "hse_risks",
            "hse_controls",
            "ppe_requirements",
        ]
        return {
            field_name: self[field_name]
            for field_name in field_names
        }

    def action_submit_review(self):
        require_jd_editor(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft JD versions can be submitted for review."))
            if record.completeness_percent < 75.0:
                raise UserError(
                    _("JD content must be at least 75%% complete before Review.")
                )
            if record.version_no > 1 and not record.change_summary:
                raise UserError(_("Change Summary is required for version 2 and later."))
            record._write_lifecycle(
                {
                    "state": "review",
                    "submitted_by_id": self.env.user.id,
                    "submitted_at": fields.Datetime.now(),
                    "approved_by_id": False,
                    "approved_at": False,
                    "published_by_id": False,
                    "published_at": False,
                    "content_fingerprint": False,
                }
            )
        return display_notification(_("Job Description submitted for Review."))

    def action_return_draft(self):
        require_jd_approver(self)
        self._require_assigned_approver()
        for record in self:
            if record.state not in ("review", "approved"):
                raise UserError(_("Only Review/Approved versions can return to Draft."))
            record._write_lifecycle(
                {
                    "state": "draft",
                    "approved_by_id": False,
                    "approved_at": False,
                    "published_by_id": False,
                    "published_at": False,
                    "content_fingerprint": False,
                }
            )
        return display_notification(
            _("Job Description returned to Draft."),
            notification_type="warning",
        )

    def action_approve(self):
        require_jd_approver(self)
        self._require_assigned_approver()
        for record in self:
            if record.state != "review":
                raise UserError(_("Only Review JD versions can be approved."))
            missing = record._required_for_approval()
            if missing:
                raise UserError(
                    _("Approval blocked. Complete: %s") % ", ".join(missing)
                )
            fingerprint = record._calculate_content_fingerprint()
            record._write_lifecycle(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_at": fields.Datetime.now(),
                    "content_fingerprint": fingerprint,
                }
            )
        return display_notification(_("Job Description approved."))

    def action_publish(self):
        require_jd_approver(self)
        self._require_assigned_approver()
        today = fields.Date.context_today(self)

        for record in self:
            if record.state != "approved":
                raise UserError(_("Only Approved JD versions can be published."))

            fingerprint = record._calculate_content_fingerprint()
            if (
                record.content_fingerprint
                and record.content_fingerprint != fingerprint
            ):
                raise UserError(
                    _("JD content changed after approval; return to Draft and re-approve.")
                )

            effective_from = record.effective_from or today
            previous_current = record.jd_id.version_ids.filtered(
                lambda version: version.is_current and version.id != record.id
            )
            for previous in previous_current:
                previous_values = {"is_current": False}
                if previous.effective_from:
                    if effective_from > previous.effective_from:
                        if (
                            not previous.effective_to
                            or previous.effective_to >= effective_from
                        ):
                            previous_values["effective_to"] = (
                                effective_from - timedelta(days=1)
                            )
                    elif effective_from == previous.effective_from:
                        previous_values["effective_to"] = previous.effective_from
                previous._write_lifecycle(previous_values)

            review_due = record.review_due_date
            if not review_due:
                review_due = effective_from + timedelta(days=365)

            record._write_lifecycle(
                {
                    "state": "published",
                    "is_current": True,
                    "effective_from": effective_from,
                    "review_due_date": review_due,
                    "published_by_id": self.env.user.id,
                    "published_at": fields.Datetime.now(),
                    "content_fingerprint": fingerprint,
                }
            )
            record.jd_id._refresh_governance_metrics()

        return display_notification(_("Job Description published."))

    def action_open_version(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Job Description Version"),
            "res_model": "onehr.jd.version",
            "res_id": self.id,
            "view_mode": "form",
        }

    def action_open_master_jd(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Job Description"),
            "res_model": "onehr.jd",
            "res_id": self.jd_id.id,
            "view_mode": "form",
        }

    def action_open_previous_version(self):
        require_jd_editor(self)
        self.ensure_one()
        if not self.previous_version_id:
            raise UserError(_("This is the first JD version."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Previous JD Version"),
            "res_model": "onehr.jd.version",
            "res_id": self.previous_version_id.id,
            "view_mode": "form",
        }

    def action_print_jd(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_job_description.action_report_jd_document"
        ).report_action(self)

    def action_print_comparison(self):
        require_jd_editor(self)
        self.ensure_one()
        if not self.previous_version_id:
            raise UserError(_("A previous version is required for comparison."))
        return self.env.ref(
            "onehr_job_description.action_report_jd_comparison"
        ).report_action(self)

    def _extract_docx_text(self, raw_bytes):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            xml_bytes = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_bytes)
        paragraphs = []
        for paragraph in root.iter(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
        ):
            chunks = [
                node.text or ""
                for node in paragraph.iter(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                )
            ]
            text = "".join(chunks).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)

    def _extract_source_text(self, raw_bytes, filename):
        extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
        if extension == "docx":
            try:
                return self._extract_docx_text(raw_bytes)
            except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
                raise UserError(_("The DOCX source could not be read: %s") % exc) from exc

        if extension in ("txt", "md", "html", "htm"):
            text = raw_bytes.decode("utf-8", errors="replace")
            if extension in ("html", "htm"):
                text = re.sub(r"<[^>]+>", " ", text)
                text = html.unescape(text)
                text = re.sub(r"\s+", " ", text).strip()
            return text

        raise UserError(
            _(
                "Supported source formats are .txt, .md, .html/.htm and .docx. "
                "Other files may be attached as evidence without automatic extraction."
            )
        )

    def action_import_source_document(self):
        require_jd_editor(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Source documents can be imported only into Draft versions."))
            if not record.source_file or not record.source_filename:
                raise UserError(_("Attach an External Source Document first."))

            try:
                raw_bytes = base64.b64decode(record.source_file)
            except Exception as exc:
                raise UserError(_("The uploaded source document is not valid binary data.")) from exc

            extracted = record._extract_source_text(
                raw_bytes,
                record.source_filename,
            )
            if not extracted.strip():
                raise UserError(_("No readable text was extracted from the source document."))

            record.write(
                {
                    "source_document_text": extracted,
                    "source_imported_at": fields.Datetime.now(),
                }
            )
        return display_notification(_("External JD source text imported for controlled review."))

    def action_refresh_competency_snapshot(self):
        require_jd_editor(self)
        refreshed = 0
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _("Competency snapshots can be refreshed only in Draft versions.")
                )
            if record.jd_id.is_template:
                raise UserError(
                    _("Position competency refresh is available on position JDs, not templates.")
                )
            if not self.env.registry.get("onehr.position.competency"):
                return display_notification(
                    _("OneHR Career & Succession is not installed; existing snapshot was preserved."),
                    notification_type="warning",
                )

            requirements = self.env["onehr.position.competency"].search(
                [
                    ("position_id", "=", record.jd_id.position_id.id),
                    ("active", "=", True),
                ],
                order="sequence, competency_id",
            )
            codes = []
            items = []
            for requirement in requirements:
                competency = requirement.competency_id
                codes.append(competency.code)
                evidence = requirement.behavioral_evidence or ""
                label = (
                    f"[{competency.code}] {competency.name} — "
                    f"Level {requirement.required_level}"
                )
                if requirement.mandatory:
                    label += " — Mandatory"
                if evidence:
                    label += f" — {evidence}"
                items.append(f"<li>{html.escape(label)}</li>")

            record.write(
                {
                    "competency_codes": ", ".join(codes),
                    "competency_requirements": (
                        "<ul>" + "".join(items) + "</ul>"
                        if items
                        else "<p>No active position competency requirements.</p>"
                    ),
                }
            )
            refreshed += 1

        return display_notification(
            _("%s JD competency snapshot(s) refreshed.") % refreshed
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unapproved(self):
        for record in self:
            if record.state in ("approved", "published"):
                raise UserError(
                    _("Approved/published JD history must be retained, not deleted.")
                )

