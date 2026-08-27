from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action, require_document_manager


class OneHRDocumentCategory(models.Model):
    """Effective-dated classification and sensitivity defaults."""

    _name = "onehr.document.category"
    _description = "OneHR Document Category"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    description = fields.Text(translate=True)
    company_id = fields.Many2one(
        "res.company",
        index=True,
        ondelete="restrict",
        tracking=True,
        help="Leave empty only for a deliberately shared category.",
    )
    sensitivity = fields.Selection(
        [
            ("internal", "Internal"),
            ("confidential", "Confidential"),
            ("restricted", "Restricted"),
        ],
        required=True,
        default="internal",
        index=True,
        tracking=True,
    )
    employee_visible = fields.Boolean(
        default=False,
        tracking=True,
        help="Allows an employee-facing integration to expose the employee's own document when its own access layer permits it.",
    )
    signature_required = fields.Boolean(default=False, tracking=True)
    default_validity_days = fields.Integer(
        default=0,
        help="Default validity after issue. Zero means no automatic expiry date.",
    )
    default_reminder_days = fields.Integer(
        default=30,
        help="Days before expiry to schedule the standard expiry reminder.",
    )
    default_grace_days = fields.Integer(
        default=0,
        help="Optional grace period after expiry before the version is automatically marked Expired.",
    )
    retention_days_after_expiry = fields.Integer(
        default=0,
        help="Retention review interval after expiry. Zero means no automatic retention due date.",
    )
    active = fields.Boolean(default=True, tracking=True)
    document_count = fields.Integer(compute="_compute_usage_counts", string="Documents")
    template_count = fields.Integer(compute="_compute_usage_counts", string="Templates")

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
        return super().write(values)

    @api.constrains("code", "company_id", "valid_from", "valid_to", "active")
    def _check_unique_effective_category(self):
        for record in self.filtered("active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("active", "=", True)],
                _("Active document-category validity cannot overlap for the same code and company scope."),
            )

    @api.constrains(
        "default_validity_days",
        "default_reminder_days",
        "default_grace_days",
        "retention_days_after_expiry",
    )
    def _check_day_defaults(self):
        for record in self:
            if (
                record.default_validity_days < 0
                or record.default_reminder_days < 0
                or record.default_grace_days < 0
                or record.retention_days_after_expiry < 0
            ):
                raise ValidationError(_("Document governance day values cannot be negative."))

    def _compute_usage_counts(self):
        Document = self.env["onehr.document"]
        Template = self.env["onehr.document.template"]
        for record in self:
            record.document_count = Document.search_count([("category_id", "=", record.id)])
            record.template_count = Template.search_count([("category_id", "=", record.id)])

    def action_open_documents(self):
        self.ensure_one()
        return open_records_action(
            name=_("Documents — %s", self.display_name),
            res_model="onehr.document",
            domain=[("category_id", "=", self.id)],
            context={"default_category_id": self.id},
        )

    def action_open_templates(self):
        self.ensure_one()
        return open_records_action(
            name=_("Templates — %s", self.display_name),
            res_model="onehr.document.template",
            domain=[("category_id", "=", self.id)],
            context={"default_category_id": self.id},
        )
