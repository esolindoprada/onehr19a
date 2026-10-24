
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action, require_corehr_manager


class OneHREngagementType(models.Model):
    """Enterprise refinement of Odoo's native hr.version.employee_type."""

    _name = "onehr.engagement.type"
    _description = "OneHR Engagement Type"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "sequence, code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", ondelete="restrict", index=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    native_employee_type = fields.Selection(
        [
            ("employee", "Employee"),
            ("worker", "Worker"),
            ("student", "Student"),
            ("trainee", "Trainee"),
            ("contractor", "Contractor"),
            ("freelance", "Freelancer"),
        ],
        required=True,
        default="employee",
        tracking=True,
        help="Maps this enterprise classification to Odoo's canonical employee_type.",
    )
    description = fields.Text(translate=True)
    version_count = fields.Integer(compute="_compute_version_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["code"] = (vals.get("code") or "").strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals:
            vals = dict(vals)
            vals["code"] = (vals.get("code") or "").strip().upper()
        return super().write(vals)

    @api.constrains("code", "company_id")
    def _check_unique_code_scope(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [
                    ("id", "!=", record.id),
                    ("code", "=ilike", record.code),
                    ("company_id", "=", record.company_id.id if record.company_id else False),
                ],
                limit=1,
            ):
                raise ValidationError(_("Engagement Type code must be unique in its company/global scope."))

    @api.constrains("code", "company_id", "valid_from", "valid_to", "active")
    def _check_no_active_overlap(self):
        for record in self.filtered("active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("active", "=", True)],
                _("Active Engagement Type validity cannot overlap for the same code and scope."),
            )

    def _compute_version_count(self):
        Version = self.env["hr.version"]
        for record in self:
            record.version_count = Version.search_count([("onehr_engagement_type_id", "=", record.id)])

    def action_open_versions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Employee Versions — %s", self.display_name),
            res_model="hr.version",
            domain=[("onehr_engagement_type_id", "=", self.id)],
        )

    def action_archive(self):
        require_corehr_manager(self.env)
        self.write({"active": False})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Engagement Types are governed history. Archive them instead of deleting."))
