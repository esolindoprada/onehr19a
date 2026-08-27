from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import open_records_action
from .authority_helpers import require_learning_manager, require_learning_officer


class OneHRLearningVendor(models.Model):
    """External training provider master."""

    _name = "onehr.learning.vendor"
    _description = "OneHR Learning Vendor"
    _inherit = ["onehr.mixin.audit"]
    _order = "code, name, id"

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        ondelete="restrict",
        tracking=True,
        help="Optional commercial/contact record; Learning keeps only provider-specific facts here.",
    )
    active = fields.Boolean(default=True, tracking=True)
    vendor_type = fields.Selection(
        [
            ("training_provider", "Training Provider"),
            ("certification_body", "Certification Body"),
            ("trainer", "Independent Trainer"),
            ("platform", "Learning Platform"),
            ("other", "Other"),
        ],
        required=True,
        default="training_provider",
        index=True,
        tracking=True,
    )
    accreditation = fields.Char(tracking=True)
    website = fields.Char()
    contact_name = fields.Char()
    contact_email = fields.Char()
    contact_phone = fields.Char()
    rating = fields.Float(
        digits=(16, 2),
        tracking=True,
        help="Internal provider rating from 0 to 5.",
    )
    notes = fields.Text()
    session_count = fields.Integer(compute="_compute_session_count")
    total_actual_cost = fields.Monetary(
        compute="_compute_cost_summary",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    _vendor_code_company_unique = models.Constraint(
        "unique(company_id, code)",
        "Learning Vendor code must be unique within a company.",
    )

    def _compute_session_count(self):
        Session = self.env["onehr.learning.session"]
        for record in self:
            record.session_count = Session.search_count([("vendor_id", "=", record.id)])

    def _compute_cost_summary(self):
        Cost = self.env["onehr.learning.cost.line"]
        for record in self:
            records = Cost.search([("vendor_id", "=", record.id), ("state", "=", "actual")])
            record.total_actual_cost = sum(records.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            vals["code"] = (vals.get("code") or "").strip().upper()
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_vendor()
        return records

    def write(self, values):
        require_learning_officer(self)
        values = dict(values)
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        result = super().write(values)
        self._validate_vendor()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_used_vendor(self):
        require_learning_manager(self)
        for record in self:
            if record.session_count or self.env["onehr.learning.cost.line"].search_count(
                [("vendor_id", "=", record.id)]
            ):
                raise AccessError(_("A Learning Vendor with operational history cannot be deleted."))

    @api.constrains("rating", "partner_id", "company_id")
    def _check_vendor(self):
        self._validate_vendor()

    def _validate_vendor(self):
        for record in self:
            if not 0 <= record.rating <= 5:
                raise ValidationError(_("Vendor Rating must be between 0 and 5."))
        return True

    def action_open_sessions(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Training Sessions — %s", self.display_name),
            res_model="onehr.learning.session",
            domain=[("vendor_id", "=", self.id)],
            context={"default_vendor_id": self.id, "default_company_id": self.company_id.id},
            view_mode="list,calendar,pivot,graph,form",
        )
