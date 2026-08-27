from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action


def _validate_scoped_code(records, label):
    """Enforce case-insensitive uniqueness in company/global scope.

    A plain SQL UNIQUE constraint is insufficient here because company_id may be
    empty for a global record and SQL NULL semantics allow multiple NULL values.
    """
    for record in records:
        domain = [
            ("id", "!=", record.id),
            ("code", "=ilike", record.code),
            (
                "company_id",
                "=",
                record.company_id.id if record.company_id else False,
            ),
        ]
        if records.with_context(active_test=False).search_count(domain, limit=1):
            raise ValidationError(
                _(
                    "%s code must be unique within its company/global scope.",
                    label,
                )
            )


class OneHRJobFamily(models.Model):
    _name = "onehr.job.family"
    _description = "OneHR Job Family"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    description = fields.Text(translate=True)
    company_id = fields.Many2one("res.company", index=True, ondelete="restrict")
    active = fields.Boolean(default=True, tracking=True)
    position_count = fields.Integer(
        string="Positions",
        compute="_compute_position_count",
    )

    def _validate_scoped_code(self, label):
        return _validate_scoped_code(self, label)

    @api.constrains("code", "company_id")
    def _check_unique_code(self):
        self._validate_scoped_code(_("Job family"))

    def _compute_position_count(self):
        Position = self.env["onehr.position"]
        for record in self:
            record.position_count = Position.search_count(
                [("job_id.onehr_job_family_id", "=", record.id)]
            )

    def action_open_positions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Positions — %s", self.display_name),
            res_model="onehr.position",
            domain=[("job_id.onehr_job_family_id", "=", self.id)],
        )


class OneHRGrade(models.Model):
    _name = "onehr.grade"
    _description = "OneHR Grade"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "sequence, code"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10, index=True)
    description = fields.Text(translate=True)
    company_id = fields.Many2one("res.company", index=True, ondelete="restrict")
    active = fields.Boolean(default=True, tracking=True)
    step_ids = fields.One2many(
        "onehr.grade.step",
        "grade_id",
        string="Progression Steps",
    )
    position_count = fields.Integer(
        string="Positions",
        compute="_compute_position_count",
    )
    step_count = fields.Integer(string="Steps", compute="_compute_step_count")

    def _validate_scoped_code(self, label):
        return _validate_scoped_code(self, label)

    @api.constrains("code", "company_id")
    def _check_unique_code(self):
        self._validate_scoped_code(_("Grade"))

    def _compute_position_count(self):
        Position = self.env["onehr.position"]
        for record in self:
            record.position_count = Position.search_count(
                [("grade_id", "=", record.id)]
            )

    def _compute_step_count(self):
        for record in self:
            record.step_count = len(record.step_ids)

    def action_open_positions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Positions — %s", self.display_name),
            res_model="onehr.position",
            domain=[("grade_id", "=", self.id)],
            context={"default_grade_id": self.id},
        )

    def action_open_steps(self):
        self.ensure_one()
        return open_records_action(
            name=_("Grade Steps — %s", self.display_name),
            res_model="onehr.grade.step",
            domain=[("grade_id", "=", self.id)],
            context={"default_grade_id": self.id},
        )


class OneHRGradeStep(models.Model):
    _name = "onehr.grade.step"
    _description = "OneHR Grade Step"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "grade_id, sequence, code"

    grade_id = fields.Many2one(
        "onehr.grade",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    code = fields.Char(required=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related="grade_id.company_id",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    @api.constrains("grade_id", "code")
    def _check_unique_grade_code(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [
                    ("id", "!=", record.id),
                    ("grade_id", "=", record.grade_id.id),
                    ("code", "=ilike", record.code),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Grade-step code must be unique within a grade.")
                )


class OneHRPosition(models.Model):
    _name = "onehr.position"
    _description = "OneHR Enterprise Position"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, name"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    grade_id = fields.Many2one("onehr.grade", ondelete="restrict", tracking=True)
    work_location_id = fields.Many2one(
        "hr.work.location",
        ondelete="restrict",
        tracking=True,
    )
    authorized_fte = fields.Float(default=1.0, required=True, tracking=True)
    authorized_headcount = fields.Integer(default=1, required=True, tracking=True)
    status = fields.Selection(
        [
            ("planned", "Planned"),
            ("open", "Open"),
            ("filled", "Filled"),
            ("frozen", "Frozen"),
            ("closed", "Closed"),
        ],
        required=True,
        default="planned",
        tracking=True,
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    hierarchy_node_count = fields.Integer(
        string="Hierarchy Nodes",
        compute="_compute_hierarchy_node_count",
    )

    @api.constrains("code", "company_id")
    def _check_unique_code(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [
                    ("id", "!=", record.id),
                    ("company_id", "=", record.company_id.id),
                    ("code", "=ilike", record.code),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Position code must be unique within a company.")
                )

    @api.constrains("authorized_fte", "authorized_headcount")
    def _check_capacity(self):
        for record in self:
            if record.authorized_fte < 0:
                raise ValidationError(_("Authorized FTE cannot be negative."))
            if record.authorized_headcount < 0:
                raise ValidationError(
                    _("Authorized headcount cannot be negative.")
                )

    @api.constrains(
        "company_id",
        "job_id",
        "department_id",
        "grade_id",
        "work_location_id",
        "valid_from",
        "valid_to",
    )
    def _check_company_and_temporal_integrity(self):
        """Keep position scope and dates inside referenced master validity."""
        for record in self:
            for related in (
                record.job_id,
                record.department_id,
                record.grade_id,
                record.work_location_id,
            ):
                if (
                    related
                    and related.company_id
                    and related.company_id != record.company_id
                ):
                    raise ValidationError(
                        _(
                            "Position references must belong to the position "
                            "company or be global."
                        )
                    )

            for related in (
                record.job_id,
                record.department_id,
                record.work_location_id,
            ):
                if not related:
                    continue
                starts_too_early = related.onehr_valid_from > record.valid_from
                ends_too_late = (
                    related.onehr_valid_to
                    and (
                        not record.valid_to
                        or related.onehr_valid_to < record.valid_to
                    )
                )
                if starts_too_early or ends_too_late:
                    raise ValidationError(
                        _(
                            "Position validity must be contained by referenced "
                            "native records."
                        )
                    )

            if record.grade_id:
                grade = record.grade_id
                starts_too_early = grade.valid_from > record.valid_from
                ends_too_late = (
                    grade.valid_to
                    and (not record.valid_to or grade.valid_to < record.valid_to)
                )
                if starts_too_early or ends_too_late:
                    raise ValidationError(
                        _("Position validity must be contained by its grade validity.")
                    )

    def _compute_hierarchy_node_count(self):
        Node = self.env["onehr.position.hierarchy.node"]
        for record in self:
            record.hierarchy_node_count = Node.search_count(
                [("position_id", "=", record.id)]
            )

    def action_open_hierarchy_nodes(self):
        self.ensure_one()
        return open_records_action(
            name=_("Hierarchy Nodes — %s", self.display_name),
            res_model="onehr.position.hierarchy.node",
            domain=[("position_id", "=", self.id)],
            context={"default_position_id": self.id},
        )
