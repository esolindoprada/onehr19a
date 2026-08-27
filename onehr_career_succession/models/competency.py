from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .authority_helpers import require_talent_manager


class OneHRCompetency(models.Model):
    _name = "onehr.competency"
    _description = "OneHR Competency Dictionary"
    _inherit = ["onehr.mixin.audit"]
    _order = "category, code, name"

    _code_company_unique = models.Constraint(
        "UNIQUE(code, company_id)",
        "Competency code must be unique per company.",
    )

    code = fields.Char(required=True, index=True, tracking=True, copy=False)
    name = fields.Char(required=True, translate=True, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    category = fields.Selection(
        [
            ("core", "Core"),
            ("leadership", "Leadership"),
            ("functional", "Functional"),
            ("technical", "Technical"),
            ("behavioral", "Behavioral"),
            ("compliance", "Compliance / Safety"),
        ],
        default="functional",
        required=True,
        index=True,
        tracking=True,
    )
    description = fields.Text(translate=True)
    evidence_guidance = fields.Text(
        translate=True,
        help="Observable evidence expected when assessing this competency.",
    )

    level_min = fields.Integer(default=1, required=True, tracking=True)
    level_max = fields.Integer(default=5, required=True, tracking=True)
    level_1_behavior = fields.Text(string="Level 1 Behaviour", translate=True)
    level_2_behavior = fields.Text(string="Level 2 Behaviour", translate=True)
    level_3_behavior = fields.Text(string="Level 3 Behaviour", translate=True)
    level_4_behavior = fields.Text(string="Level 4 Behaviour", translate=True)
    level_5_behavior = fields.Text(string="Level 5 Behaviour", translate=True)

    position_requirement_ids = fields.One2many(
        "onehr.position.competency",
        "competency_id",
        string="Position Requirements",
    )
    position_count = fields.Integer(compute="_compute_counts")
    talent_count = fields.Integer(compute="_compute_counts")
    usage_count = fields.Integer(compute="_compute_counts")

    @api.depends("position_requirement_ids")
    def _compute_counts(self):
        PositionRequirement = self.env["onehr.position.competency"]
        Talent = self.env["onehr.talent.pool"]
        for record in self:
            record.position_count = PositionRequirement.search_count(
                [("competency_id", "=", record.id), ("active", "=", True)]
            )
            # Talent records store readiness against target positions; talent_count
            # means talent whose target position requires this competency.
            record.talent_count = Talent.search_count(
                [
                    ("target_position_id", "!=", False),
                    ("target_position_id", "in",
                     PositionRequirement.search(
                         [("competency_id", "=", record.id), ("active", "=", True)]
                     ).mapped("position_id").ids),
                    ("state", "=", "active"),
                ]
            )
            record.usage_count = record.position_count + record.talent_count

    @api.constrains("level_min", "level_max")
    def _check_level_scale(self):
        for record in self:
            if record.level_min < 1:
                raise ValidationError(_("Minimum competency level must be at least 1."))
            if record.level_max < record.level_min:
                raise ValidationError(
                    _("Maximum competency level cannot be below the minimum.")
                )
            if record.level_max > 10:
                raise ValidationError(
                    _("Competency level scale cannot exceed 10.")
                )

    def action_open_position_requirements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Position Requirements — %s", self.name),
            "res_model": "onehr.position.competency",
            "view_mode": "list,form,pivot,graph",
            "domain": [("competency_id", "=", self.id)],
            "context": {
                "default_competency_id": self.id,
                "default_company_id": self.company_id.id,
            },
        }

    def action_open_related_talent(self):
        self.ensure_one()
        position_ids = self.position_requirement_ids.filtered(
            lambda line: line.active
        ).mapped("position_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Talent Requiring %s", self.name),
            "res_model": "onehr.talent.pool",
            "view_mode": "kanban,list,form,pivot,graph",
            "domain": [("target_position_id", "in", position_ids)],
        }

    def action_archive_governed(self):
        require_talent_manager(self)
        self.write({"active": False})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unused(self):
        for record in self:
            if self.env["onehr.position.competency"].search_count(
                [("competency_id", "=", record.id)],
                limit=1,
            ):
                raise UserError(
                    _("A competency used by a position requirement must be archived, not deleted.")
                )
