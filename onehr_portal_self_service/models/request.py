
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_portal_admin,
    is_portal_hr,
    is_portal_manager,
    open_records_action,
    require_portal_admin,
    require_portal_hr,
)
from .request_stage import REQUEST_STATES


FINAL_STATES = {"done", "rejected", "cancelled"}
OPEN_STATES = {"submitted", "manager_review", "hr_review", "approved", "processing"}
LIFECYCLE_FIELDS = {
    "state",
    "stage_id",
    "submitted_at",
    "submitted_by_id",
    "manager_decision_at",
    "manager_decision_by_id",
    "manager_decision_note",
    "hr_decision_at",
    "hr_decision_by_id",
    "hr_decision_note",
    "processing_started_at",
    "processing_started_by_id",
    "completed_at",
    "completed_by_id",
    "cancelled_at",
    "cancelled_by_id",
    "integration_model",
    "integration_res_id",
    "integration_reference",
    "integration_status",
    "integration_message",
    "integration_last_attempt_at",
    "integration_last_attempt_by_id",
    "sla_deadline",
    "sla_reminder_sent_at",
}


class OneHRPortalRequest(models.Model):
    _name = "onehr.portal.request"
    _description = "OneHR Portal Self-Service Request"
    _inherit = ["onehr.mixin.audit"]
    _order = "priority desc, submitted_at desc, id desc"
    _rec_name = "name"

    _reference_unique = models.Constraint(
        "unique(name)",
        "Portal Request Reference must be unique.",
    )

    name = fields.Char(
        string="Request Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    type_id = fields.Many2one(
        "onehr.portal.request.type",
        string="Request Type",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=False,
    )
    service_kind = fields.Selection(
        related="type_id.service_kind",
        store=True,
        readonly=True,
        index=True,
    )
    stage_id = fields.Many2one(
        "onehr.portal.request.stage",
        ondelete="restrict",
        index=True,
        tracking=True,
        copy=False,
    )
    state = fields.Selection(
        REQUEST_STATES,
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Low"), ("2", "High"), ("3", "Urgent")],
        required=True,
        default="0",
        index=True,
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )
    employee_name = fields.Char(
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="employee_id.user_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_name = fields.Char(
        related="employee_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    manager_employee_id = fields.Many2one(
        "hr.employee",
        string="Direct Manager",
        related="employee_id.parent_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )
    manager_name = fields.Char(
        related="employee_id.parent_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    manager_user_id = fields.Many2one(
        "res.users",
        related="employee_id.parent_id.user_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    hr_responsible_user_id = fields.Many2one(
        "res.users",
        related="type_id.responsible_user_id",
        store=True,
        readonly=True,
        index=True,
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )

    subject = fields.Char(required=True, tracking=True, index=True)
    description = fields.Text(required=True, tracking=True)
    employee_note = fields.Text(tracking=True)
    internal_note = fields.Html(
        tracking=True,
        sanitize=True,
        groups="onehr_portal_self_service.group_onehr_portal_hr",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_port_req_att_rel",
        "request_id",
        "attachment_id",
        string="Supporting Attachments",
        copy=False,
    )
    attachment_count = fields.Integer(compute="_compute_attachment_count")

    requested_date_from = fields.Date(string="Requested From", tracking=True)
    requested_date_to = fields.Date(string="Requested To", tracking=True)
    leave_type_code = fields.Char(
        string="Leave Type Code",
        tracking=True,
        help="Exact OneHR Time Off leave type code used by the optional downstream hand-off.",
    )
    learning_session_reference = fields.Char(
        string="Learning Session Reference",
        tracking=True,
        help="Exact OneHR Learning Session reference used by the optional downstream hand-off.",
    )
    document_category_code = fields.Char(
        string="Document Category Code",
        tracking=True,
        help="Exact OneHR Document category code used by the optional downstream hand-off.",
    )
    document_title = fields.Char(tracking=True)
    profile_change_json = fields.Json(
        string="Requested Profile Changes",
        copy=False,
        help="Requested self-service profile changes. Values are applied only after governed HR approval.",
    )

    submitted_at = fields.Datetime(readonly=True, copy=False, index=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    manager_decision_at = fields.Datetime(readonly=True, copy=False)
    manager_decision_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    manager_decision_note = fields.Text(readonly=True, copy=False)
    hr_decision_at = fields.Datetime(readonly=True, copy=False)
    hr_decision_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    hr_decision_note = fields.Text(readonly=True, copy=False)
    processing_started_at = fields.Datetime(readonly=True, copy=False)
    processing_started_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    completed_at = fields.Datetime(readonly=True, copy=False, index=True)
    completed_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    cancelled_at = fields.Datetime(readonly=True, copy=False)
    cancelled_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")

    sla_deadline = fields.Datetime(readonly=True, copy=False, index=True)
    sla_reminder_sent_at = fields.Datetime(readonly=True, copy=False)
    is_sla_overdue = fields.Boolean(
        compute="_compute_sla_status",
        search="_search_is_sla_overdue",
    )
    sla_status = fields.Selection(
        [
            ("none", "No SLA"),
            ("on_track", "On Track"),
            ("due_soon", "Due Soon"),
            ("overdue", "Overdue"),
            ("met", "Completed Within SLA"),
            ("breached", "Completed After SLA"),
        ],
        compute="_compute_sla_status",
    )
    sla_remaining_hours = fields.Float(compute="_compute_sla_status")

    integration_model = fields.Char(readonly=True, copy=False, index=True)
    integration_res_id = fields.Integer(readonly=True, copy=False, index=True)
    integration_reference = fields.Char(readonly=True, copy=False, index=True)
    integration_status = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("pending", "Pending"),
            ("success", "Success"),
            ("error", "Needs Attention"),
        ],
        default="not_applicable",
        readonly=True,
        copy=False,
        index=True,
    )
    integration_message = fields.Text(readonly=True, copy=False)
    integration_last_attempt_at = fields.Datetime(readonly=True, copy=False)
    integration_last_attempt_by_id = fields.Many2one(
        "res.users", readonly=True, copy=False, ondelete="restrict"
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        own_employee = self.env.user.employee_id
        actor_is_hr = is_portal_hr(self.env)

        for incoming in vals_list:
            values = dict(incoming)
            if values.get("state", "draft") != "draft":
                raise AccessError(_("Portal Requests must be created in Draft and advanced through governed actions."))

            employee = self.env["hr.employee"].browse(values.get("employee_id")).exists()
            if not employee:
                employee = own_employee
            if not employee:
                raise ValidationError(_("The current user is not linked to an employee. HR must create the request."))

            if not actor_is_hr and employee != own_employee:
                raise AccessError(_("Employees may create self-service requests only for themselves."))
            if not actor_is_hr and not self.env.user.onehr_portal_self_service_enabled:
                raise AccessError(_("Self-service is disabled for this employee account."))

            request_type = self.env["onehr.portal.request.type"].browse(values.get("type_id")).exists()
            if not request_type:
                raise ValidationError(_("A valid Request Type is required."))
            if request_type.company_id and request_type.company_id != employee.company_id:
                raise ValidationError(_("The Request Type is not available in the employee company."))
            if not actor_is_hr and (not request_type.active or not request_type.portal_enabled):
                raise AccessError(_("This Request Type is not available in self-service."))

            values["employee_id"] = employee.id
            values["company_id"] = employee.company_id.id
            values.setdefault("priority", request_type.default_priority)
            # The initial stage is always system-derived. Caller-supplied stage data
            # must never create a Draft request that visually claims another state.
            values["stage_id"] = self._find_stage("draft", employee.company_id).id or False
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.portal.request") or _("New")
            prepared.append(values)

        records = super().create(prepared)
        records._validate_request_payload(submission=False)
        return records

    def write(self, vals):
        values = dict(vals)
        if LIFECYCLE_FIELDS & set(values):
            raise AccessError(_("Lifecycle, SLA, decision and integration evidence must change through governed actions."))

        immutable_ownership_fields = {"company_id", "employee_id"}
        if immutable_ownership_fields & set(values):
            raise AccessError(_("Request company and employee ownership are immutable after creation."))
        if "type_id" in values:
            for record in self:
                if record.state != "draft":
                    raise AccessError(_("Request Type can be changed only while the request is Draft."))

        actor_is_hr = is_portal_hr(self.env)
        editable_business_fields = {
            "type_id",
            "priority",
            "subject",
            "description",
            "employee_note",
            "attachment_ids",
            "requested_date_from",
            "requested_date_to",
            "leave_type_code",
            "learning_session_reference",
            "document_category_code",
            "document_title",
            "profile_change_json",
            "message_follower_ids",
        }
        hr_extra_fields = {"internal_note"}

        for record in self:
            if actor_is_hr:
                if record.state in FINAL_STATES and (set(values) & editable_business_fields):
                    raise AccessError(_("Completed/rejected/cancelled request facts are frozen as audit evidence."))
                continue

            if record.employee_user_id != self.env.user:
                raise AccessError(_("You may update only your own self-service request."))
            if record.state != "draft":
                raise AccessError(_("Employees may edit request details only while the request is Draft."))
            if set(values) - editable_business_fields:
                raise AccessError(_("The requested fields exceed employee self-service authority."))

        if not actor_is_hr and hr_extra_fields & set(values):
            raise AccessError(_("Internal HR notes are restricted to Portal HR."))

        result = super().write(values)
        if set(values) & editable_business_fields:
            self._validate_request_payload(submission=False)
        return result

    @api.constrains("company_id", "type_id", "stage_id")
    def _check_company_scope(self):
        for record in self:
            if record.employee_id and record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Portal Request company must follow the employee company."))
            if record.type_id.company_id and record.type_id.company_id != record.company_id:
                raise ValidationError(_("Request Type company scope must match the request company."))
            if record.stage_id.company_id and record.stage_id.company_id != record.company_id:
                raise ValidationError(_("Request Stage company scope must match the request company."))

    @api.constrains("type_id", "company_id", "stage_id", "state")
    def _check_catalog_alignment(self):
        for record in self:
            if record.type_id.company_id and record.type_id.company_id != record.company_id:
                raise ValidationError(_("Request Type company must match the Portal Request company."))
            if record.stage_id:
                if record.stage_id.company_id and record.stage_id.company_id != record.company_id:
                    raise ValidationError(_("Request Stage company must match the Portal Request company."))
                if record.stage_id.state_key != record.state:
                    raise ValidationError(_("Request Stage must represent the same lifecycle state as the Portal Request."))

    @api.constrains("requested_date_from", "requested_date_to")
    def _check_requested_dates(self):
        for record in self:
            if (
                record.requested_date_from
                and record.requested_date_to
                and record.requested_date_from > record.requested_date_to
            ):
                raise ValidationError(_("Requested From cannot be after Requested To."))

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.depends("sla_deadline", "state", "completed_at", "type_id.reminder_hours_before")
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_sla_overdue = False
            record.sla_remaining_hours = 0.0
            if not record.sla_deadline:
                record.sla_status = "none"
                continue

            end_time = record.completed_at or now
            delta_hours = (record.sla_deadline - end_time).total_seconds() / 3600.0
            record.sla_remaining_hours = delta_hours

            if record.state == "done":
                record.sla_status = "met" if record.completed_at and record.completed_at <= record.sla_deadline else "breached"
            elif record.state in {"rejected", "cancelled"}:
                record.sla_status = "none"
            elif now > record.sla_deadline:
                record.is_sla_overdue = True
                record.sla_status = "overdue"
            elif record.type_id.reminder_hours_before and delta_hours <= record.type_id.reminder_hours_before:
                record.sla_status = "due_soon"
            else:
                record.sla_status = "on_track"

    @api.model
    def _search_is_sla_overdue(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(_("SLA overdue search supports only boolean equality."))
        overdue_domain = [
            ("sla_deadline", "!=", False),
            ("sla_deadline", "<", fields.Datetime.now()),
            ("state", "in", tuple(OPEN_STATES)),
        ]
        wants_overdue = value if operator == "=" else not value
        if wants_overdue:
            return overdue_domain
        return [
            "|", "|",
            ("sla_deadline", "=", False),
            ("sla_deadline", ">=", fields.Datetime.now()),
            ("state", "not in", tuple(OPEN_STATES)),
        ]

    @api.model
    def _find_stage(self, state, company):
        Stage = self.env["onehr.portal.request.stage"]
        stage = Stage.search(
            [
                ("state_key", "=", state),
                ("active", "=", True),
                ("company_id", "=", company.id),
            ],
            order="sequence, id",
            limit=1,
        )
        if not stage:
            stage = Stage.search(
                [
                    ("state_key", "=", state),
                    ("active", "=", True),
                    ("company_id", "=", False),
                ],
                order="sequence, id",
                limit=1,
            )
        return stage

    def _write_governed(self, values):
        """Private lifecycle writer. Public RPC write never accepts protected evidence fields."""
        return super(OneHRPortalRequest, self).write(values)

    def _set_state(self, state, extra=None):
        values = dict(extra or {})
        values["state"] = state
        for record in self:
            stage = record._find_stage(state, record.company_id)
            record_values = dict(values)
            record_values["stage_id"] = stage.id or False
            record._write_governed(record_values)
        return True

    def _validate_request_payload(self, submission=False):
        for record in self:
            if record.service_kind == "timeoff":
                if submission and not all((record.leave_type_code, record.requested_date_from, record.requested_date_to)):
                    raise ValidationError(_("Time Off requests require Leave Type Code, Requested From and Requested To."))
            elif record.service_kind == "learning":
                if submission and not record.learning_session_reference:
                    raise ValidationError(_("Learning requests require an exact Learning Session Reference."))
            elif record.service_kind == "document":
                if submission and not record.document_category_code:
                    raise ValidationError(_("Document requests require a Document Category Code."))
                if submission and not record.attachment_ids:
                    raise ValidationError(_("Document requests require at least one supporting attachment."))
            elif record.service_kind == "profile_change":
                if submission and not record.profile_change_json:
                    raise ValidationError(_("Profile Change requests require at least one requested field change."))
        return True

    def _require_employee_owner_or_hr(self):
        for record in self:
            if is_portal_hr(self.env):
                continue
            if record.employee_user_id != self.env.user:
                raise AccessError(_("This action is restricted to the request owner or Portal HR."))

    def _require_manager_for_request(self):
        for record in self:
            if is_portal_hr(self.env):
                continue
            if not is_portal_manager(self.env) or record.manager_user_id != self.env.user:
                raise AccessError(_("Only the employee's assigned direct manager may make this decision."))

    def _post_transition_message(self, body):
        for record in self:
            record.message_post(body=body, subtype_xmlid="mail.mt_comment")

    def _schedule_internal_activity(self, user, summary, deadline=None):
        """Schedule an internal activity only from an internal execution context.

        Portal employees/managers are intentionally external users. Their request or
        approval must never fail merely because ``mail.activity`` is an internal-user
        facility. The hourly SLA monitor runs internally and can create the HR follow-up
        activity later when needed.
        """
        self.ensure_one()
        actor_is_internal = self.env.is_superuser() or self.env.user.has_group("base.group_user")
        if not actor_is_internal or not user or not user.has_group("base.group_user"):
            return False
        existing = self.activity_ids.filtered(
            lambda activity: activity.user_id == user and activity.summary == summary
        )
        if existing:
            return existing[:1]
        return self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=summary,
            date_deadline=deadline or fields.Date.context_today(self),
        )

    def _handle_approved_integration(self):
        """Run auto-execution only when the current actor has Portal HR authority.

        Final approval may legally be recorded by an employee flow with no approval
        requirement, or by a Portal Manager when HR approval is not required. Those
        external actors must not be escalated into downstream HR authority. Instead the
        request remains Approved with a transparent Pending integration for an authorized
        Portal HR operator to execute.
        """
        self.ensure_one()
        if not self.type_id.auto_execute_on_approval or self.service_kind == "generic":
            return False
        if is_portal_hr(self.env):
            return self._dispatch_integration(raise_on_error=False)

        self._write_governed(
            {
                "integration_status": "pending",
                "integration_message": _(
                    "Approved. Downstream execution is pending an authorized Portal HR operator."
                ),
            }
        )
        return False

    def action_submit(self):
        self._require_employee_owner_or_hr()
        now = fields.Datetime.now()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a Draft request can be submitted."))
            if not record.type_id.active:
                raise UserError(_("The selected Request Type is no longer active."))
            record._validate_request_payload(submission=True)

            deadline = now + timedelta(hours=record.type_id.sla_hours) if record.type_id.sla_hours else False
            values = {
                "submitted_at": now,
                "submitted_by_id": self.env.user.id,
                "sla_deadline": deadline,
                "sla_reminder_sent_at": False,
                "integration_status": "pending" if record.service_kind != "generic" else "not_applicable",
            }
            if record.type_id.manager_approval_required and record.manager_user_id:
                next_state = "manager_review"
            elif record.type_id.hr_approval_required:
                next_state = "hr_review"
            else:
                next_state = "approved"
            record._set_state(next_state, values)
            record._post_transition_message(record.type_id.submission_message or _("Request submitted."))

            if next_state == "manager_review":
                record._schedule_internal_activity(record.manager_user_id, _("Review HR self-service request"))
            elif next_state == "hr_review":
                record._schedule_internal_activity(record.hr_responsible_user_id, _("Review HR self-service request"))
            elif next_state == "approved":
                record._handle_approved_integration()
        return display_notification(_("Request submitted successfully."))

    def action_manager_approve(self, note=None):
        self._require_manager_for_request()
        now = fields.Datetime.now()
        for record in self:
            if record.state != "manager_review":
                raise UserError(_("Only a request awaiting Manager Review can be approved by a manager."))
            next_state = "hr_review" if record.type_id.hr_approval_required else "approved"
            record._set_state(
                next_state,
                {
                    "manager_decision_at": now,
                    "manager_decision_by_id": self.env.user.id,
                    "manager_decision_note": note or "",
                },
            )
            record._post_transition_message(record.type_id.approval_message or _("Manager approval recorded."))
            if next_state == "hr_review":
                record._schedule_internal_activity(record.hr_responsible_user_id, _("Review manager-approved HR request"))
            else:
                record._handle_approved_integration()
        return display_notification(_("Manager approval recorded."))

    def action_manager_reject(self, note=None):
        self._require_manager_for_request()
        if not (note or "").strip():
            raise ValidationError(_("A rejection note is required."))
        for record in self:
            if record.state != "manager_review":
                raise UserError(_("Only a request awaiting Manager Review can be rejected by a manager."))
            record._set_state(
                "rejected",
                {
                    "manager_decision_at": fields.Datetime.now(),
                    "manager_decision_by_id": self.env.user.id,
                    "manager_decision_note": note.strip(),
                    "integration_status": "not_applicable",
                },
            )
            record._post_transition_message(record.type_id.rejection_message or _("Request rejected by manager."))
        return display_notification(_("Request rejected."), notification_type="warning")

    def action_hr_approve(self, note=None):
        require_portal_hr(self)
        for record in self:
            if record.state not in ("hr_review", "submitted"):
                raise UserError(_("Only a request awaiting HR Review can be approved by HR."))
            record._set_state(
                "approved",
                {
                    "hr_decision_at": fields.Datetime.now(),
                    "hr_decision_by_id": self.env.user.id,
                    "hr_decision_note": note or "",
                },
            )
            record._post_transition_message(record.type_id.approval_message or _("HR approval recorded."))
            record._handle_approved_integration()
        return display_notification(_("HR approval recorded."))

    def action_hr_reject(self, note=None):
        require_portal_hr(self)
        if not (note or "").strip():
            raise ValidationError(_("A rejection note is required."))
        for record in self:
            if record.state not in ("hr_review", "submitted"):
                raise UserError(_("Only a request awaiting HR Review can be rejected by HR."))
            record._set_state(
                "rejected",
                {
                    "hr_decision_at": fields.Datetime.now(),
                    "hr_decision_by_id": self.env.user.id,
                    "hr_decision_note": note.strip(),
                    "integration_status": "not_applicable",
                },
            )
            record._post_transition_message(record.type_id.rejection_message or _("Request rejected by HR."))
        return display_notification(_("Request rejected."), notification_type="warning")

    def action_start_processing(self):
        require_portal_hr(self)
        for record in self:
            if record.state != "approved":
                raise UserError(_("Only an Approved request can move to Processing."))
            record._set_state(
                "processing",
                {
                    "processing_started_at": fields.Datetime.now(),
                    "processing_started_by_id": self.env.user.id,
                },
            )
        return display_notification(_("Request moved to Processing."))

    def action_complete(self):
        require_portal_hr(self)
        for record in self:
            if record.state not in ("approved", "processing"):
                raise UserError(_("Only an Approved or Processing request can be completed."))
            record._set_state(
                "done",
                {
                    "completed_at": fields.Datetime.now(),
                    "completed_by_id": self.env.user.id,
                },
            )
            record._post_transition_message(record.type_id.completion_message or _("Request completed."))
        return display_notification(_("Request completed."))

    def action_cancel(self):
        self._require_employee_owner_or_hr()
        for record in self:
            if record.state in ("done", "rejected", "cancelled"):
                raise UserError(_("This request can no longer be cancelled."))
            if not is_portal_hr(self.env) and record.state in ("approved", "processing"):
                raise AccessError(_("Only Portal HR may cancel an approved or processing request."))
            record._set_state(
                "cancelled",
                {
                    "cancelled_at": fields.Datetime.now(),
                    "cancelled_by_id": self.env.user.id,
                    "integration_status": "not_applicable" if not record.integration_res_id else record.integration_status,
                },
            )
            record._post_transition_message(_("Request cancelled."))
        return display_notification(_("Request cancelled."), notification_type="warning")

    def action_execute_integration(self):
        require_portal_hr(self)
        for record in self:
            if record.state not in ("approved", "processing"):
                raise UserError(_("Downstream execution is available only for Approved or Processing requests."))
            record._dispatch_integration(raise_on_error=True)
        return display_notification(_("Downstream integration completed."))

    def action_retry_integration(self):
        require_portal_hr(self)
        return self.action_execute_integration()

    def action_refresh_sla(self):
        self.invalidate_recordset(["is_sla_overdue", "sla_status", "sla_remaining_hours"])
        return display_notification(_("SLA status refreshed."), notification_type="info")

    def action_schedule_sla_activity(self):
        require_portal_hr(self)
        for record in self:
            owner = record.hr_responsible_user_id or self.env.user
            deadline = fields.Date.to_date(record.sla_deadline) if record.sla_deadline else fields.Date.context_today(record)
            record._schedule_internal_activity(owner, _("Portal request SLA follow-up"), deadline=deadline)
        return display_notification(_("SLA follow-up activity scheduled."))

    def action_open_decision_wizard(self):
        self.ensure_one()
        self.check_access("read")
        if self.state == "manager_review":
            self._require_manager_for_request()
        elif self.state in ("hr_review", "submitted"):
            require_portal_hr(self)
        else:
            raise UserError(_("This request is not waiting for an approval decision."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Request Decision"),
            "res_model": "onehr.portal.request.decision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_open_employee(self):
        require_portal_hr(self)
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.employee_name,
            "res_model": "hr.employee",
            "res_id": self.employee_id.id,
            "view_mode": "form",
        }

    def action_open_attachments(self):
        self.ensure_one()
        return open_records_action(
            name=_("Attachments — %s", self.name),
            res_model="ir.attachment",
            domain=[("id", "in", self.attachment_ids.ids)],
            view_mode="list,form",
        )

    def action_open_integration_record(self):
        self.ensure_one()
        if not self.integration_model or not self.integration_res_id:
            raise UserError(_("No downstream record has been linked yet."))
        if not self.env.registry.get(self.integration_model):
            raise UserError(_("The downstream model is not available in this database."))
        record = self.env[self.integration_model].browse(self.integration_res_id).exists()
        if not record:
            raise UserError(_("The linked downstream record no longer exists."))
        record.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.integration_reference or record.display_name,
            "res_model": self.integration_model,
            "res_id": record.id,
            "view_mode": "form",
        }

    def action_open_self(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unsubmitted(self):
        for record in self:
            if record.state != "draft":
                raise AccessError(_("Submitted self-service request history cannot be deleted."))
            if not is_portal_admin(self.env):
                raise AccessError(_("Only Portal Administrators may delete unsubmitted Draft requests."))

    @api.model
    def _cron_sla_monitor(self):
        now = fields.Datetime.now()
        records = self.search(
            [
                ("state", "in", tuple(OPEN_STATES)),
                ("sla_deadline", "!=", False),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        for record in records:
            owner = record.hr_responsible_user_id
            if not owner or not owner.has_group("base.group_user"):
                continue
            reminder_hours = record.type_id.reminder_hours_before
            reminder_threshold = record.sla_deadline - timedelta(hours=reminder_hours) if reminder_hours else record.sla_deadline
            if not record.sla_reminder_sent_at and now >= reminder_threshold:
                record._schedule_internal_activity(
                    owner,
                    _("Portal request SLA due / overdue"),
                    deadline=fields.Date.to_date(record.sla_deadline),
                )
                record._write_governed({"sla_reminder_sent_at": now})
        return True

