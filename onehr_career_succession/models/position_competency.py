from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .authority_helpers import require_talent_manager


class OneHRPositionCompetency(models.Model):
    _name = "onehr.position.competency"
    _description = "OneHR Position Competency Requirement"
    _inherit = ["onehr.mixin.audit"]
    _order = "position_id, sequence, competency_id"

    _position_competency_unique = models.Constraint(
        "UNIQUE(position_id, competency_id)",
        "A competency can appear only once for the same position.",
    )

    sequence = fields.Integer(default=10, index=True)
    company_id = fields.Many2one(
        "res.company",
        related="position_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    position_id = fields.Many2one(
        "onehr.position",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
        tracking=True,
    )
    position_code = fields.Char(
        related="position_id.code",
        store=True,
        readonly=True,
        index=True,
    )
    position_name = fields.Char(
        related="position_id.name",
        store=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="position_id.job_id",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="position_id.department_id",
        store=True,
        readonly=True,
        index=True,
    )
    competency_id = fields.Many2one(
        "onehr.competency",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    competency_category = fields.Selection(
        related="competency_id.category",
        store=True,
        readonly=True,
        index=True,
    )
    required_level = fields.Integer(default=3, required=True, tracking=True)
    weight = fields.Float(
        default=0.0,
        tracking=True,
        help="Optional contribution to aggregate competency readiness. "
             "Zero means equal-weight when all requirements are zero.",
    )
    mandatory = fields.Boolean(default=True, tracking=True)
    evidence_required = fields.Boolean(default=True, tracking=True)
    behavioral_evidence = fields.Text(
        string="Expected Behaviour / Evidence",
        translate=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    @api.constrains("required_level", "competency_id")
    def _check_required_level(self):
        for line in self:
            if not line.competency_id:
                continue
            if not (
                line.competency_id.level_min
                <= line.required_level
                <= line.competency_id.level_max
            ):
                raise ValidationError(
                    _(
                        "Required level for %s must be between %s and %s."
                    )
                    % (
                        line.competency_id.name,
                        line.competency_id.level_min,
                        line.competency_id.level_max,
                    )
                )

    @api.constrains("weight")
    def _check_weight(self):
        for line in self:
            if line.weight < 0 or line.weight > 100:
                raise ValidationError(
                    _("Position competency weight must be between 0 and 100.")
                )

    @api.constrains("company_id", "competency_id")
    def _check_company_alignment(self):
        for line in self:
            if (
                line.competency_id
                and line.competency_id.company_id != line.company_id
            ):
                raise ValidationError(
                    _("Position and competency must belong to the same company.")
                )

    def action_open_position(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Position"),
            "res_model": "onehr.position",
            "res_id": self.position_id.id,
            "view_mode": "form",
        }

    def action_open_talent_gap(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Talent Gap — %s", self.position_name),
            "res_model": "onehr.talent.pool",
            "view_mode": "kanban,list,form,pivot,graph",
            "domain": [
                ("target_position_id", "=", self.position_id.id),
                ("state", "in", ("approved", "active")),
            ],
        }

    def action_archive_governed(self):
        require_talent_manager(self)
        self.write({"active": False})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unused(self):
        for line in self:
            if self.env["onehr.talent.pool"].search_count(
                [
                    ("target_position_id", "=", line.position_id.id),
                    ("state", "in", ("approved", "active")),
                ],
                limit=1,
            ):
                raise UserError(
                    _("Position competency requirements used by active talent evidence "
                      "must be archived, not deleted.")
                )
