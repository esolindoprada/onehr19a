from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .authority_helpers import require_learning_officer


class OneHRLearningEnrollmentServices(models.Model):
    _inherit = "onehr.learning.enrollment"

    @api.model
    def onehr_external_enroll(self, payload):
        """Stable authenticated-service boundary for the future integration owner.

        This method owns no HTTP route, token, webhook signature or retry queue.
        `onehr_integrations_api` may call it after normal authentication/authorization.
        """
        require_learning_officer(self)
        if not isinstance(payload, dict):
            raise ValidationError(_("External enrollment payload must be an object."))

        external_system = (payload.get("external_system") or "").strip()
        external_reference = (payload.get("external_reference") or "").strip()
        employee_number = (payload.get("employee_number") or "").strip()
        session_reference = (payload.get("session_reference") or "").strip()
        if not all(
            [external_system, external_reference, employee_number, session_reference]
        ):
            raise ValidationError(
                _(
                    "external_system, external_reference, employee_number and "
                    "session_reference are required."
                )
            )

        existing = self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("external_system", "=", external_system),
                ("external_reference", "=", external_reference),
            ],
            limit=1,
        )
        if existing:
            return {"enrollment_id": existing.id, "state": existing.state, "idempotent": True}

        session = self.env["onehr.learning.session"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("name", "=", session_reference),
            ],
            limit=2,
        )
        employee = self.env["hr.employee"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("onehr_employee_number", "=", employee_number),
            ],
            limit=2,
        )
        if len(session) != 1 or len(employee) != 1:
            raise ValidationError(
                _("External enrollment must resolve to exactly one Session and Employee.")
            )

        enrollment = self.create(
            {
                "session_id": session.id,
                "employee_id": employee.id,
                "external_system": external_system,
                "external_reference": external_reference,
                "request_reason": payload.get("request_reason") or _("External Learning enrollment"),
            }
        )
        if payload.get("submit_for_approval"):
            enrollment.action_request_approval()
        return {
            "enrollment_id": enrollment.id,
            "state": enrollment.state,
            "idempotent": False,
        }

    @api.model
    def onehr_participant_portal_payload(self, employee):
        """Read-only downstream portal contract under the caller's normal access."""
        self.check_access("read")
        employee.ensure_one()
        employee.check_access("read")
        records = self.search(
            [
                ("employee_id", "=", employee.id),
                ("company_id", "in", self.env.companies.ids),
            ],
            order="create_date desc, id desc",
        )
        return [
            {
                "enrollment_id": record.id,
                "number": record.name,
                "course": record.course_id.name,
                "course_code": record.course_id.code,
                "session": record.session_id.name,
                "start_datetime": fields.Datetime.to_string(record.session_id.start_datetime),
                "end_datetime": fields.Datetime.to_string(record.session_id.end_datetime),
                "state": record.state,
                "attendance_percent": record.attendance_percent,
                "post_test_score": record.post_test_score,
                "certificate_number": record.certificate_id.name or "",
                "certificate_valid_to": (
                    fields.Date.to_string(record.certificate_id.valid_to)
                    if record.certificate_id and record.certificate_id.valid_to
                    else False
                ),
            }
            for record in records
        ]


class OneHRLearningSessionServices(models.Model):
    _inherit = "onehr.learning.session"

    @api.model
    def onehr_learning_kpi_snapshot(self, company, date_from, date_to):
        """Analytics-ready Learning facts; external analytics remains downstream-owned."""
        require_learning_officer(self)
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        if date_to < date_from:
            raise ValidationError(_("KPI Date To cannot be before Date From."))

        start_dt = fields.Datetime.to_datetime(f"{date_from} 00:00:00")
        end_dt = fields.Datetime.to_datetime(f"{date_to} 23:59:59")
        sessions = self.search(
            [
                ("company_id", "=", company.id),
                ("start_datetime", "<=", end_dt),
                ("end_datetime", ">=", start_dt),
                ("state", "in", ["in_progress", "completed"]),
            ]
        )
        enrollments = sessions.mapped("enrollment_ids")
        attendance = sessions.mapped("attendance_ids")
        certificates = self.env["onehr.learning.certificate"].search(
            [
                ("company_id", "=", company.id),
                ("issue_date", ">=", date_from),
                ("issue_date", "<=", date_to),
                ("state", "in", ["valid", "expired"]),
            ]
        )
        completed_results = enrollments.filtered(
            lambda item: item.state in {"passed", "failed", "certified"}
        )
        passed = enrollments.filtered(lambda item: item.state in {"passed", "certified"})
        learners = enrollments.filtered(
            lambda item: item.state
            not in {"draft", "requested", "rejected", "cancelled"}
        ).mapped("employee_id")
        actual_cost = sum(sessions.mapped("actual_cost"))
        return {
            "company_id": company.id,
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
            "session_count": len(sessions),
            "learner_count": len(learners),
            "training_hours": round(sum(attendance.mapped("attended_hours")), 2),
            "completion_rate": (
                round(len(passed) * 100.0 / len(completed_results), 2)
                if completed_results
                else 0.0
            ),
            "certificate_count": len(certificates),
            "actual_cost": actual_cost,
            "cost_per_learner": actual_cost / len(learners) if learners else 0.0,
            "fte_normalization_owner": "downstream_assignment_or_analytics",
        }


class OneHRLearningCertificateServices(models.Model):
    _inherit = "onehr.learning.certificate"

    def onehr_certificate_export_payload(self):
        """Certificate/grade export hook without API transport ownership."""
        require_learning_officer(self)
        result = []
        for record in self:
            result.append(
                {
                    "certificate_id": record.id,
                    "certificate_number": record.name,
                    "employee_number": record.employee_number or "",
                    "employee_name": record.employee_name,
                    "course_code": record.course_id.code,
                    "course": record.course_id.name,
                    "session": record.session_id.name,
                    "state": record.state,
                    "issue_date": fields.Date.to_string(record.issue_date)
                    if record.issue_date
                    else False,
                    "valid_to": fields.Date.to_string(record.valid_to)
                    if record.valid_to
                    else False,
                    "post_test_score": record.enrollment_id.post_test_score,
                }
            )
        return result
