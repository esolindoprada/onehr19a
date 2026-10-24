

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .action_helpers import open_records_action


class OneHRSequenceRule(models.Model):
    _name = "onehr.sequence.rule"
    _description = "OneHR Sequence Rule"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    purpose = fields.Text(required=True, translate=True)
    company_id = fields.Many2one("res.company", index=True, ondelete="restrict")
    sequence_id = fields.Many2one(
        "ir.sequence",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    @api.constrains("code", "company_id", "valid_from", "valid_to", "active")
    def _check_rule_overlap(self):
        for record in self.filtered("active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("active", "=", True)],
                _("Sequence-rule validity cannot overlap for a business code."),
            )

    @api.constrains("company_id", "sequence_id")
    def _check_sequence_company(self):
        for record in self:
            if (
                record.sequence_id.company_id
                and record.sequence_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _(
                        "The Odoo sequence must be global or belong to the "
                        "rule company."
                    )
                )

    def next_value(self, sequence_date=None):
        """Generate the next business number through canonical ir.sequence."""
        self.ensure_one()
        if not self.active or not self.is_effective_on(sequence_date):
            raise UserError(_("The sequence rule is not effective."))
        return self.sequence_id.with_company(
            self.company_id or self.env.company
        ).next_by_id(sequence_date=sequence_date)


class OneHREligibilityProfile(models.Model):
    _name = "onehr.eligibility.profile"
    _description = "OneHR Eligibility Profile"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    company_id = fields.Many2one("res.company", index=True, ondelete="restrict")
    active = fields.Boolean(default=True, tracking=True)
    department_ids = fields.Many2many("hr.department", string="Departments")
    job_ids = fields.Many2many("hr.job", string="Jobs")
    position_ids = fields.Many2many("onehr.position", string="Positions")
    grade_ids = fields.Many2many("onehr.grade", string="Grades")
    work_location_ids = fields.Many2many(
        "hr.work.location",
        string="Work Locations",
    )
    classification_keys = fields.Char(
        help=(
            "Comma-separated exact employee/engagement classification keys. "
            "Downstream domains may provide classification_key."
        )
    )
    min_service_months = fields.Integer()
    max_service_months = fields.Integer()

    @api.constrains("min_service_months", "max_service_months")
    def _check_service_range(self):
        for record in self:
            if record.min_service_months < 0:
                raise ValidationError(
                    _("Minimum service months cannot be negative.")
                )
            if record.max_service_months < 0:
                raise ValidationError(
                    _("Maximum service months cannot be negative.")
                )
            if (
                record.max_service_months
                and record.max_service_months < record.min_service_months
            ):
                raise ValidationError(
                    _("Maximum service must be at least minimum service.")
                )

    def matches(self, context_values):
        """Evaluate deterministic structured eligibility without safe_eval."""
        self.ensure_one()
        if not self.active or not self.is_effective_on(
            context_values.get("as_of_date")
        ):
            return False

        scalar_rules = (
            (self.company_id, "company_id"),
            (self.department_ids, "department_id"),
            (self.job_ids, "job_id"),
            (self.position_ids, "position_id"),
            (self.grade_ids, "grade_id"),
            (self.work_location_ids, "work_location_id"),
        )
        for allowed, key in scalar_rules:
            actual = context_values.get(key)
            actual_id = actual.id if hasattr(actual, "id") else actual
            if allowed and actual_id not in allowed.ids:
                return False

        allowed_keys = {
            key.strip()
            for key in (self.classification_keys or "").split(",")
            if key.strip()
        }
        if (
            allowed_keys
            and context_values.get("classification_key") not in allowed_keys
        ):
            return False

        service_months = context_values.get("service_months", 0)
        if service_months < self.min_service_months:
            return False
        if (
            self.max_service_months
            and service_months > self.max_service_months
        ):
            return False
        return True


class OneHRLifecycleEventType(models.Model):
    _name = "onehr.lifecycle.event.type"
    _description = "OneHR Lifecycle Event Type"
    _inherit = ["onehr.mixin.audit"]
    _order = "sequence, code"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    checklist_template_count = fields.Integer(
        string="Checklist Templates",
        compute="_compute_checklist_template_count",
    )

    @api.constrains("code")
    def _check_unique_code(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [("id", "!=", record.id), ("code", "=ilike", record.code)],
                limit=1,
            ):
                raise ValidationError(_("Lifecycle-event code must be unique."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values["code"] = (values.get("code") or "").strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals:
            requested_code = (vals["code"] or "").strip().upper()
            if any(record.code != requested_code for record in self):
                raise UserError(
                    _("Lifecycle-event business codes are immutable after creation.")
                )
        return super().write(vals)

    def _compute_checklist_template_count(self):
        Template = self.env["onehr.checklist.template"]
        for record in self:
            record.checklist_template_count = Template.search_count(
                [("lifecycle_event_type_id", "=", record.id)]
            )

    def action_open_checklist_templates(self):
        self.ensure_one()
        return open_records_action(
            name=_("Checklist Templates — %s", self.display_name),
            res_model="onehr.checklist.template",
            domain=[("lifecycle_event_type_id", "=", self.id)],
            context={"default_lifecycle_event_type_id": self.id},
        )
