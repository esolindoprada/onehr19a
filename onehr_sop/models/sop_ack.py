
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import open_record


class OneHRSOPAcknowledgement(models.Model):
    _name = "onehr.sop.ack"
    _description = "OneHR SOP Acknowledgement"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, department_name, employee_name"

    _sop_ack_employee_uniq = models.Constraint(
        "UNIQUE(version_id, employee_id)",
        "An employee can acknowledge an SOP version only once.",
    )

    _ACTION_CONTEXT = "onehr_sop_ack_action_write"

    version_id = fields.Many2one(
        "onehr.sop.version",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    sop_id = fields.Many2one(
        "onehr.sop",
        related="version_id.sop_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="version_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        readonly=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    employee_name = fields.Char(
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        string="Employee",
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="employee_id.user_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    job_name = fields.Char(
        related="employee_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("acknowledged", "Acknowledged"),
        ],
        default="pending",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    published_at = fields.Datetime(
        related="version_id.published_at",
        store=True,
        readonly=True,
        index=True,
    )
    acknowledged_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    acknowledged_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        tracking=True,
    )
    acknowledged_by_name = fields.Char(
        related="acknowledged_by_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    acknowledgement_source = fields.Selection(
        [
            ("backend", "OneHR Backend"),
            ("portal", "Employee Portal"),
            ("api", "Integration API"),
        ],
        readonly=True,
        copy=False,
        tracking=True,
    )
    acknowledgement_comment = fields.Text(
        readonly=True,
        copy=False,
        tracking=True,
        help="Optional employee comment supplied at acknowledgement time through a governed client.",
    )
    days_to_ack = fields.Float(
        compute="_compute_days_to_ack",
        store=True,
        string="Days to Acknowledge",
    )
    last_reminder_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_sop.group_onehr_sop_editor",
    )
    reminder_count = fields.Integer(
        readonly=True,
        copy=False,
        default=0,
        groups="onehr_sop.group_onehr_sop_editor",
    )

    @api.depends("published_at", "acknowledged_at")
    def _compute_days_to_ack(self):
        for record in self:
            if record.published_at and record.acknowledged_at:
                elapsed = record.acknowledged_at - record.published_at
                record.days_to_ack = elapsed.total_seconds() / 86400.0
            else:
                record.days_to_ack = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(
            "onehr_sop_publish_ack_creation"
        ):
            raise AccessError(
                _("Acknowledgement records are generated only by controlled SOP publication.")
            )

        records = self.browse()
        for incoming in vals_list:
            vals = dict(incoming)
            version = self.env["onehr.sop.version"].browse(
                vals.get("version_id")
            ).exists()
            employee = self.env["hr.employee"].browse(
                vals.get("employee_id")
            ).exists()
            if not version or not employee:
                raise ValidationError(
                    _("A valid SOP version and employee are required.")
                )
            if version.state != "approved":
                raise ValidationError(
                    _("Acknowledgement evidence can be generated only while publishing an Approved SOP.")
                )
            if employee.company_id != version.company_id:
                raise ValidationError(
                    _("Acknowledgement employee and SOP company must match.")
                )
            vals["state"] = "pending"
            records |= super(OneHRSOPAcknowledgement, self).create(vals)
        return records

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)
        raise AccessError(
            _("SOP acknowledgement evidence can change only through Read & Agree.")
        )

    def action_acknowledge(self):
        now = fields.Datetime.now()
        source = self.env.context.get(
            "onehr_sop_ack_source",
            "backend",
        )
        if source not in ("backend", "portal", "api"):
            source = "backend"

        for record in self:
            if record.state == "acknowledged":
                continue
            if record.version_id.state != "published" or not record.version_id.is_current:
                raise UserError(
                    _("Only the current Published SOP version can be acknowledged.")
                )
            if not record.employee_user_id or record.employee_user_id != self.env.user:
                raise AccessError(
                    _("You may acknowledge only your own assigned SOP.")
                )

            comment = self.env.context.get("onehr_sop_ack_comment")
            record.with_context(
                **{self._ACTION_CONTEXT: True}
            ).write(
                {
                    "state": "acknowledged",
                    "acknowledged_at": now,
                    "acknowledged_by_id": self.env.user.id,
                    "acknowledgement_source": source,
                    "acknowledgement_comment": comment or False,
                }
            )
            own_activities = record.activity_ids.filtered(
                lambda activity: activity.user_id == self.env.user
            )
            if own_activities:
                own_activities.action_feedback(
                    feedback=_("SOP read and acknowledged.")
                )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OneHR SOP"),
                "message": _("Read & Agree acknowledgement recorded with timestamp."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_sop_version(self):
        self.ensure_one()
        return open_record(
            name=_("Published SOP"),
            res_model="onehr.sop.version",
            res_id=self.version_id.id,
        )

    def action_open_employee(self):
        self.ensure_one()
        if not self.env.user.has_group("onehr_sop.group_onehr_sop_editor"):
            raise AccessError(_("Employee drill-down requires SOP Editor / QA authority."))
        return open_record(
            name=self.employee_name,
            res_model="hr.employee",
            res_id=self.employee_id.id,
        )

    @api.ondelete(at_uninstall=False)
    def _retain_acknowledgement_evidence(self):
        raise AccessError(
            _("SOP acknowledgement evidence is retained and cannot be deleted.")
        )

