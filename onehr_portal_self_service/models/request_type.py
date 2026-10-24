
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import is_portal_hr, require_portal_hr, open_records_action


SERVICE_KINDS = [
    ("generic", "General HR Service"),
    ("profile_change", "Profile Change"),
    ("timeoff", "Time Off"),
    ("learning", "Learning / Training"),
    ("document", "HR Document"),
]


class OneHRPortalRequestType(models.Model):
    _name = "onehr.portal.request.type"
    _description = "OneHR Portal Request Type"
    _inherit = ["onehr.mixin.audit"]
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
    sequence = fields.Integer(default=10, index=True)
    company_id = fields.Many2one(
        "res.company",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for a deliberately shared request type.",
    )
    active = fields.Boolean(default=True, tracking=True)
    portal_enabled = fields.Boolean(
        default=True,
        tracking=True,
        help="Allows authenticated self-service users to select this request type.",
    )
    service_kind = fields.Selection(
        SERVICE_KINDS,
        required=True,
        default="generic",
        index=True,
        tracking=True,
    )
    default_priority = fields.Selection(
        [("0", "Normal"), ("1", "Low"), ("2", "High"), ("3", "Urgent")],
        default="0",
        required=True,
        tracking=True,
    )
    manager_approval_required = fields.Boolean(default=True, tracking=True)
    hr_approval_required = fields.Boolean(default=True, tracking=True)
    responsible_user_id = fields.Many2one(
        "res.users",
        string="HR Service Owner",
        ondelete="restrict",
        tracking=True,
        domain=[("share", "=", False)],
        groups="onehr_portal_self_service.group_onehr_portal_hr",
        help="Optional internal owner for SLA activities and HR processing.",
    )
    auto_execute_on_approval = fields.Boolean(
        default=False,
        tracking=True,
        help=(
            "When enabled, an authorized final approver attempts the configured soft integration. "
            "The downstream addon still enforces its own ACL, record rules and business authority."
        ),
    )
    sla_hours = fields.Integer(
        default=72,
        tracking=True,
        help="Target service time from submission. Zero disables the SLA deadline.",
    )
    reminder_hours_before = fields.Integer(
        default=24,
        tracking=True,
        help="Schedule an activity this many hours before the SLA deadline. Zero disables pre-due reminder.",
    )
    instructions = fields.Html(translate=True, sanitize=True)
    submission_message = fields.Text(
        translate=True,
        default="Your request has been submitted and is now being processed.",
    )
    approval_message = fields.Text(
        translate=True,
        default="Your request has been approved.",
    )
    rejection_message = fields.Text(
        translate=True,
        default="Your request has been rejected. Review the decision note for details.",
    )
    completion_message = fields.Text(
        translate=True,
        default="Your request has been completed.",
    )
    profile_allowed_fields = fields.Char(
        default="private_email,private_phone,private_street,private_street2,private_city,private_zip",
        help=(
            "Comma-separated hr.employee fields that may be changed by an approved Profile Change request. "
            "Every field is still checked at execution time and written under normal HR authority."
        ),
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )
    request_ids = fields.One2many(
        "onehr.portal.request",
        "type_id",
        string="Requests",
        readonly=True,
    )
    request_count = fields.Integer(compute="_compute_request_metrics")
    open_count = fields.Integer(compute="_compute_request_metrics")
    overdue_count = fields.Integer(compute="_compute_request_metrics")

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

        # Routing and payload identity are historical contract fields. Once a type
        # has transaction history, changing them would reinterpret in-flight or
        # completed requests. Create a new Request Type instead.
        historical_contract_fields = {
            "code",
            "company_id",
            "service_kind",
            "manager_approval_required",
            "hr_approval_required",
            "auto_execute_on_approval",
            "profile_allowed_fields",
        }
        if historical_contract_fields & set(values):
            for record in self:
                if record.request_ids:
                    raise AccessError(
                        _("Request Type routing/payload identity is frozen after transaction history exists. Create a new Request Type for a changed contract.")
                    )
        return super().write(values)

    @api.constrains("code", "company_id")
    def _check_unique_code_scope(self):
        for record in self:
            domain = [("id", "!=", record.id), ("code", "=", record.code)]
            if record.company_id:
                domain.append(("company_id", "=", record.company_id.id))
            else:
                domain.append(("company_id", "=", False))
            if self.search_count(domain, limit=1):
                raise ValidationError(_("Request Type Code must be unique in its company scope."))

    @api.constrains("sla_hours", "reminder_hours_before")
    def _check_sla_values(self):
        for record in self:
            if record.sla_hours < 0 or record.reminder_hours_before < 0:
                raise ValidationError(_("SLA and reminder hours cannot be negative."))
            if record.sla_hours and record.reminder_hours_before > record.sla_hours:
                raise ValidationError(_("Reminder Hours Before cannot exceed the SLA target."))

    @api.constrains("service_kind", "manager_approval_required", "hr_approval_required", "auto_execute_on_approval")
    def _check_execution_governance(self):
        for record in self:
            if record.auto_execute_on_approval and record.service_kind == "generic":
                raise ValidationError(_("Generic HR services cannot auto-execute a downstream integration."))
            if record.service_kind == "profile_change" and not record.hr_approval_required:
                raise ValidationError(_("Profile Change requests require HR approval before canonical employee data can change."))

    def _compute_request_metrics(self):
        Request = self.env["onehr.portal.request"]
        for record in self:
            record.request_count = Request.search_count([("type_id", "=", record.id)])
            record.open_count = Request.search_count(
                [("type_id", "=", record.id), ("state", "not in", ("done", "rejected", "cancelled"))]
            )
            record.overdue_count = Request.search_count(
                [("type_id", "=", record.id), ("is_sla_overdue", "=", True)]
            )

    def action_open_requests(self):
        self.ensure_one()
        return open_records_action(
            name=_("Requests — %s", self.display_name),
            res_model="onehr.portal.request",
            domain=[("type_id", "=", self.id)],
            context={"default_type_id": self.id},
            view_mode="list,kanban,form,pivot,graph",
        )

    def action_toggle_portal(self):
        require_portal_hr(self)
        for record in self:
            record.write({"portal_enabled": not record.portal_enabled})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unused(self):
        if any(record.request_ids for record in self):
            raise AccessError(_("A Request Type with transaction history cannot be deleted. Archive it instead."))

