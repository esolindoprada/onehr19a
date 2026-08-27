import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action
from .authority_helpers import (
    is_learning_officer,
    is_learning_trainer,
    require_learning_manager,
    require_learning_officer,
    require_learning_trainer_or_officer,
)


FINAL_ENROLLMENT_STATES = {
    "certified",
    "cancelled",
    "no_show",
}


class OneHRLearningEnrollment(models.Model):
    """Governed participant journey and approval source transaction."""

    _name = "onehr.learning.enrollment"
    _description = "OneHR Learning Enrollment"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "requested_at desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_learning_enrollment_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_learning_enrollment_evidence_controlled"

    name = fields.Char(
        string="Enrollment No.",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    session_id = fields.Many2one(
        "onehr.learning.session",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
    )
    course_id = fields.Many2one(
        "onehr.learning.course",
        related="session_id.course_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="session_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
        tracking=True,
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
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
        groups="onehr_learning.group_onehr_learning_officer,onehr_learning.group_onehr_learning_manager_approver",
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    manager_user_id = fields.Many2one(
        "res.users",
        related="employee_id.parent_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("requested", "Requested"),
            ("approved", "Approved"),
            ("enrolled", "Enrolled"),
            ("waitlisted", "Waitlisted"),
            ("attended", "Attended"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("certified", "Certified"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    request_reason = fields.Text(tracking=True)
    requested_at = fields.Datetime(readonly=True, copy=False, index=True)
    requested_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    approved_at = fields.Datetime(readonly=True, copy=False, index=True)
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    enrolled_at = fields.Datetime(readonly=True, copy=False, index=True)
    completed_at = fields.Datetime(readonly=True, copy=False, index=True)

    prerequisite_override_reason = fields.Text(
        tracking=True,
        help="Manager-only exception evidence; does not delete prerequisite requirements.",
    )
    prerequisite_override_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    prerequisite_override_at = fields.Datetime(readonly=True, copy=False)

    pre_test_score = fields.Float(digits=(16, 2), tracking=True, aggregator="avg")
    post_test_score = fields.Float(digits=(16, 2), tracking=True, aggregator="avg")
    reaction_score = fields.Float(
        digits=(16, 2),
        tracking=True,
        aggregator="avg",
        help="Participant reaction/evaluation score on a 0–5 scale.",
    )
    reaction_comment = fields.Text(tracking=True)
    result_note = fields.Text(tracking=True)

    attendance_id = fields.Many2one(
        "onehr.learning.attendance",
        compute="_compute_evidence_links",
        string="Attendance",
    )
    attendance_percent = fields.Float(
        compute="_compute_evidence_links",
        digits=(16, 2),
    )
    certificate_id = fields.Many2one(
        "onehr.learning.certificate",
        compute="_compute_evidence_links",
        string="Certificate",
    )

    external_system = fields.Char(index=True, copy=False)
    external_reference = fields.Char(index=True, copy=False)
    external_payload_hash = fields.Char(readonly=True, copy=False)

    # Soft integration evidence: no Many2one to optional addons is declared.
    timeoff_target_model = fields.Char(readonly=True, copy=False)
    timeoff_target_res_id = fields.Integer(readonly=True, copy=False)
    timeoff_target_label = fields.Char(readonly=True, copy=False)

    _session_employee_unique = models.Constraint(
        "unique(session_id, employee_id)",
        "An employee may be enrolled only once in the same Learning Session.",
    )
    _external_reference_unique = models.Constraint(
        "unique(company_id, external_system, external_reference)",
        "External Learning enrollment reference must be unique within a company/system.",
    )

    def _compute_evidence_links(self):
        Attendance = self.env["onehr.learning.attendance"]
        Certificate = self.env["onehr.learning.certificate"]
        for record in self:
            attendance = Attendance.search([("enrollment_id", "=", record.id)], limit=1)
            certificate = Certificate.search([("enrollment_id", "=", record.id)], limit=1)
            record.attendance_id = attendance
            record.attendance_percent = attendance.attendance_percent if attendance else 0.0
            record.certificate_id = certificate

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("Learning Enrollments must be created in Draft."))
            session = self.env["onehr.learning.session"].browse(vals.get("session_id")).exists()
            employee = self.env["hr.employee"].browse(vals.get("employee_id")).exists()
            if not session or not employee:
                raise ValidationError(_("A valid Session and Employee are required."))
            if employee.company_id != session.company_id:
                raise ValidationError(_("Employee and Learning Session company must match."))
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.learning.enrollment"
                ) or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_enrollment_integrity()
        return records

    def _write_governed(self, values):
        return super(OneHRLearningEnrollment, self).write(values)

    def write(self, values):
        values = dict(values)
        evidence_fields = {
            "requested_at", "requested_by_id", "approved_at", "approved_by_id",
            "enrolled_at", "completed_at", "prerequisite_override_by_id",
            "prerequisite_override_at", "external_payload_hash",
            "timeoff_target_model", "timeoff_target_res_id", "timeoff_target_label",
        }
        if evidence_fields & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Learning enrollment evidence is server-controlled."))
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Enrollment state changes only through governed actions."))

        for record in self:
            if record.state != "draft":
                identity_fields = {
                    "employee_id",
                    "session_id",
                    "external_system",
                    "external_reference",
                    "request_reason",
                }
                if identity_fields & set(values):
                    raise AccessError(
                        _("Enrollment participant/session/external identity is frozen after Draft.")
                    )
            if record.state in {"passed", "failed", "certified", "no_show", "cancelled"}:
                result_fields = {
                    "pre_test_score",
                    "post_test_score",
                    "reaction_score",
                    "reaction_comment",
                    "result_note",
                }
                if result_fields & set(values):
                    raise AccessError(
                        _("Final Learning result evidence is frozen; use a governed correction cycle instead.")
                    )

        officer = is_learning_officer(self.env)
        trainer = is_learning_trainer(self.env)
        if not officer:
            if not trainer:
                raise AccessError(_("You are not allowed to update Learning Enrollments."))
            allowed = {
                "pre_test_score",
                "post_test_score",
                "reaction_score",
                "reaction_comment",
                "result_note",
            }
            if set(values) - allowed:
                raise AccessError(_("Trainers may update only assessment/reaction fields."))
            for record in self:
                if record.session_id.trainer_user_id != self.env.user:
                    raise AccessError(_("Trainers may update only their assigned Learning Sessions."))
                if record.state in FINAL_ENROLLMENT_STATES:
                    raise AccessError(_("Final/cancelled enrollment evidence cannot be edited by a Trainer."))

        result = super().write(values)
        self._validate_enrollment_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_enrollment_history(self):
        require_learning_manager(self)
        for record in self:
            if record.state != "draft" or record.attendance_id or record.certificate_id:
                raise AccessError(_("Only an unused Draft Enrollment can be deleted."))

    @api.constrains(
        "employee_id",
        "session_id",
        "pre_test_score",
        "post_test_score",
        "reaction_score",
    )
    def _check_enrollment_integrity(self):
        self._validate_enrollment_integrity()

    def _validate_enrollment_integrity(self):
        for record in self:
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Employee and Enrollment company must match."))
            for field_name in ("pre_test_score", "post_test_score"):
                value = record[field_name]
                if value < 0 or value > 100:
                    raise ValidationError(_("%s must be between 0 and 100.") % field_name)
            if record.reaction_score < 0 or record.reaction_score > 5:
                raise ValidationError(_("Reaction Score must be between 0 and 5."))
        return True

    def _prerequisite_gaps(self):
        self.ensure_one()
        required = self.course_id.prerequisite_course_ids
        if not required:
            return self.env["onehr.learning.course"]
        as_of_date = fields.Date.to_date(self.session_id.start_datetime)
        satisfied = self.env["onehr.learning.course"]
        Certificate = self.env["onehr.learning.certificate"]
        for course in required:
            certificate = Certificate.search(
                [
                    ("employee_id", "=", self.employee_id.id),
                    ("course_id", "=", course.id),
                    ("state", "=", "valid"),
                    ("valid_from", "<=", as_of_date),
                    "|",
                    ("valid_to", "=", False),
                    ("valid_to", ">=", as_of_date),
                ],
                limit=1,
            )
            if certificate:
                satisfied |= course
        return required - satisfied

    def action_approve_prerequisite_override(self):
        self.ensure_one()
        require_learning_manager(self)
        gaps = self._prerequisite_gaps()
        if not gaps:
            raise UserError(_("No prerequisite gap exists for this Enrollment."))
        if not (self.prerequisite_override_reason or "").strip():
            raise UserError(_("Enter a Prerequisite Override Reason first."))
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "prerequisite_override_by_id": self.env.user.id,
                "prerequisite_override_at": fields.Datetime.now(),
            }
        )
        self.log_business_action(
            _("Prerequisite exception approved by %s. Missing: %s",
              self.env.user.display_name, ", ".join(gaps.mapped("code")))
        )
        return display_notification(_("Prerequisite override evidence recorded."), notification_type="warning")

    def _validate_request_readiness(self):
        self.ensure_one()
        if self.session_id.state != "open":
            raise UserError(_("Enrollment requests require a Session that is Open for Enrollment."))
        if (
            self.session_id.enrollment_deadline
            and fields.Datetime.now() > self.session_id.enrollment_deadline
        ):
            raise UserError(_("The Session enrollment deadline has passed."))
        if not self.course_id.published or not self.course_id.active:
            raise UserError(_("The Course must remain published and active."))
        gaps = self._prerequisite_gaps()
        if gaps and not self.prerequisite_override_by_id:
            raise ValidationError(
                _("Missing prerequisite certificate(s): %s") % ", ".join(gaps.mapped("code"))
            )
        return True

    def _approval_payload(self):
        self.ensure_one()
        return {
            "enrollment": self.name,
            "employee": self.employee_name,
            "employee_number": self.employee_number,
            "course": self.course_id.display_name,
            "course_code": self.course_id.code,
            "session": self.session_id.name,
            "start_datetime": fields.Datetime.to_string(self.session_id.start_datetime),
            "end_datetime": fields.Datetime.to_string(self.session_id.end_datetime),
            "estimated_cost": self.session_id.estimated_cost,
            "request_reason": self.request_reason or "",
            "prerequisite_override": bool(self.prerequisite_override_by_id),
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        manager_ids = self.manager_user_id.ids
        values.update(
            {
                "company_id": self.company_id.id,
                "document_type": "learning_enrollment",
                "amount": self.session_id.estimated_cost,
                "currency_id": self.company_id.currency_id.id,
                "risk_level": "elevated" if self.prerequisite_override_by_id else "normal",
                "manager_user_ids": manager_ids,
                "extra": {
                    "course_type": self.course_id.course_type,
                    "mandatory": self.course_id.mandatory,
                    "session_type": self.session_id.session_type,
                },
            }
        )
        return values

    def action_request_approval(self):
        self.ensure_one()
        require_learning_officer(self)
        if self.state != "draft":
            raise UserError(_("Only a Draft Enrollment can be requested for approval."))
        self._validate_request_readiness()
        now = fields.Datetime.now()
        self.with_context(
            **{
                self._STATE_CONTEXT: True,
                self._EVIDENCE_CONTEXT: True,
            }
        )._write_governed(
            {
                "state": "requested",
                "requested_at": now,
                "requested_by_id": self.env.user.id,
            }
        )
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "requested":
            return True
        if decision == "approve":
            values = {
                "state": "approved",
                "approved_at": fields.Datetime.now(),
                "approved_by_id": self.env.user.id,
            }
        else:
            values = {"state": "rejected"}
        self.with_context(
            **{
                self._STATE_CONTEXT: True,
                self._EVIDENCE_CONTEXT: True,
            }
        )._write_governed(values)
        return True

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        if self.state not in {"requested", "rejected"}:
            raise UserError(_("Approval evidence cannot be cancelled after business execution."))
        return True

    def _latest_approved_request(self):
        self.ensure_one()
        return self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", self._name),
                ("source_res_id", "=", self.id),
                ("state", "=", "approved"),
            ],
            order="finalized_at desc, id desc",
            limit=1,
        )

    def action_enroll(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "approved":
                raise UserError(_("Only an Approved Enrollment can be enrolled."))
            if record.session_id.state != "open":
                raise UserError(_("The Learning Session must still be Open."))
            if record.session_id.enrolled_count < record.session_id.capacity:
                target_state = "enrolled"
            elif (
                record.session_id.waitlist_enabled
                and record.session_id.waitlist_count < record.session_id.waitlist_capacity
            ):
                target_state = "waitlisted"
            else:
                raise UserError(_("Session and waitlist capacity are both full."))

            record.with_context(
                **{
                    self._STATE_CONTEXT: True,
                    self._EVIDENCE_CONTEXT: True,
                }
            )._write_governed(
                {
                    "state": target_state,
                    "enrolled_at": fields.Datetime.now(),
                }
            )
            approval = record._latest_approved_request()
            if approval:
                record.onehr_mark_approval_executed(approval)
            record.log_business_action(
                _("Approved Learning request executed as %s.", target_state)
            )
        return True

    def _enroll_from_waitlist(self):
        self.ensure_one()
        if self.state != "waitlisted":
            return False
        self.with_context(**{self._STATE_CONTEXT: True})._write_governed(
            {"state": "enrolled"}
        )
        self.log_business_action(_("Participant promoted from waitlist to enrolled."))
        return True

    def _mark_attended_from_attendance(self):
        self.ensure_one()
        if self.state not in {"enrolled", "attended"}:
            raise UserError(_("Only an Enrolled participant can advance to Attended."))
        if self.state != "attended":
            self.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "attended"}
            )
        return True

    def _mark_no_show_from_session(self):
        self.ensure_one()
        if self.state == "enrolled":
            self.with_context(
                **{
                    self._STATE_CONTEXT: True,
                    self._EVIDENCE_CONTEXT: True,
                }
            )._write_governed(
                {
                    "state": "no_show",
                    "completed_at": fields.Datetime.now(),
                }
            )
        return True

    def _cancel_from_session(self):
        self.ensure_one()
        if self.state not in {"rejected", "cancelled", "certified"}:
            self.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "cancelled"}
            )
        return True

    def action_reset_to_draft(self):
        require_learning_officer(self)
        for record in self:
            if record.state != "rejected":
                raise UserError(_("Only a Rejected Enrollment can be reset to Draft."))
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "draft"}
            )
        return True

    def action_cancel(self):
        require_learning_officer(self)
        for record in self:
            if record.state not in {"draft", "requested", "approved", "waitlisted", "enrolled"}:
                raise UserError(_("This Enrollment can no longer be cancelled."))
            if record.state == "requested":
                latest = self.env["onehr.approval.request"].search(
                    [
                        ("source_model", "=", record._name),
                        ("source_res_id", "=", record.id),
                        ("state", "in", ["draft", "submitted", "pending"]),
                    ],
                    order="requested_at desc, id desc",
                    limit=1,
                )
                if latest:
                    latest.action_cancel()
            record.with_context(**{self._STATE_CONTEXT: True})._write_governed(
                {"state": "cancelled"}
            )
            record.log_business_action(_("Learning Enrollment cancelled."))
        return True

    def action_evaluate_result(self):
        require_learning_trainer_or_officer(self)
        for record in self:
            if not is_learning_officer(self.env):
                if record.session_id.trainer_user_id != self.env.user:
                    raise AccessError(_("Trainer is not assigned to this Learning Session."))
            if record.state != "attended":
                raise UserError(_("Only an Attended participant can be evaluated."))
            target = (
                "passed"
                if record.post_test_score >= record.course_id.pass_score
                else "failed"
            )
            record.with_context(
                **{
                    self._STATE_CONTEXT: True,
                    self._EVIDENCE_CONTEXT: True,
                }
            )._write_governed(
                {
                    "state": target,
                    "completed_at": fields.Datetime.now(),
                }
            )
            record.log_business_action(
                _("Learning result evaluated as %s.", target)
            )
        return True

    def action_issue_certificate(self):
        self.ensure_one()
        require_learning_officer(self)
        if self.state != "passed":
            raise UserError(_("Only a Passed Enrollment can receive a certificate."))
        certificate = self.env["onehr.learning.certificate"].create(
            {"enrollment_id": self.id}
        )
        certificate.action_issue()
        self.with_context(**{self._STATE_CONTEXT: True})._write_governed(
            {"state": "certified"}
        )
        self.log_business_action(
            _("Learning Certificate issued: %s", certificate.name)
        )
        return open_record_action(
            name=certificate.display_name,
            res_model=certificate._name,
            res_id=certificate.id,
        )

    def action_open_attendance(self):
        self.ensure_one()
        require_learning_trainer_or_officer(self)
        if self.attendance_id:
            return open_record_action(
                name=self.attendance_id.display_name,
                res_model=self.attendance_id._name,
                res_id=self.attendance_id.id,
            )
        attendance = self.env["onehr.learning.attendance"].create(
            {"enrollment_id": self.id}
        )
        return open_record_action(
            name=attendance.display_name,
            res_model=attendance._name,
            res_id=attendance.id,
        )

    def action_open_certificate(self):
        self.ensure_one()
        require_learning_officer(self)
        if not self.certificate_id:
            raise UserError(_("No Learning Certificate exists yet."))
        return open_record_action(
            name=self.certificate_id.display_name,
            res_model=self.certificate_id._name,
            res_id=self.certificate_id.id,
        )

    def action_generate_training_leave(self):
        """Soft Time Off integration using the employee's normal authority.

        L&D never sudo-creates leave. If Time Off or employee self-service authority
        is absent, the action fails explicitly and leaves no partial evidence.
        """
        self.ensure_one()
        require_learning_officer(self)
        if self.state not in {"approved", "enrolled", "waitlisted"}:
            raise UserError(_("Training Leave can be generated only after Learning approval."))
        code = (self.course_id.training_leave_type_code or "").strip().upper()
        if not code:
            raise UserError(_("Configure Training Leave Type Code on the Course first."))
        if "onehr.leave.request" not in self.env.registry.models:
            raise UserError(_("OneHR Time Off is not installed; no training leave was created."))
        if self.timeoff_target_res_id:
            raise UserError(_("Training Leave integration evidence already exists."))

        employee_user = self.employee_user_id
        if not employee_user:
            raise UserError(_("The participant is not linked to an Odoo user."))
        group = self.env.ref(
            "onehr_timeoff.group_onehr_timeoff_user",
            raise_if_not_found=False,
        )
        if not group or group not in employee_user.group_ids:
            raise UserError(
                _("The participant does not have OneHR Time Off self-service authority.")
            )

        employee_env_record = self.with_user(employee_user)
        date_from = fields.Datetime.context_timestamp(
            employee_env_record,
            self.session_id.start_datetime,
        ).date()
        date_to = fields.Datetime.context_timestamp(
            employee_env_record,
            self.session_id.end_datetime,
        ).date()

        LeaveType = self.env["onehr.leave.type"].with_user(employee_user)
        leave_type = LeaveType.search(
            [
                ("company_id", "=", self.company_id.id),
                ("code", "=", code),
                ("state", "=", "active"),
                ("active", "=", True),
                ("valid_from", "<=", date_from),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", date_to),
            ],
            limit=2,
        )
        if len(leave_type) != 1:
            raise UserError(
                _("Training Leave Type code '%s' must resolve to one active/effective policy.", code)
            )

        leave = self.env["onehr.leave.request"].with_user(employee_user).create(
            {
                "employee_id": self.employee_id.id,
                "leave_type_id": leave_type.id,
                "date_from": date_from,
                "date_to": date_to,
                "reason": _("Training: %(course)s / %(session)s",
                            course=self.course_id.display_name,
                            session=self.session_id.name),
            }
        )
        leave.action_submit_for_approval()
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {
                "timeoff_target_model": leave._name,
                "timeoff_target_res_id": leave.id,
                "timeoff_target_label": leave.display_name,
            }
        )
        self.log_business_action(
            _("Training Leave request created under participant authority: %s", leave.display_name)
        )
        return display_notification(_("Training Leave request created/submitted."))

    @api.model
    def onehr_ingest_external_result(self, payload):
        """Stable LMS/SCORM/xAPI boundary for the future integrations owner.

        Authentication, rate limiting, signatures and webhooks are deliberately not
        owned here. The caller must already hold normal Learning authority.
        """
        require_learning_trainer_or_officer(self)
        if not isinstance(payload, dict):
            raise ValidationError(_("External Learning result payload must be an object."))

        external_system = (payload.get("external_system") or "").strip()
        external_reference = (payload.get("external_reference") or "").strip()
        if not external_system or not external_reference:
            raise ValidationError(_("external_system and external_reference are required."))

        enrollment = self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("external_system", "=", external_system),
                ("external_reference", "=", external_reference),
            ],
            limit=2,
        )
        if len(enrollment) != 1:
            raise ValidationError(_("External result must resolve to exactly one Enrollment."))

        if not is_learning_officer(self.env) and enrollment.session_id.trainer_user_id != self.env.user:
            raise AccessError(_("Trainer is not assigned to the resolved Learning Session."))

        updates = {}
        for source_key, target_field in (
            ("pre_test_score", "pre_test_score"),
            ("post_test_score", "post_test_score"),
            ("reaction_score", "reaction_score"),
            ("reaction_comment", "reaction_comment"),
            ("result_note", "result_note"),
        ):
            if source_key in payload:
                updates[target_field] = payload[source_key]
        if updates:
            enrollment.write(updates)

        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        import hashlib
        enrollment.with_context(**{self._EVIDENCE_CONTEXT: True}).write(
            {"external_payload_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
        )
        return {
            "enrollment_id": enrollment.id,
            "state": enrollment.state,
            "payload_sha256": enrollment.external_payload_hash,
        }
