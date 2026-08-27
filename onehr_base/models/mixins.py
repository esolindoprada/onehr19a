from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OneHRAuditMixin(models.AbstractModel):
    """Registry-approved chatter/activity foundation."""

    _name = "onehr.mixin.audit"
    _description = "OneHR Business Audit Mixin"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def log_business_action(self, body, subtype_xmlid="mail.mt_note"):
        for record in self:
            record.message_post(body=body, subtype_xmlid=subtype_xmlid)
        return True


class OneHREffectiveDatedMixin(models.AbstractModel):
    """Registry-approved effective-dated interval behavior."""

    _name = "onehr.mixin.effective.dated"
    _description = "OneHR Effective Dated Mixin"

    valid_from = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    valid_to = fields.Date(index=True, tracking=True)

    @api.constrains("valid_from", "valid_to")
    def _check_valid_interval(self):
        for record in self:
            if record.valid_to and record.valid_to < record.valid_from:
                raise ValidationError(_("Valid To must be on or after Valid From."))

    def is_effective_on(self, as_of_date=None):
        self.ensure_one()
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        return self.valid_from <= as_of_date and (not self.valid_to or self.valid_to >= as_of_date)

    @api.model
    def effective_domain(self, as_of_date=None, prefix=""):
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        return [
            (f"{prefix}valid_from", "<=", as_of_date),
            "|",
            (f"{prefix}valid_to", "=", False),
            (f"{prefix}valid_to", ">=", as_of_date),
        ]

    def _overlap_domain(self, business_key_fields, extra_domain=None):
        self.ensure_one()
        domain = [("id", "!=", self.id)]
        for field_name in business_key_fields:
            value = self[field_name]
            domain.append((field_name, "=", value.id if hasattr(value, "id") else value))
        domain += [
            ("valid_from", "<=", self.valid_to or fields.Date.to_date("9999-12-31")),
            "|",
            ("valid_to", "=", False),
            ("valid_to", ">=", self.valid_from),
        ]
        return domain + (extra_domain or [])

    def _check_no_effective_overlap(self, business_key_fields, extra_domain=None, message=None):
        for record in self:
            if self.search_count(record._overlap_domain(business_key_fields, extra_domain), limit=1):
                raise ValidationError(message or _("An overlapping effective-dated record already exists."))
        return True
