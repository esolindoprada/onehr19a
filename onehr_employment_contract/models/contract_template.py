from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_contract_manager


class OneHRContractTemplate(models.Model):
    """Versioned legal/business policy template (ED2).

    Document body ownership deliberately remains in onehr_document. This model
    owns employment-contract policy/applicability and references a document
    template by stable business code only, preserving the soft dependency.
    """

    _name = "onehr.contract.template"
    _description = "OneHR Employment Contract Template Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, version desc, id desc"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    version = fields.Integer(required=True, default=1, tracking=True)
    company_id = fields.Many2one(
        "res.company", index=True, ondelete="restrict", tracking=True,
        help="Leave empty only for a deliberately shared template policy.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        required=True, default="draft", index=True, tracking=True,
    )

    default_contract_kind = fields.Selection(
        [("initial", "Initial"), ("renewal", "Renewal"), ("amendment", "Amendment")],
        required=True, default="initial", tracking=True,
    )
    engagement_type_ids = fields.Many2many("onehr.engagement.type", string="Engagement Types")
    grade_ids = fields.Many2many("onehr.grade", string="Grades")
    position_ids = fields.Many2many("onehr.position", string="Positions")
    job_ids = fields.Many2many("hr.job", string="Jobs")

    default_probation_days = fields.Integer(default=0, tracking=True)
    notice_period_days = fields.Integer(default=30, tracking=True)
    expiry_reminder_lead_days = fields.Integer(default=30, tracking=True)
    approval_sla_hours = fields.Integer(default=48, tracking=True)
    document_template_code = fields.Char(
        default="EMPLOYMENT_CONTRACT", tracking=True,
        help="Soft link to onehr_document template business code; no hard model relation is created.",
    )
    notes = fields.Html(sanitize=True, translate=True)
    contract_count = fields.Integer(compute="_compute_contract_count", string="Contracts")

    @api.model_create_multi
    def create(self, vals_list):
        require_contract_manager(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            vals["code"] = (vals.get("code") or "").strip().upper()
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        require_contract_manager(self)
        values = dict(vals)
        if "state" in values and not self.env.context.get("onehr_contract_template_state_action"):
            raise AccessError(_("Template state can change only through governed template actions."))
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        if any(record.state != "draft" for record in self):
            protected = {
                "code", "version", "company_id", "engagement_type_ids", "grade_ids",
                "position_ids", "job_ids", "default_contract_kind", "valid_from",
            }
            if protected & set(values):
                raise AccessError(
                    _("Activated/retired template identity cannot be rewritten. Create a new version instead.")
                )
        return super().write(values)

    @api.constrains("code", "company_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.with_context(active_test=False).search_count([
                ("id", "!=", record.id),
                ("code", "=ilike", record.code),
                ("company_id", "=", record.company_id.id if record.company_id else False),
                ("version", "=", record.version),
            ], limit=1):
                raise ValidationError(_("Template version must be unique within its company/global scope."))

    @api.constrains("code", "company_id", "valid_from", "valid_to", "state")
    def _check_active_overlap(self):
        for record in self.filtered(lambda row: row.state == "active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("state", "=", "active")],
                _("Active contract-template versions cannot overlap for the same code and scope."),
            )

    @api.constrains(
        "company_id", "engagement_type_ids", "grade_ids", "position_ids", "job_ids",
        "default_probation_days", "notice_period_days", "expiry_reminder_lead_days", "approval_sla_hours",
    )
    def _check_policy_integrity(self):
        for record in self:
            for value, label in (
                (record.default_probation_days, _("Default Probation Days")),
                (record.notice_period_days, _("Notice Period Days")),
                (record.expiry_reminder_lead_days, _("Expiry Reminder Lead Days")),
                (record.approval_sla_hours, _("Approval SLA Hours")),
            ):
                if value < 0:
                    raise ValidationError(_("%s cannot be negative.", label))
            if record.company_id:
                for scoped_records in (
                    record.engagement_type_ids,
                    record.grade_ids,
                    record.position_ids,
                    record.job_ids,
                ):
                    for item in scoped_records:
                        if getattr(item, "company_id", False) and item.company_id != record.company_id:
                            raise ValidationError(_("Template applicability records must be global or belong to the template company."))

    def _compute_contract_count(self):
        Contract = self.env["onehr.contract"]
        for record in self:
            record.contract_count = Contract.search_count([("template_id", "=", record.id)])

    def matches_hr_version(self, version, as_of_date=None):
        """Deterministic applicability check; no executable expressions."""
        self.ensure_one()
        as_of_date = fields.Date.to_date(as_of_date or version.contract_date_start or version.date_version)
        if self.state != "active" or not self.is_effective_on(as_of_date):
            return False
        if self.company_id and self.company_id != version.company_id:
            return False
        if self.engagement_type_ids and version.onehr_engagement_type_id not in self.engagement_type_ids:
            return False
        if self.grade_ids and version.onehr_grade_id not in self.grade_ids:
            return False
        if self.position_ids and version.onehr_primary_position_id not in self.position_ids:
            return False
        if self.job_ids and version.job_id not in self.job_ids:
            return False
        return True

    def action_activate(self):
        require_contract_manager(self)
        self.with_context(onehr_contract_template_state_action=True).write({"state": "active"})
        return True

    def action_retire(self):
        require_contract_manager(self)
        self.with_context(onehr_contract_template_state_action=True).write({"state": "retired"})
        return True

    def action_create_new_version(self):
        self.ensure_one()
        require_contract_manager(self)
        latest = self.with_context(active_test=False).search([
            ("code", "=ilike", self.code),
            ("company_id", "=", self.company_id.id if self.company_id else False),
        ], order="version desc, id desc", limit=1)
        values = {
            "version": (latest.version if latest else self.version) + 1,
            "state": "draft",
            "valid_from": fields.Date.context_today(self),
            "valid_to": False,
        }
        new_version = self.copy(values)
        return open_record_action(
            name=_("Contract Template Version %s", new_version.version),
            res_model=self._name,
            res_id=new_version.id,
        )

    def action_open_contracts(self):
        self.ensure_one()
        return open_records_action(
            name=_("Contracts — %s", self.display_name),
            res_model="onehr.contract",
            domain=[("template_id", "=", self.id)],
            context={"default_template_id": self.id},
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(record.state != "draft" or record.contract_count for record in self):
            raise AccessError(_("Only unused draft contract templates may be deleted."))
