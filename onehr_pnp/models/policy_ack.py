
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import open_record_action


class OneHRPolicyAcknowledgement(models.Model):
    _name = "onehr.policy.ack"
    _description = "OneHR Policy Acknowledgement"
    _inherit = ["onehr.mixin.audit"]
    _order = "state, due_date, department_name, employee_name"

    _policy_employee_ack_uniq = models.Constraint(
        "UNIQUE(policy_id, employee_id)",
        "An employee can have only one acknowledgement assignment per policy version.",
    )

    _ACTION_CONTEXT = "onehr_pnp_ack_action"

    policy_id = fields.Many2one(
        "onehr.policy",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="policy_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    policy_code = fields.Char(
        related="policy_id.policy_code",
        store=True,
        readonly=True,
        index=True,
    )
    policy_title = fields.Char(
        related="policy_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    policy_version = fields.Integer(
        related="policy_id.version_no",
        store=True,
        readonly=True,
        index=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        readonly=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_pnp.group_onehr_pnp_compliance",
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
        groups="onehr_pnp.group_onehr_pnp_compliance",
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
        groups="onehr_pnp.group_onehr_pnp_compliance",
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
            ("not_required", "Not Required"),
        ],
        default="pending",
        required=True,
        readonly=True,
        tracking=True,
        index=True,
    )
    published_at = fields.Datetime(
        related="policy_id.published_at",
        store=True,
        readonly=True,
        index=True,
    )
    due_date = fields.Date(
        required=True,
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
    )
    last_reminder_at = fields.Datetime(
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    reminder_count = fields.Integer(
        default=0,
        readonly=True,
        copy=False,
        groups="onehr_pnp.group_onehr_pnp_owner",
    )
    days_to_ack = fields.Float(
        compute="_compute_days_to_ack",
        store=True,
        string="Days to Acknowledge",
    )
    evidence_ids = fields.One2many(
        "onehr.policy.evidence",
        "ack_id",
        string="Compliance Evidence",
        readonly=True,
    )
    verified_evidence_count = fields.Integer(
        compute="_compute_evidence_count",
        store=True,
    )

    @api.depends("published_at", "acknowledged_at")
    def _compute_days_to_ack(self):
        for ack in self:
            if ack.published_at and ack.acknowledged_at:
                elapsed = ack.acknowledged_at - ack.published_at
                ack.days_to_ack = elapsed.total_seconds() / 86400.0
            else:
                ack.days_to_ack = 0.0

    @api.depends("evidence_ids.state")
    def _compute_evidence_count(self):
        for ack in self:
            ack.verified_evidence_count = len(
                ack.evidence_ids.filtered(
                    lambda evidence: evidence.state == "verified"
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_pnp_publish_ack_creation"):
            raise AccessError(
                _("Policy acknowledgement assignments are generated only by controlled publication.")
            )

        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            policy = self.env["onehr.policy"].browse(
                vals.get("policy_id")
            ).exists()
            employee = self.env["hr.employee"].browse(
                vals.get("employee_id")
            ).exists()
            if not policy or not employee:
                raise ValidationError(
                    _("A valid Policy and Employee are required.")
                )
            if policy.state != "approved":
                raise ValidationError(
                    _("Acknowledgement assignments can be generated only while publishing an Approved policy.")
                )
            if employee.company_id != policy.company_id:
                raise ValidationError(
                    _("Acknowledgement employee and policy company must match.")
                )
            vals["state"] = (
                "pending"
                if policy.acknowledgement_required
                else "not_required"
            )
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)
        raise AccessError(
            _("Policy acknowledgement evidence changes only through governed actions.")
        )

    def action_acknowledge(self):
        now = fields.Datetime.now()
        source = self.env.context.get("onehr_pnp_ack_source", "backend")
        if source not in ("backend", "portal", "api"):
            source = "backend"

        for ack in self:
            if ack.state == "acknowledged":
                continue
            if ack.state == "not_required":
                raise UserError(
                    _("Acknowledgement is not required for this policy version.")
                )
            if (
                ack.policy_id.state not in ("published", "review")
                or not ack.policy_id.is_current
            ):
                raise UserError(
                    _("Only the current Published/Review policy can be acknowledged.")
                )
            if not ack.employee_user_id or ack.employee_user_id != self.env.user:
                raise AccessError(
                    _("You may acknowledge only your own policy assignment.")
                )

            ack.with_context(
                **{self._ACTION_CONTEXT: True}
            ).write(
                {
                    "state": "acknowledged",
                    "acknowledged_at": now,
                    "acknowledged_by_id": self.env.user.id,
                    "acknowledgement_source": source,
                    "acknowledgement_comment": self.env.context.get(
                        "onehr_pnp_ack_comment"
                    )
                    or False,
                }
            )

            own_activities = ack.activity_ids.filtered(
                lambda activity: activity.user_id == self.env.user
            )
            if own_activities:
                own_activities.action_feedback(
                    feedback=_("Policy read and acknowledged.")
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OneHR Policies & Procedures"),
                "message": _("Policy acknowledgement recorded with timestamp."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_policy(self):
        self.ensure_one()
        return open_record_action(
            name=_("Policy / Procedure"),
            res_model="onehr.policy",
            res_id=self.policy_id.id,
        )

    def action_open_evidence(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("My Policy Evidence"),
            "res_model": "onehr.policy.evidence",
            "view_mode": "list,form",
            "domain": [("ack_id", "=", self.id)],
            "context": {
                "default_policy_id": self.policy_id.id,
                "default_ack_id": self.id,
            },
        }

    @api.ondelete(at_uninstall=False)
    def _retain_acknowledgement_evidence(self):
        raise AccessError(
            _("Policy acknowledgement assignments/evidence are retained and cannot be deleted.")
        )

