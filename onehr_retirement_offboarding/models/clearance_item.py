from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action
from .security_helpers import require_offboarding_admin


class OneHRClearanceItem(models.Model):
    """Reusable clearance catalogue.

    The catalogue defines *what* must be cleared. Generated checklist records keep
    a snapshot so later catalogue changes never rewrite historical exit evidence.
    """

    _name = "onehr.clearance.item"
    _description = "OneHR Offboarding Clearance Item"
    _inherit = ["onehr.mixin.audit"]
    _order = "sequence, code, id"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Leave empty for a global clearance item.",
    )
    category = fields.Selection(
        [
            ("asset", "Asset Return"),
            ("access", "Access / Identity"),
            ("knowledge", "Knowledge Handover"),
            ("finance", "Finance / Settlement"),
            ("hr", "HR Administration"),
            ("compliance", "Compliance"),
            ("security", "Physical Security"),
            ("other", "Other"),
        ],
        required=True,
        default="other",
        index=True,
        tracking=True,
    )
    owner_role = fields.Selection(
        [
            ("hr", "HR"),
            ("it", "IT"),
            ("finance", "Finance"),
            ("manager", "Line Manager"),
            ("employee", "Employee"),
            ("security", "Security"),
            ("other", "Other"),
        ],
        required=True,
        default="hr",
        tracking=True,
    )
    mandatory = fields.Boolean(default=True, tracking=True)
    sla_days = fields.Integer(default=3, tracking=True)
    instructions = fields.Text(tracking=True)
    job_id = fields.Many2one("hr.job", ondelete="restrict", tracking=True)
    grade_id = fields.Many2one("onehr.grade", ondelete="restrict", tracking=True)
    offboarding_type = fields.Selection(
        [
            ("all", "All Exit Types"),
            ("resignation", "Resignation"),
            ("retirement", "Retirement"),
            ("employer_termination", "Employer Termination"),
            ("mutual", "Mutual Agreement"),
            ("other", "Other"),
        ],
        default="all",
        required=True,
        index=True,
        tracking=True,
    )
    generated_task_count = fields.Integer(compute="_compute_generated_task_count")

    _sla_non_negative = models.Constraint(
        "CHECK(sla_days >= 0)",
        "Clearance-item SLA days cannot be negative.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_offboarding_admin(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code"):
                vals["code"] = vals["code"].strip().upper()
            prepared.append(vals)
        records = super().create(prepared)
        records._check_code_uniqueness()
        return records

    def write(self, vals):
        require_offboarding_admin(self)
        values = dict(vals)
        if values.get("code"):
            values["code"] = values["code"].strip().upper()
        result = super().write(values)
        self._check_code_uniqueness()
        return result

    def unlink(self):
        require_offboarding_admin(self)
        if self.env["onehr.offboarding.checklist"].search_count(
            [("clearance_item_id", "in", self.ids)], limit=1
        ):
            raise ValidationError(
                _("A clearance item already used by offboarding evidence cannot be deleted. Archive it instead.")
            )
        return super().unlink()

    @api.constrains("code", "company_id")
    def _check_code_uniqueness(self):
        for record in self:
            domain = [("id", "!=", record.id), ("code", "=", record.code)]
            if record.company_id:
                domain.append(("company_id", "=", record.company_id.id))
            else:
                domain.append(("company_id", "=", False))
            if self.search_count(domain, limit=1):
                raise ValidationError(
                    _("Clearance item code must be unique inside its global/company scope.")
                )

    def _compute_generated_task_count(self):
        Checklist = self.env["onehr.offboarding.checklist"]
        for record in self:
            record.generated_task_count = Checklist.search_count(
                [("clearance_item_id", "=", record.id)]
            )

    def action_open_generated_tasks(self):
        self.ensure_one()
        return open_records_action(
            name=_("Generated Tasks — %s", self.display_name),
            res_model="onehr.offboarding.checklist",
            domain=[("clearance_item_id", "=", self.id)],
        )

    def action_archive(self):
        require_offboarding_admin(self)
        self.write({"active": False})
        return True

    def action_restore(self):
        require_offboarding_admin(self)
        self.write({"active": True})
        return True
