
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_pnp_compliance,
    open_record_action,
    require_pnp_compliance,
)


class OneHRPolicyEvidence(models.Model):
    _name = "onehr.policy.evidence"
    _description = "OneHR Policy Compliance Evidence"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, submitted_at desc, id desc"

    _ACTION_CONTEXT = "onehr_pnp_evidence_action"

    policy_id = fields.Many2one(
        "onehr.policy",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    ack_id = fields.Many2one(
        "onehr.policy.ack",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    evidence_scope = fields.Selection(
        [
            ("employee", "Employee"),
            ("unit", "Department / Unit"),
            ("policy", "Policy-wide"),
        ],
        required=True,
        default="employee",
        tracking=True,
        index=True,
    )
    unit_department_id = fields.Many2one(
        "hr.department",
        string="Evidence Department / Unit",
        ondelete="restrict",
        check_company=True,
        tracking=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    company_id = fields.Many2one(
        "res.company",
        related="policy_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    policy_code = fields.Char(
        related="policy_id.policy_code",
        store=True,
        readonly=True,
        index=True,
    )
    policy_title = fields.Char(
        related="policy_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        related="ack_id.employee_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    employee_number = fields.Char(
        related="ack_id.employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    employee_name = fields.Char(
        related="ack_id.employee_name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="ack_id.employee_user_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        compute="_compute_subject_department",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    department_name = fields.Char(
        related="department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_name = fields.Char(
        related="ack_id.job_name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    evidence_type = fields.Selection(
        [
            ("attachment", "File / Photo Attachment"),
            ("controlled_document", "Controlled OneHR Document"),
            ("url", "External Link"),
            ("note", "Compliance Note"),
        ],
        required=True,
        default="attachment",
        tracking=True,
        index=True,
    )
    title = fields.Char(
        required=True,
        tracking=True,
        index=True,
    )
    evidence_note = fields.Text(
        tracking=True,
    )
    reference_url = fields.Char(
        string="Evidence URL",
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_pnp_evidence_attachment_rel",
        "evidence_id",
        "attachment_id",
        string="Evidence Files / Photos",
        copy=False,
    )
    document_version_id = fields.Many2one(
        "onehr.document.version",
        string="Controlled Document Evidence",
        ondelete="restrict",
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
        index=True,
    )
    submitted_at = fields.Datetime(
        readonly=True,
        copy=False,
        index=True,
    )
    submitted_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
    )
    verified_at = fields.Datetime(
        readonly=True,
        copy=False,
        index=True,
    )
    verified_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    verification_comment = fields.Text(
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    rejection_reason = fields.Text(
        tracking=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    due_date = fields.Date(
        compute="_compute_due_date",
        store=True,
        readonly=True,
        index=True,
    )
    overdue = fields.Boolean(
        compute="_compute_overdue",
    )

    @api.depends(
        "evidence_scope",
        "ack_id.department_id",
        "unit_department_id",
    )
    def _compute_subject_department(self):
        for evidence in self:
            evidence.department_id = (
                evidence.unit_department_id
                if evidence.evidence_scope == "unit"
                else evidence.ack_id.department_id
            )

    @api.depends(
        "policy_id.published_at",
        "policy_id.evidence_due_days",
    )
    def _compute_due_date(self):
        for evidence in self:
            if evidence.policy_id.published_at:
                publish_date = fields.Datetime.to_datetime(
                    evidence.policy_id.published_at
                ).date()
                evidence.due_date = publish_date + timedelta(
                    days=evidence.policy_id.evidence_due_days
                )
            else:
                evidence.due_date = False

    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for evidence in self:
            evidence.overdue = bool(
                evidence.state not in ("verified",)
                and evidence.due_date
                and evidence.due_date < today
            )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            scope = vals.get("evidence_scope") or "employee"
            if (
                vals.get("evidence_type") == "controlled_document"
                and not is_pnp_compliance(self.env)
            ):
                raise AccessError(
                    _("Controlled OneHR Document evidence requires Compliance authority.")
                )

            ack = self.env["onehr.policy.ack"].browse(
                vals.get("ack_id")
            ).exists()
            policy = self.env["onehr.policy"].browse(
                vals.get("policy_id")
            ).exists()
            if not policy:
                raise ValidationError(_("Evidence requires a valid policy."))
            if policy.state not in ("published", "review") or not policy.is_current:
                raise UserError(
                    _("Evidence may be submitted only for the current Published/Review policy.")
                )

            if scope == "employee":
                if not ack or ack.policy_id != policy:
                    raise ValidationError(
                        _("Employee evidence requires a valid acknowledgement assignment for the same policy.")
                    )
                if vals.get("unit_department_id"):
                    raise ValidationError(
                        _("Employee evidence cannot also specify a Unit evidence department.")
                    )
                if not is_pnp_compliance(self.env):
                    if (
                        not ack.employee_user_id
                        or ack.employee_user_id != self.env.user
                    ):
                        raise AccessError(
                            _("You may create employee compliance evidence only for your own policy assignment.")
                        )
            elif scope == "unit":
                require_pnp_compliance(self)
                department = self.env["hr.department"].browse(
                    vals.get("unit_department_id")
                ).exists()
                if not department:
                    raise ValidationError(
                        _("Department / Unit evidence requires a valid department.")
                    )
                if department.company_id and department.company_id != policy.company_id:
                    raise ValidationError(
                        _("Evidence department and policy company must match.")
                    )
                vals["ack_id"] = False
            elif scope == "policy":
                require_pnp_compliance(self)
                vals["ack_id"] = False
                vals["unit_department_id"] = False
            else:
                raise ValidationError(_("Unsupported evidence scope."))

            vals["evidence_scope"] = scope
            vals["state"] = "draft"
            prepared.append(vals)

        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)

        requested = set(vals)
        if (
            vals.get("evidence_type") == "controlled_document"
            and not is_pnp_compliance(self.env)
        ):
            raise AccessError(
                _("Controlled OneHR Document evidence requires Compliance authority.")
            )

        content_fields = {
            "evidence_type",
            "title",
            "evidence_note",
            "reference_url",
            "attachment_ids",
            "document_version_id",
        }
        lifecycle_fields = {
            "policy_id",
            "ack_id",
            "evidence_scope",
            "unit_department_id",
            "state",
            "submitted_at",
            "submitted_by_id",
            "verified_at",
            "verified_by_id",
        }
        if lifecycle_fields.intersection(requested):
            raise AccessError(
                _("Evidence lifecycle fields change only through governed actions.")
            )

        for evidence in self:
            if is_pnp_compliance(self.env):
                if evidence.state in ("submitted", "verified") and content_fields.intersection(requested):
                    raise AccessError(
                        _("Submitted/verified evidence content is immutable. Reject it before correction.")
                    )
                continue

            if (
                evidence.evidence_scope != "employee"
                or not evidence.employee_user_id
                or evidence.employee_user_id != self.env.user
            ):
                raise AccessError(
                    _("You may update only your own employee-scoped policy evidence.")
                )
            if evidence.state not in ("draft", "rejected"):
                raise AccessError(
                    _("Only Draft or Rejected evidence may be edited by the employee.")
                )
            if requested - content_fields:
                raise AccessError(
                    _("Only evidence content fields may be edited by the employee.")
                )
        return super().write(vals)

    @api.constrains(
        "evidence_type",
        "attachment_ids",
        "document_version_id",
        "reference_url",
        "evidence_note",
    )
    def _check_evidence_payload(self):
        for evidence in self:
            if evidence.state == "draft":
                continue
            if evidence.evidence_type == "attachment" and not evidence.attachment_ids:
                raise ValidationError(
                    _("File / Photo evidence requires at least one attachment.")
                )
            if evidence.evidence_type == "controlled_document" and not evidence.document_version_id:
                raise ValidationError(
                    _("Controlled Document evidence requires a OneHR Document Version.")
                )
            if evidence.evidence_type == "url" and not evidence.reference_url:
                raise ValidationError(_("URL evidence requires an Evidence URL."))
            if evidence.evidence_type == "note" and not evidence.evidence_note:
                raise ValidationError(_("Compliance Note evidence requires a note."))

    def _write_action(self, values):
        return self.with_context(
            **{self._ACTION_CONTEXT: True}
        ).write(values)

    def action_submit(self):
        for evidence in self:
            if evidence.state not in ("draft", "rejected"):
                raise UserError(
                    _("Only Draft or Rejected evidence can be submitted.")
                )
            if not is_pnp_compliance(self.env):
                if (
                    evidence.evidence_scope != "employee"
                    or not evidence.employee_user_id
                    or evidence.employee_user_id != self.env.user
                ):
                    raise AccessError(
                        _("You may submit only your own compliance evidence.")
                    )

            evidence._write_action(
                {
                    "state": "submitted",
                    "submitted_at": fields.Datetime.now(),
                    "submitted_by_id": self.env.user.id,
                    "verified_at": False,
                    "verified_by_id": False,
                    "rejection_reason": False,
                }
            )
            evidence._check_evidence_payload()
        return display_notification(_("Compliance evidence submitted."))

    def action_verify(self):
        require_pnp_compliance(self)
        for evidence in self:
            if evidence.state != "submitted":
                raise UserError(_("Only Submitted evidence can be verified."))
            evidence._write_action(
                {
                    "state": "verified",
                    "verified_at": fields.Datetime.now(),
                    "verified_by_id": self.env.user.id,
                    "rejection_reason": False,
                }
            )
        return display_notification(_("Compliance evidence verified."))

    def action_reject(self):
        require_pnp_compliance(self)
        for evidence in self:
            if evidence.state != "submitted":
                raise UserError(_("Only Submitted evidence can be rejected."))
            if not evidence.rejection_reason:
                raise UserError(
                    _("Enter a Rejection Reason before rejecting evidence.")
                )
            evidence._write_action(
                {
                    "state": "rejected",
                    "verified_at": False,
                    "verified_by_id": False,
                }
            )
        return display_notification(
            _("Compliance evidence rejected for correction."),
            notification_type="warning",
        )

    def action_open_policy(self):
        self.ensure_one()
        return open_record_action(
            name=_("Policy / Procedure"),
            res_model="onehr.policy",
            res_id=self.policy_id.id,
        )

    def action_open_acknowledgement(self):
        self.ensure_one()
        if not self.ack_id:
            raise UserError(
                _("Unit/Policy-wide evidence has no employee acknowledgement assignment.")
            )
        return open_record_action(
            name=_("Policy Acknowledgement"),
            res_model="onehr.policy.ack",
            res_id=self.ack_id.id,
        )

    def action_open_document(self):
        require_pnp_compliance(self)
        self.ensure_one()
        if not self.document_version_id:
            raise UserError(_("No controlled OneHR Document Version is linked."))
        return open_record_action(
            name=_("Controlled Evidence Document"),
            res_model="onehr.document.version",
            res_id=self.document_version_id.id,
        )

    @api.ondelete(at_uninstall=False)
    def _retain_submitted_evidence(self):
        for evidence in self:
            if evidence.state != "draft":
                raise AccessError(
                    _("Submitted/verified/rejected compliance evidence is retained and cannot be deleted.")
                )
            if not (
                is_pnp_compliance(self.env)
                or (
                    evidence.evidence_scope == "employee"
                    and evidence.employee_user_id == self.env.user
                )
            ):
                raise AccessError(
                    _("You may delete only your own Draft evidence.")
                )

