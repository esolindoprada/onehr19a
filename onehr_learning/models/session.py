import base64
import csv
import io
from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_records_action
from .authority_helpers import require_learning_manager, require_learning_officer


SESSION_LOCKED_STATES = {"in_progress", "completed", "cancelled"}


class OneHRLearningSession(models.Model):
    """Scheduled delivery of a published course."""

    _name = "onehr.learning.session"
    _description = "OneHR Learning Session"
    _inherit = ["onehr.mixin.audit"]
    _order = "start_datetime desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_learning_session_state_controlled"
    _DOWNLOAD_CONTEXT = "onehr_learning_session_download_controlled"

    name = fields.Char(
        string="Session No.",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    title = fields.Char(required=True, tracking=True, index=True)
    course_id = fields.Many2one(
        "onehr.learning.course",
        required=True,
        ondelete="restrict",
        check_company=True,
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
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open for Enrollment"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    delivery_mode = fields.Selection(
        [
            ("classroom", "Classroom"),
            ("virtual", "Virtual"),
            ("blended", "Blended"),
            ("self_paced", "Self-Paced"),
        ],
        required=True,
        default="classroom",
        index=True,
        tracking=True,
    )
    session_type = fields.Selection(
        [("internal", "In-House"), ("external", "External")],
        required=True,
        default="internal",
        index=True,
        tracking=True,
    )

    start_datetime = fields.Datetime(required=True, index=True, tracking=True)
    end_datetime = fields.Datetime(required=True, index=True, tracking=True)
    planned_hours = fields.Float(compute="_compute_planned_hours", store=True)
    venue = fields.Char(tracking=True)
    online_url = fields.Char(tracking=True)

    trainer_type = fields.Selection(
        [("internal", "Internal Trainer"), ("external", "External Trainer")],
        required=True,
        default="internal",
        tracking=True,
    )
    trainer_employee_id = fields.Many2one(
        "hr.employee",
        string="Internal Trainer",
        ondelete="restrict",
        check_company=True,
        tracking=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    trainer_user_id = fields.Many2one(
        "res.users",
        related="trainer_employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    vendor_id = fields.Many2one(
        "onehr.learning.vendor",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    external_trainer_name = fields.Char(tracking=True)

    capacity = fields.Integer(default=20, tracking=True)
    waitlist_enabled = fields.Boolean(default=True, tracking=True)
    waitlist_capacity = fields.Integer(default=10, tracking=True)
    enrollment_deadline = fields.Datetime(index=True, tracking=True)
    reminder_days_before = fields.Integer(default=3, tracking=True)
    reminder_scheduled = fields.Boolean(readonly=True, copy=False)
    sync_work_attendance = fields.Boolean(
        default=False,
        tracking=True,
        help=(
            "Explicit opt-in only. Training attendance remains canonical in OneHR Learning; "
            "an authorized Attendance Officer may separately publish the training interval "
            "to canonical work attendance when appropriate."
        ),
    )

    budget_id = fields.Many2one(
        "onehr.learning.budget",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    estimated_cost = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
        tracking=True,
    )

    enrollment_ids = fields.One2many(
        "onehr.learning.enrollment",
        "session_id",
        string="Enrollments",
    )
    attendance_ids = fields.One2many(
        "onehr.learning.attendance",
        "session_id",
        string="Training Attendance",
        readonly=True,
    )
    cost_line_ids = fields.One2many(
        "onehr.learning.cost.line",
        "session_id",
        string="Training Costs",
    )

    requested_count = fields.Integer(compute="_compute_operational_counts")
    enrolled_count = fields.Integer(compute="_compute_operational_counts")
    waitlist_count = fields.Integer(compute="_compute_operational_counts")
    attended_count = fields.Integer(compute="_compute_operational_counts")
    passed_count = fields.Integer(compute="_compute_operational_counts")
    certified_count = fields.Integer(compute="_compute_operational_counts")
    attendance_rate = fields.Float(compute="_compute_operational_counts", digits=(16, 2))
    completion_rate = fields.Float(compute="_compute_operational_counts", digits=(16, 2))
    actual_cost = fields.Monetary(
        compute="_compute_actual_cost",
        store=True,
        currency_field="currency_id",
        aggregator="sum",
    )

    # Human-friendly bulk participant interchange without an unapproved staging/wizard model.
    participant_import_file = fields.Binary(attachment=False, copy=False)
    participant_import_filename = fields.Char(copy=False)
    result_download_file = fields.Binary(attachment=False, readonly=True, copy=False)
    result_download_filename = fields.Char(readonly=True, copy=False)

    _session_number_unique = models.Constraint(
        "unique(name)",
        "Learning Session number must be unique.",
    )

    @api.depends("start_datetime", "end_datetime")
    def _compute_planned_hours(self):
        for record in self:
            if record.start_datetime and record.end_datetime:
                delta = record.end_datetime - record.start_datetime
                record.planned_hours = max(delta.total_seconds() / 3600.0, 0.0)
            else:
                record.planned_hours = 0.0

    def _compute_operational_counts(self):
        for record in self:
            enrollments = record.enrollment_ids
            record.requested_count = len(
                enrollments.filtered(lambda item: item.state == "requested")
            )
            record.enrolled_count = len(
                enrollments.filtered(
                    lambda item: item.state
                    in {"enrolled", "attended", "passed", "failed", "certified"}
                )
            )
            record.waitlist_count = len(
                enrollments.filtered(lambda item: item.state == "waitlisted")
            )
            record.attended_count = len(
                enrollments.filtered(
                    lambda item: item.state in {"attended", "passed", "failed", "certified"}
                )
            )
            record.passed_count = len(
                enrollments.filtered(lambda item: item.state in {"passed", "certified"})
            )
            record.certified_count = len(
                enrollments.filtered(lambda item: item.state == "certified")
            )
            denominator = record.enrolled_count
            record.attendance_rate = (
                round(record.attended_count * 100.0 / denominator, 2)
                if denominator
                else 0.0
            )
            result_denominator = len(
                enrollments.filtered(
                    lambda item: item.state in {"passed", "failed", "certified"}
                )
            )
            record.completion_rate = (
                round(record.passed_count * 100.0 / result_denominator, 2)
                if result_denominator
                else 0.0
            )

    @api.depends("cost_line_ids.state", "cost_line_ids.amount")
    def _compute_actual_cost(self):
        for record in self:
            record.actual_cost = sum(
                record.cost_line_ids.filtered(lambda line: line.state == "actual").mapped("amount")
            )

    @api.onchange("course_id")
    def _onchange_course_id(self):
        if self.course_id:
            self.company_id = self.course_id.company_id
            self.title = self.title or self.course_id.name
            self.delivery_mode = self.course_id.default_delivery_mode

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("Learning Sessions must be created in Draft."))
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.learning.session"
                ) or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_session_integrity()
        return records

    def _write_governed(self, values):
        return super(OneHRLearningSession, self).write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_session_history(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft" or record.enrollment_ids or record.cost_line_ids:
                raise AccessError(
                    _("Only an unused Draft Learning Session can be deleted.")
                )

    @api.constrains(
        "course_id", "company_id", "start_datetime", "end_datetime",
        "capacity", "waitlist_capacity", "estimated_cost",
        "trainer_type", "trainer_employee_id", "vendor_id",
        "reminder_days_before", "enrollment_deadline",
    )
    def _check_session_integrity(self):
        self._validate_session_integrity()

    def _validate_session_integrity(self):
        for record in self:
            if record.course_id.company_id != record.company_id:
                raise ValidationError(_("Course and Session company must match."))
            if record.end_datetime <= record.start_datetime:
                raise ValidationError(_("Session End must be after Session Start."))
            if record.capacity <= 0:
                raise ValidationError(_("Session Capacity must be greater than zero."))
            if record.waitlist_capacity < 0 or record.reminder_days_before < 0:
                raise ValidationError(_("Waitlist/Reminder values cannot be negative."))
            if record.estimated_cost < 0:
                raise ValidationError(_("Estimated Cost cannot be negative."))
            if (
                record.enrollment_deadline
                and record.enrollment_deadline > record.start_datetime
            ):
                raise ValidationError(_("Enrollment Deadline cannot be after Session Start."))
            if record.trainer_type == "internal":
                if record.trainer_employee_id and record.trainer_employee_id.company_id != record.company_id:
                    raise ValidationError(_("Internal Trainer must belong to the Session company."))
            elif not record.vendor_id and not (record.external_trainer_name or "").strip():
                raise ValidationError(
                    _("External training requires a Vendor or External Trainer Name.")
                )
            if record.vendor_id and record.vendor_id.company_id != record.company_id:
                raise ValidationError(_("Vendor and Session company must match."))
            if record.budget_id and record.budget_id.company_id != record.company_id:
                raise ValidationError(_("Budget and Session company must match."))
        return True

    def action_open_enrollment(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft sessions can be opened for enrollment."))
            record._validate_session_integrity()
            if not record.course_id.published or not record.course_id.active:
                raise UserError(_("Publish the active Course before opening this Session."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "open"}
            )
            record.log_business_action(_("Session opened for enrollment."))
        return display_notification(_("Session opened for enrollment."))

    def action_start(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "open":
                raise UserError(_("Only an Open session can start."))
            if not record.enrollment_ids.filtered(
                lambda item: item.state in {"enrolled", "attended", "passed", "failed", "certified"}
            ):
                raise UserError(_("At least one participant must be enrolled before starting."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "in_progress"}
            )
            record.log_business_action(_("Training session started."))
        return True

    def action_complete(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Only an In Progress session can be completed."))
            # Participants with no attendance evidence become No Show. Result grading
            # for attended participants may continue after delivery completion.
            for enrollment in record.enrollment_ids.filtered(
                lambda item: item.state == "enrolled"
            ):
                enrollment._mark_no_show_from_session()
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "completed"}
            )
            record.log_business_action(_("Training delivery completed."))
        return display_notification(_("Session completed."))

    def action_cancel(self):
        require_learning_manager(self)
        for record in self:
            if record.state not in {"draft", "open"}:
                raise UserError(_("Only Draft/Open sessions can be cancelled."))
            if record.enrollment_ids.filtered(
                lambda item: item.state in {"attended", "passed", "failed", "certified"}
            ):
                raise UserError(_("A session with attendance/result evidence cannot be cancelled."))
            for enrollment in record.enrollment_ids.filtered(
                lambda item: item.state not in {"rejected", "cancelled"}
            ):
                enrollment._cancel_from_session()
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "cancelled"}
            )
            record.log_business_action(_("Training session cancelled."))
        return True

    def action_process_waitlist(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "open":
                raise UserError(_("Waitlist processing is available only while the Session is Open."))
            available = max(record.capacity - record.enrolled_count, 0)
            if not available:
                continue
            waiting = record.enrollment_ids.filtered(
                lambda item: item.state == "waitlisted"
            ).sorted(key=lambda item: (item.requested_at or item.create_date, item.id))
            for enrollment in waiting[:available]:
                enrollment._enroll_from_waitlist()
        return display_notification(_("Waitlist processed against current available seats."))

    def action_open_enrollments(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Enrollments — %s", self.display_name),
            res_model="onehr.learning.enrollment",
            domain=[("session_id", "=", self.id)],
            context={"default_session_id": self.id},
            view_mode="kanban,list,pivot,graph,form",
        )

    def action_open_attendance(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Training Attendance — %s", self.display_name),
            res_model="onehr.learning.attendance",
            domain=[("session_id", "=", self.id)],
            context={"default_session_id": self.id},
            view_mode="list,pivot,graph,form",
        )

    def action_open_costs(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Training Costs — %s", self.display_name),
            res_model="onehr.learning.cost.line",
            domain=[("session_id", "=", self.id)],
            context={
                "default_session_id": self.id,
                "default_budget_id": self.budget_id.id,
                "default_company_id": self.company_id.id,
            },
            view_mode="list,pivot,graph,form",
        )

    def action_import_participants_csv(self):
        """Create Draft enrollments only; bulk import never bypasses approval."""
        self.ensure_one()
        require_learning_officer(self)
        if self.state not in {"draft", "open"}:
            raise UserError(_("Participants may be imported only into Draft/Open sessions."))
        if not self.participant_import_file:
            raise UserError(_("Upload a participant CSV file first."))

        try:
            raw = base64.b64decode(self.participant_import_file)
            content = raw.decode("utf-8-sig")
        except Exception as exc:
            raise ValidationError(_("Unable to decode participant CSV.")) from exc

        reader = csv.DictReader(io.StringIO(content))
        required = {"employee_number"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValidationError(_("Participant CSV requires an 'employee_number' column."))

        created = self.env["onehr.learning.enrollment"]
        seen = set()
        for row_number, row in enumerate(reader, start=2):
            employee_number = (row.get("employee_number") or "").strip()
            if not employee_number:
                raise ValidationError(_("CSV row %s has no employee_number.") % row_number)
            if employee_number in seen:
                raise ValidationError(_("CSV contains duplicate employee_number '%s'.") % employee_number)
            seen.add(employee_number)

            employee = self.env["hr.employee"].search(
                [
                    ("onehr_employee_number", "=", employee_number),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=2,
            )
            if len(employee) != 1:
                raise ValidationError(
                    _("CSV row %(row)s employee '%(number)s' must resolve to exactly one employee.",
                      row=row_number, number=employee_number)
                )
            existing = self.env["onehr.learning.enrollment"].search_count(
                [("session_id", "=", self.id), ("employee_id", "=", employee.id)]
            )
            if existing:
                continue
            created |= self.env["onehr.learning.enrollment"].create(
                {
                    "session_id": self.id,
                    "employee_id": employee.id,
                    "request_reason": (row.get("request_reason") or "").strip(),
                }
            )

        self.log_business_action(
            _("Participant CSV imported: %s new Draft enrollment(s).", len(created))
        )
        return display_notification(
            _("%s Draft enrollment(s) created. Approval was not bypassed.", len(created))
        )

    def action_export_results_csv(self):
        self.ensure_one()
        require_learning_officer(self)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "employee_number",
                "employee_name",
                "course_code",
                "session",
                "state",
                "attendance_percent",
                "pre_test_score",
                "post_test_score",
                "reaction_score",
                "certificate_number",
            ]
        )
        for enrollment in self.enrollment_ids.sorted(
            key=lambda item: (item.employee_name or "", item.id)
        ):
            writer.writerow(
                [
                    enrollment.employee_number or "",
                    enrollment.employee_name or "",
                    enrollment.course_id.code,
                    self.name,
                    enrollment.state,
                    enrollment.attendance_percent,
                    enrollment.pre_test_score,
                    enrollment.post_test_score,
                    enrollment.reaction_score,
                    enrollment.certificate_id.name or "",
                ]
            )

        filename = f"{self.name}-learning-results.csv"
        self.with_context(**{self._DOWNLOAD_CONTEXT: True}).write(
            {
                "result_download_file": base64.b64encode(
                    output.getvalue().encode("utf-8-sig")
                ),
                "result_download_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/result_download_file/%s?download=true"
            % (self._name, self.id, quote(filename)),
            "target": "self",
        }

    def write(self, values):
        # Download evidence is server-generated, never client-forged.
        if {"result_download_file", "result_download_filename"} & set(values):
            if not self.env.context.get(self._DOWNLOAD_CONTEXT):
                raise AccessError(_("Generated Learning result downloads are server-controlled."))
        return self._write_normal(values)

    def _write_normal(self, values):
        require_learning_officer(self)
        values = dict(values)
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Session state changes only through governed action buttons."))
        for record in self:
            if (
                record.state in {"completed", "cancelled"}
                and not self.env.context.get(self._STATE_CONTEXT)
            ):
                allowed = {"result_download_file", "result_download_filename"}
                if set(values) - allowed:
                    raise AccessError(
                        _("Completed/Cancelled Session business evidence is frozen.")
                    )
            elif (
                record.state == "in_progress"
                and not self.env.context.get(self._STATE_CONTEXT)
            ):
                protected = {
                    "course_id", "company_id", "start_datetime", "end_datetime",
                    "capacity", "waitlist_enabled", "waitlist_capacity",
                    "trainer_type", "trainer_employee_id", "vendor_id",
                }
                if protected & set(values):
                    raise AccessError(
                        _("In Progress Session identity and delivery scope are locked.")
                    )
        result = super().write(values)
        self._validate_session_integrity()
        return result

    @api.model
    def _cron_schedule_upcoming_reminders(self):
        now = fields.Datetime.now()
        sessions = self.search(
            [
                ("state", "=", "open"),
                ("start_datetime", ">", now),
                ("reminder_scheduled", "=", False),
            ]
        )
        todo = self.env.ref("mail.mail_activity_data_todo")
        for session in sessions:
            threshold = session.start_datetime - timedelta(days=session.reminder_days_before)
            if now < threshold:
                continue
            user = session.trainer_user_id or session.create_uid
            session.activity_schedule(
                todo.id,
                user_id=user.id,
                summary=_("Upcoming Learning Session"),
                note=_(
                    "%(course)s starts on %(start)s. Review participant readiness, "
                    "attendance preparation and delivery logistics.",
                    course=session.course_id.display_name,
                    start=fields.Datetime.to_string(session.start_datetime),
                ),
            )
            session.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"reminder_scheduled": True}
            )
        return True
