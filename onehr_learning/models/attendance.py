from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action
from .authority_helpers import (
    is_learning_officer,
    is_learning_trainer,
    require_learning_manager,
    require_learning_trainer_or_officer,
)


class OneHRLearningAttendance(models.Model):
    """Training-attendance evidence.

    This model intentionally does not replace `hr.attendance`: it records presence
    in a Learning Session. Work-attendance synchronization is explicit, optional,
    and delegated to the accepted OneHR Attendance ingestion service.
    """

    _name = "onehr.learning.attendance"
    _description = "OneHR Learning Attendance"
    _inherit = ["onehr.mixin.audit"]
    _order = "session_start desc, employee_name, id"
    _rec_name = "name"

    _EVIDENCE_CONTEXT = "onehr_learning_attendance_evidence_controlled"

    name = fields.Char(compute="_compute_name", store=True)
    enrollment_id = fields.Many2one(
        "onehr.learning.enrollment",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    session_id = fields.Many2one(
        "onehr.learning.session",
        related="enrollment_id.session_id",
        store=True,
        readonly=True,
        index=True,
    )
    session_start = fields.Datetime(
        related="session_id.start_datetime",
        store=True,
        readonly=True,
        index=True,
    )
    course_id = fields.Many2one(
        "onehr.learning.course",
        related="enrollment_id.course_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="enrollment_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="enrollment_id.employee_id",
        store=True,
        readonly=True,
        index=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    employee_name = fields.Char(
        related="enrollment_id.employee_name",
        store=True,
        readonly=True,
        index=True,
    )

    attendance_status = fields.Selection(
        [
            ("not_recorded", "Not Recorded"),
            ("present", "Present"),
            ("late", "Late"),
            ("partial", "Partial"),
            ("absent", "Absent"),
            ("excused", "Excused"),
        ],
        required=True,
        default="not_recorded",
        index=True,
        tracking=True,
    )
    check_in = fields.Datetime(index=True, tracking=True)
    check_out = fields.Datetime(index=True, tracking=True)
    attended_hours = fields.Float(default=0.0, tracking=True, aggregator="sum")
    attendance_percent = fields.Float(
        compute="_compute_attendance_percent",
        store=True,
        digits=(16, 2),
        aggregator="avg",
    )
    source = fields.Selection(
        [
            ("manual", "Manual"),
            ("import", "Import"),
            ("lms", "External LMS"),
            ("attendance_bridge", "Attendance Bridge"),
        ],
        required=True,
        default="manual",
        index=True,
        tracking=True,
    )
    note = fields.Text(tracking=True)
    correction_reason = fields.Text(
        tracking=True,
        help="Manager evidence required when correcting completed-session attendance.",
    )

    work_attendance_model = fields.Char(readonly=True, copy=False)
    work_attendance_res_id = fields.Integer(readonly=True, copy=False)
    work_attendance_label = fields.Char(readonly=True, copy=False)
    work_attendance_synced_at = fields.Datetime(readonly=True, copy=False)
    work_attendance_synced_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    _enrollment_attendance_unique = models.Constraint(
        "unique(enrollment_id)",
        "Each Learning Enrollment may have only one training-attendance record.",
    )

    @api.depends("enrollment_id.name", "employee_name")
    def _compute_name(self):
        for record in self:
            record.name = _(
                "%(enrollment)s — %(employee)s",
                enrollment=record.enrollment_id.name or _("Enrollment"),
                employee=record.employee_name or _("Participant"),
            )

    @api.depends("attended_hours", "session_id.planned_hours", "attendance_status")
    def _compute_attendance_percent(self):
        for record in self:
            if record.attendance_status in {"absent", "excused", "not_recorded"}:
                record.attendance_percent = 0.0
                continue
            planned = record.session_id.planned_hours
            record.attendance_percent = (
                min(round(record.attended_hours * 100.0 / planned, 2), 100.0)
                if planned > 0
                else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_trainer_or_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            enrollment = self.env["onehr.learning.enrollment"].browse(
                vals.get("enrollment_id")
            ).exists()
            if not enrollment:
                raise ValidationError(_("A valid Learning Enrollment is required."))
            if not is_learning_officer(self.env):
                if enrollment.session_id.trainer_user_id != self.env.user:
                    raise AccessError(_("Trainer is not assigned to this Learning Session."))
            if enrollment.state not in {
                "enrolled", "attended", "passed", "failed", "certified", "no_show"
            }:
                raise UserError(_("Attendance may be recorded only after the participant is Enrolled."))
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_attendance()
        return records

    def write(self, values):
        values = dict(values)
        evidence = {
            "work_attendance_model",
            "work_attendance_res_id",
            "work_attendance_label",
            "work_attendance_synced_at",
            "work_attendance_synced_by_id",
        }
        if evidence & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Work-attendance synchronization evidence is server-controlled."))

        officer = is_learning_officer(self.env)
        if not officer:
            if not is_learning_trainer(self.env):
                raise AccessError(_("Trainer or L&D Officer authority is required."))
            for record in self:
                if record.session_id.trainer_user_id != self.env.user:
                    raise AccessError(_("Trainer is not assigned to this Learning Session."))
                if record.session_id.state == "completed":
                    raise AccessError(
                        _("Completed-session attendance correction requires Learning Manager authority.")
                    )
        else:
            for record in self:
                if (
                    record.session_id.state == "completed"
                    and not self.env.user.has_group(
                        "onehr_learning.group_onehr_learning_manager_approver"
                    )
                    and set(values)
                    & {"attendance_status", "check_in", "check_out", "attended_hours"}
                ):
                    raise AccessError(
                        _("Completed-session attendance correction requires Learning Manager authority.")
                    )
                if (
                    record.session_id.state == "completed"
                    and set(values)
                    & {"attendance_status", "check_in", "check_out", "attended_hours"}
                    and not (values.get("correction_reason") or record.correction_reason or "").strip()
                ):
                    raise ValidationError(
                        _("A Correction Reason is required for completed-session attendance changes.")
                    )

        result = super().write(values)
        self._validate_attendance()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_attendance_evidence(self):
        require_learning_manager(self)
        for record in self:
            if (
                record.attendance_status != "not_recorded"
                or record.work_attendance_res_id
                or record.enrollment_id.state
                in {"attended", "passed", "failed", "certified", "no_show"}
            ):
                raise AccessError(_("Recorded training-attendance evidence cannot be deleted."))

    @api.constrains("check_in", "check_out", "attended_hours", "attendance_status")
    def _check_attendance(self):
        self._validate_attendance()

    def _validate_attendance(self):
        for record in self:
            if record.check_out and not record.check_in:
                raise ValidationError(_("Check In is required when Check Out is provided."))
            if record.check_in and record.check_out and record.check_out <= record.check_in:
                raise ValidationError(_("Training Check Out must be after Check In."))
            if record.attended_hours < 0:
                raise ValidationError(_("Attended Hours cannot be negative."))
            if record.attended_hours > record.session_id.planned_hours + 0.0001:
                raise ValidationError(_("Attended Hours cannot exceed Session planned hours."))
        return True

    def _record_status(self, status):
        require_learning_trainer_or_officer(self)
        now = fields.Datetime.now()
        for record in self:
            if not is_learning_officer(self.env) and record.session_id.trainer_user_id != self.env.user:
                raise AccessError(_("Trainer is not assigned to this Learning Session."))
            if record.session_id.state not in {"in_progress", "completed"}:
                raise UserError(_("Attendance can be finalized only while/after the Session is delivered."))

            values = {"attendance_status": status}
            if status == "present":
                values.update(
                    {
                        "check_in": record.check_in or record.session_id.start_datetime,
                        "check_out": record.check_out or record.session_id.end_datetime,
                        "attended_hours": record.session_id.planned_hours,
                    }
                )
            elif status == "absent":
                values.update({"check_in": False, "check_out": False, "attended_hours": 0.0})
            elif status == "excused":
                values.update({"attended_hours": 0.0})
            elif status in {"late", "partial"}:
                if not record.check_in or not record.check_out:
                    raise UserError(_("Late/Partial attendance requires Check In and Check Out."))
                values["attended_hours"] = max(
                    (record.check_out - record.check_in).total_seconds() / 3600.0,
                    0.0,
                )

            record.write(values)
            if status in {"present", "late", "partial"}:
                record.enrollment_id._mark_attended_from_attendance()
            elif status == "absent":
                record.enrollment_id._mark_no_show_from_session()
            record.log_business_action(
                _("Training attendance recorded as %s at %s.", status, fields.Datetime.to_string(now))
            )
        return True

    def action_mark_present(self):
        return self._record_status("present")

    def action_mark_late(self):
        return self._record_status("late")

    def action_mark_partial(self):
        return self._record_status("partial")

    def action_mark_absent(self):
        return self._record_status("absent")

    def action_mark_excused(self):
        return self._record_status("excused")

    def action_open_enrollment(self):
        self.ensure_one()
        require_learning_trainer_or_officer(self)
        return open_record_action(
            name=self.enrollment_id.display_name,
            res_model=self.enrollment_id._name,
            res_id=self.enrollment_id.id,
        )

    def action_sync_work_attendance(self):
        """Explicit soft synchronization to canonical OneHR Attendance."""
        self.ensure_one()
        require_learning_trainer_or_officer(self)
        if not self.session_id.sync_work_attendance:
            raise UserError(
                _("Work-attendance sync is not enabled on this Learning Session.")
            )
        if self.attendance_status not in {"present", "late", "partial"}:
            raise UserError(_("Only actual attended intervals can be synchronized."))
        if not self.check_in or not self.check_out:
            raise UserError(_("Training Check In and Check Out are required for work-attendance sync."))
        if self.work_attendance_res_id:
            raise UserError(_("This training attendance already has work-attendance sync evidence."))
        if "hr.attendance" not in self.env.registry.models:
            raise UserError(_("Canonical Attendance is not installed."))

        officer_group = self.env.ref(
            "onehr_attendance.group_onehr_attendance_officer",
            raise_if_not_found=False,
        )
        if not officer_group or officer_group not in self.env.user.group_ids:
            raise AccessError(
                _("Work-attendance synchronization requires OneHR Attendance Officer authority.")
            )

        Attendance = self.env["hr.attendance"]
        if not hasattr(Attendance, "onehr_ingest_interval"):
            raise UserError(_("Installed Attendance does not expose the accepted OneHR ingestion service."))

        attendance = Attendance.onehr_ingest_interval(
            {
                "employee_id": self.employee_id.id,
                "check_in": self.check_in,
                "check_out": self.check_out,
                "source_channel": "api",
                "source_system": "ONEHR_LEARNING",
                "external_reference": self.name,
                "device_reference": self.session_id.name,
            }
        )
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "work_attendance_model": attendance._name,
                "work_attendance_res_id": attendance.id,
                "work_attendance_label": attendance.display_name,
                "work_attendance_synced_at": fields.Datetime.now(),
                "work_attendance_synced_by_id": self.env.user.id,
            }
        )
        return display_notification(_("Training interval synchronized to canonical Attendance."))
