import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action


# Odoo 19 builds registry classes dynamically. Keep reusable compatibility
# behavior in module-level helpers instead of plain-Python model base classes.
def _onehr_is_effective_on(record, as_of_date=None):
    record.ensure_one()
    as_of_date = fields.Date.to_date(
        as_of_date or fields.Date.context_today(record)
    )
    return record.onehr_valid_from <= as_of_date and (
        not record.onehr_valid_to or record.onehr_valid_to >= as_of_date
    )


def _onehr_effective_domain(recordset, as_of_date=None):
    as_of_date = fields.Date.to_date(
        as_of_date or fields.Date.context_today(recordset)
    )
    return [
        ("onehr_valid_from", "<=", as_of_date),
        "|",
        ("onehr_valid_to", "=", False),
        ("onehr_valid_to", ">=", as_of_date),
    ]


def _check_onehr_valid_interval(records):
    for record in records:
        if (
            record.onehr_valid_to
            and record.onehr_valid_to < record.onehr_valid_from
        ):
            raise ValidationError(
                _("OneHR Valid To must be on or after OneHR Valid From.")
            )


class HrDepartment(models.Model):
    _inherit = "hr.department"

    onehr_code = fields.Char(index=True, tracking=True)
    onehr_unit_type = fields.Selection(
        [
            ("division", "Division"),
            ("department", "Department"),
            ("section", "Section"),
            ("team", "Team"),
            ("other", "Other"),
        ],
        default="department",
        tracking=True,
    )
    onehr_valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    onehr_valid_to = fields.Date(index=True, tracking=True)
    onehr_position_count = fields.Integer(
        string="Positions",
        compute="_compute_onehr_position_count",
    )

    def onehr_is_effective_on(self, as_of_date=None):
        return _onehr_is_effective_on(self, as_of_date)

    @api.model
    def onehr_effective_domain(self, as_of_date=None):
        return _onehr_effective_domain(self, as_of_date)

    @api.constrains("onehr_valid_from", "onehr_valid_to")
    def _check_onehr_valid_interval(self):
        _check_onehr_valid_interval(self)

    def _compute_onehr_position_count(self):
        Position = self.env["onehr.position"]
        for record in self:
            record.onehr_position_count = Position.search_count(
                [("department_id", "=", record.id)]
            )

    def action_open_onehr_positions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Positions — %s", self.display_name),
            res_model="onehr.position",
            domain=[("department_id", "=", self.id)],
            context={"default_department_id": self.id},
        )


class HrJob(models.Model):
    _inherit = "hr.job"

    onehr_code = fields.Char(index=True, tracking=True)
    onehr_job_family_id = fields.Many2one(
        "onehr.job.family",
        ondelete="restrict",
        tracking=True,
    )
    onehr_grade_ids = fields.Many2many(
        "onehr.grade",
        string="Valid Grades",
        tracking=True,
    )
    onehr_valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    onehr_valid_to = fields.Date(index=True, tracking=True)
    onehr_position_count = fields.Integer(
        string="Positions",
        compute="_compute_onehr_position_count",
    )

    def onehr_is_effective_on(self, as_of_date=None):
        return _onehr_is_effective_on(self, as_of_date)

    @api.model
    def onehr_effective_domain(self, as_of_date=None):
        return _onehr_effective_domain(self, as_of_date)

    @api.constrains("onehr_valid_from", "onehr_valid_to")
    def _check_onehr_valid_interval(self):
        _check_onehr_valid_interval(self)

    def _compute_onehr_position_count(self):
        Position = self.env["onehr.position"]
        for record in self:
            record.onehr_position_count = Position.search_count(
                [("job_id", "=", record.id)]
            )

    def action_open_onehr_positions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Positions — %s", self.display_name),
            res_model="onehr.position",
            domain=[("job_id", "=", self.id)],
            context={"default_job_id": self.id},
        )


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

    onehr_site_code = fields.Char(index=True)
    onehr_timezone = fields.Selection(
        selection=lambda self: [(tz, tz) for tz in pytz.all_timezones],
        string="Timezone",
    )
    onehr_latitude = fields.Float(digits=(10, 7))
    onehr_longitude = fields.Float(digits=(10, 7))
    onehr_business_metadata = fields.Text()
    onehr_valid_from = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    onehr_valid_to = fields.Date(index=True)
    onehr_position_count = fields.Integer(
        string="Positions",
        compute="_compute_onehr_position_count",
    )

    def onehr_is_effective_on(self, as_of_date=None):
        return _onehr_is_effective_on(self, as_of_date)

    @api.model
    def onehr_effective_domain(self, as_of_date=None):
        return _onehr_effective_domain(self, as_of_date)

    @api.constrains("onehr_valid_from", "onehr_valid_to")
    def _check_onehr_valid_interval(self):
        _check_onehr_valid_interval(self)

    @api.constrains("onehr_latitude", "onehr_longitude")
    def _check_coordinates(self):
        for record in self:
            if not -90 <= record.onehr_latitude <= 90:
                raise ValidationError(_("Latitude must be between -90 and 90."))
            if not -180 <= record.onehr_longitude <= 180:
                raise ValidationError(
                    _("Longitude must be between -180 and 180.")
                )

    def _compute_onehr_position_count(self):
        Position = self.env["onehr.position"]
        for record in self:
            record.onehr_position_count = Position.search_count(
                [("work_location_id", "=", record.id)]
            )

    def action_open_onehr_positions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Positions — %s", self.display_name),
            res_model="onehr.position",
            domain=[("work_location_id", "=", self.id)],
            context={"default_work_location_id": self.id},
        )
