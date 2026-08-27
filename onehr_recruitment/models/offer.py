from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_recruiter, require_recruitment_manager


class OneHROffer(models.Model):
    """Governed offer terms, approval and candidate decision evidence (ED3)."""

    _name = "onehr.offer"
    _description = "OneHR Recruitment Offer"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "offer_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Offer Number", required=True, default=lambda self: _("New"),
        readonly=True, copy=False, index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True, ondelete="restrict"
    )
    applicant_id = fields.Many2one(
        "hr.applicant", required=True, index=True, tracking=True,
        ondelete="restrict", check_company=True,
    )
    requisition_id = fields.Many2one(
        "onehr.recruitment.requisition", index=True, tracking=True,
        ondelete="set null", check_company=True,
    )
    job_id = fields.Many2one(
        "hr.job", related="applicant_id.job_id", store=True, index=True, readonly=True,
    )
    position_id = fields.Many2one(
        "onehr.position", string="Position", index=True, tracking=True,
        ondelete="restrict", check_company=True,
    )
    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.company.currency_id,
        readonly=False,
    )
    base_salary = fields.Monetary(
        string="Base Salary", currency_field="currency_id", tracking=True,
        groups="onehr_recruitment.group_onehr_recruiter",
    )
    variable_compensation = fields.Monetary(
        string="Variable Compensation", currency_field="currency_id", tracking=True,
        groups="onehr_recruitment.group_onehr_recruiter",
    )
    other_compensation = fields.Monetary(
        string="Other Compensation", currency_field="currency_id", tracking=True,
        groups="onehr_recruitment.group_onehr_recruiter",
    )
    total_cash_compensation = fields.Monetary(
        string="Total Cash", currency_field="currency_id", compute="_compute_total_cash",
        groups="onehr_recruitment.group_onehr_recruiter",
    )
    offer_date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    proposed_start_date = fields.Date(index=True, tracking=True)
    expiry_date = fields.Date(required=True, index=True, tracking=True)
    terms = fields.Html(sanitize=True, tracking=True)
    internal_justification = fields.Text(
        tracking=True, groups="onehr_recruitment.group_onehr_recruiter"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("withdrawn", "Withdrawn"),
            ("expired", "Expired"),
        ],
        required=True, default="draft", index=True, tracking=True, copy=False,
    )
    approved_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    sent_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    responded_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    response_note = fields.Text(copy=False, tracking=True)
    preboarding_ids = fields.One2many("onehr.preboarding", "offer_id", string="Preboarding")
    preboarding_count = fields.Integer(compute="_compute_preboarding_count")

    _PROTECTED_TERMS = {
        "company_id", "applicant_id", "requisition_id", "position_id", "currency_id",
        "base_salary", "variable_compensation", "other_compensation", "offer_date",
        "proposed_start_date", "expiry_date", "terms",
    }

    @api.model_create_multi
    def create(self, vals_list):
        require_recruiter(self)
        for values in vals_list:
            if values.get("name", _("New")) in (False, _("New")):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.recruitment.offer") or _("New")
            applicant = self.env["hr.applicant"].browse(values.get("applicant_id"))
            values.setdefault("company_id", applicant.company_id.id or self.env.company.id)
            values.setdefault("requisition_id", applicant.onehr_requisition_id.id)
            if not values.get("expiry_date"):
                raise ValidationError(_("Offer expiry date is required."))
        return super().create(vals_list)

    def write(self, values):
        if self._PROTECTED_TERMS.intersection(values) and self.filtered(lambda rec: rec.state != "draft"):
            raise AccessError(_("Submitted offer terms are historical evidence and cannot be rewritten."))
        return super().write(values)

    @api.depends("base_salary", "variable_compensation", "other_compensation")
    def _compute_total_cash(self):
        for offer in self:
            offer.total_cash_compensation = offer.base_salary + offer.variable_compensation + offer.other_compensation

    @api.depends("preboarding_ids")
    def _compute_preboarding_count(self):
        for offer in self:
            offer.preboarding_count = len(offer.preboarding_ids)

    @api.constrains("offer_date", "expiry_date", "proposed_start_date")
    def _check_dates(self):
        for offer in self:
            if offer.expiry_date and offer.expiry_date < offer.offer_date:
                raise ValidationError(_("Offer expiry date cannot be before offer date."))
            if offer.proposed_start_date and offer.proposed_start_date < offer.offer_date:
                raise ValidationError(_("Proposed start date cannot be before offer date."))

    @api.constrains("base_salary", "variable_compensation", "other_compensation")
    def _check_compensation(self):
        for offer in self:
            if min(offer.base_salary, offer.variable_compensation, offer.other_compensation) < 0:
                raise ValidationError(_("Offer compensation amounts cannot be negative."))

    @api.constrains("applicant_id", "requisition_id", "position_id", "company_id")
    def _check_scope_alignment(self):
        for offer in self:
            if offer.applicant_id.company_id and offer.applicant_id.company_id != offer.company_id:
                raise ValidationError(_("Applicant and offer must belong to the same company."))
            if offer.requisition_id:
                if offer.requisition_id.company_id != offer.company_id:
                    raise ValidationError(_("Requisition and offer must belong to the same company."))
                if offer.applicant_id.onehr_requisition_id and offer.requisition_id != offer.applicant_id.onehr_requisition_id:
                    raise ValidationError(_("Offer requisition must match the applicant requisition."))
            if offer.position_id:
                if offer.position_id.company_id != offer.company_id:
                    raise ValidationError(_("Position and offer must belong to the same company."))
                if offer.position_id.job_id != offer.job_id:
                    raise ValidationError(_("Offer position must use the applicant's job."))

    def _approval_payload(self):
        self.ensure_one()
        return {
            "offer": self.name,
            "applicant": self.applicant_id.partner_name or self.applicant_id.display_name,
            "job": self.job_id.display_name,
            "position": self.position_id.display_name if self.position_id else False,
            "proposed_start_date": fields.Date.to_string(self.proposed_start_date) if self.proposed_start_date else False,
            "expiry_date": fields.Date.to_string(self.expiry_date),
            "total_cash_compensation": self.total_cash_compensation,
            "currency": self.currency_id.name,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = []
        if self.requisition_id.hiring_manager_user_id:
            manager_ids.append(self.requisition_id.hiring_manager_user_id.id)
        values.update({
            "document_type": "recruitment_offer",
            "amount": self.total_cash_compensation,
            "currency_id": self.currency_id.id,
            "manager_user_ids": manager_ids,
            "extra": {
                "job_id": self.job_id.id,
                "position_id": self.position_id.id,
                "applicant_id": self.applicant_id.id,
            },
        })
        return values

    def action_submit_for_approval(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "draft":
            raise UserError(_("Only a draft offer can be submitted for approval."))
        self.write({"state": "pending_approval"})
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "pending_approval":
            return True
        if decision == "approve":
            self.write({"state": "approved", "approved_at": fields.Datetime.now()})
        elif decision == "reject":
            self.write({"state": "rejected"})
        return True

    def action_mark_sent(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "approved":
            raise UserError(_("Only an approved offer can be marked sent."))
        self.write({"state": "sent", "sent_at": fields.Datetime.now()})
        request = self.env["onehr.approval.request"].search(
            [("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")],
            order="requested_at desc, id desc", limit=1,
        )
        if request:
            self.onehr_mark_approval_executed(request)
        return True

    def action_accept(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "sent":
            raise UserError(_("Only a sent offer can be accepted."))
        if fields.Date.today() > self.expiry_date:
            raise UserError(_("This offer has expired. Mark it expired or issue a new governed offer."))
        self.write({"state": "accepted", "responded_at": fields.Datetime.now()})
        return True

    def action_decline(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "sent":
            raise UserError(_("Only a sent offer can be declined."))
        self.write({"state": "declined", "responded_at": fields.Datetime.now()})
        return True

    def action_withdraw(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state not in {"approved", "sent"}:
            raise UserError(_("Only approved or sent offers can be withdrawn."))
        if not self.response_note:
            raise UserError(_("Record the withdrawal reason in Response Note first."))
        self.write({"state": "withdrawn", "responded_at": fields.Datetime.now()})
        return True

    def action_expire(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "sent":
            raise UserError(_("Only a sent offer can be expired."))
        if fields.Date.today() <= self.expiry_date:
            raise UserError(_("The offer has not reached its expiry date."))
        self.write({"state": "expired", "responded_at": fields.Datetime.now()})
        return True

    def action_generate_offer_document(self):
        """Soft integration with onehr_document; no hard reverse dependency."""
        self.ensure_one()
        require_recruiter(self)
        if self.state not in {"approved", "sent", "accepted"}:
            raise UserError(_("Generate an offer document only after offer approval."))
        try:
            DocumentTemplate = self.env["onehr.document.template"]
            self.env["wizard.document.generate"]
        except KeyError:
            raise UserError(_("OneHR Document is not installed. Install it to generate governed offer documents."))
        template = DocumentTemplate.search(
            [
                ("code", "=ilike", "RECRUITMENT_OFFER"),
                ("active", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            order="company_id desc, id desc", limit=1,
        )
        if not template:
            raise UserError(_("Create an active OneHR Document template with code RECRUITMENT_OFFER first."))
        source_model = self.env["ir.model"]._get(self._name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Offer Document"),
            "res_model": "wizard.document.generate",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_template_id": template.id,
                "default_company_id": self.company_id.id,
                "default_source_model_id": source_model.id,
                "default_source_res_id": self.id,
                "default_document_name": _("Offer — %s", self.applicant_id.partner_name or self.applicant_id.display_name),
                "default_effective_from": self.offer_date,
                "default_expiry_date": self.expiry_date,
            },
        }

    def action_create_preboarding(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "accepted":
            raise UserError(_("Preboarding can start only after the offer is accepted."))
        existing = self.preboarding_ids.filtered(lambda rec: rec.state != "cancelled")[:1]
        if existing:
            return existing.action_open_self()
        preboarding = self.env["onehr.preboarding"].create({
            "applicant_id": self.applicant_id.id,
            "requisition_id": self.requisition_id.id,
            "offer_id": self.id,
            "planned_start_date": self.proposed_start_date or fields.Date.today(),
        })
        return preboarding.action_open_self()

    def action_open_applicant(self):
        self.ensure_one()
        return open_record_action(name=_("Applicant"), res_model="hr.applicant", res_id=self.applicant_id.id)

    def action_open_preboarding(self):
        self.ensure_one()
        return open_records_action(
            name=_("Preboarding — %s", self.name), res_model="onehr.preboarding",
            domain=[("offer_id", "=", self.id)], context={"default_offer_id": self.id, "default_applicant_id": self.applicant_id.id},
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "draft" for rec in self):
            raise UserError(_("Only draft offers may be deleted. Offer decision evidence must be retained."))
