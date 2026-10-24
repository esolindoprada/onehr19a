
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import require_portal_hr, open_records_action


REQUEST_STATES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("manager_review", "Manager Review"),
    ("hr_review", "HR Review"),
    ("approved", "Approved"),
    ("processing", "Processing"),
    ("done", "Done"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]


class OneHRPortalRequestStage(models.Model):
    _name = "onehr.portal.request.stage"
    _description = "OneHR Portal Request Stage"
    _inherit = ["onehr.mixin.audit"]
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(required=True, tracking=True, index=True)
    sequence = fields.Integer(default=10, index=True)
    company_id = fields.Many2one(
        "res.company",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for a shared stage available to all companies.",
    )
    state_key = fields.Selection(
        REQUEST_STATES,
        required=True,
        index=True,
        tracking=True,
        help="Technical lifecycle state represented by this display stage.",
    )
    active = fields.Boolean(default=True, tracking=True)
    portal_visible = fields.Boolean(default=True, tracking=True)
    fold = fields.Boolean(
        help="Fold this stage in Kanban when the client supports grouped folding.",
        tracking=True,
    )
    description = fields.Text(translate=True)
    request_ids = fields.One2many(
        "onehr.portal.request",
        "stage_id",
        string="Requests",
        readonly=True,
    )
    request_count = fields.Integer(compute="_compute_request_count")

    @api.model_create_multi
    def create(self, vals_list):
        require_portal_hr(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            values["code"] = (values.get("code") or "").strip().upper()
            prepared.append(values)
        return super().create(prepared)

    def write(self, vals):
        require_portal_hr(self)
        values = dict(vals)
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        if {"code", "company_id", "state_key"} & set(values):
            if any(record.request_ids for record in self):
                raise AccessError(
                    _("A Request Stage code/company/lifecycle mapping is frozen after transaction history exists. Archive it and create a replacement stage instead.")
                )
        return super().write(values)

    @api.constrains("code", "company_id")
    def _check_unique_code_scope(self):
        for record in self:
            domain = [("id", "!=", record.id), ("code", "=", record.code)]
            domain.append(("company_id", "=", record.company_id.id if record.company_id else False))
            if self.search_count(domain, limit=1):
                raise ValidationError(_("Request Stage Code must be unique in its company scope."))

    def _compute_request_count(self):
        Request = self.env["onehr.portal.request"]
        for record in self:
            record.request_count = Request.search_count([("stage_id", "=", record.id)])

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Requests — %s", self.display_name),
            res_model="onehr.portal.request",
            domain=[("stage_id", "=", self.id)],
            context={"default_stage_id": self.id},
            view_mode="list,kanban,form,pivot,graph",
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unused(self):
        if any(record.request_ids for record in self):
            raise AccessError(_("A Request Stage with transaction history cannot be deleted. Archive it instead."))

