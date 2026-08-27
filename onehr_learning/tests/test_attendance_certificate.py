from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRLearningCommon


@tagged("post_install", "-at_install", "onehr_learning")
class TestLearningAttendanceAndCertificate(OneHRLearningCommon):
    def _attendance_ready(self):
        enrollment = self.enrolled_participant()
        enrollment.session_id.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        return enrollment, attendance

    def test_25_assigned_trainer_can_create_training_attendance(self):
        enrollment, attendance = self._attendance_ready()
        self.assertEqual(attendance.enrollment_id, enrollment)
        self.assertEqual(attendance.attendance_status, "not_recorded")

    def test_26_present_attendance_advances_enrollment_to_attended(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.invalidate_recordset()
        self.assertEqual(attendance.attendance_status, "present")
        self.assertEqual(enrollment.state, "attended")
        self.assertEqual(attendance.attendance_percent, 100.0)

    def test_27_attended_participant_can_be_evaluated_passed(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "passed")

    def test_28_failed_result_uses_course_pass_score(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 40.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "failed")

    def test_29_issue_certificate_advances_enrollment_to_certified(self):
        course = self.make_course(code="CERT-ISS", certificate_validity_months=12)
        session = self.make_session(course=course)
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 95.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        action = enrollment.with_user(self.officer_user).action_issue_certificate()
        certificate = self.env["onehr.learning.certificate"].browse(action["res_id"])
        enrollment.invalidate_recordset()
        self.assertEqual(certificate.state, "valid")
        self.assertEqual(enrollment.state, "certified")
        self.assertTrue(certificate.valid_to)

    def test_30_absent_attendance_marks_no_show(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_absent()
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "no_show")

    def test_31_work_attendance_sync_requires_session_opt_in(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_present()
        with self.assertRaises(UserError):
            attendance.with_user(self.officer_user).action_sync_work_attendance()

    def test_32_final_result_score_is_immutable(self):
        enrollment, attendance = self._attendance_ready()
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        with self.assertRaises(AccessError):
            enrollment.with_user(self.officer_user).write({"post_test_score": 91.0})

    def test_33_certificate_revocation_requires_reason(self):
        course = self.make_course(code="CERT-REV")
        session = self.make_session(course=course)
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        action = enrollment.with_user(self.officer_user).action_issue_certificate()
        certificate = self.env["onehr.learning.certificate"].browse(action["res_id"])
        with self.assertRaises(UserError):
            certificate.with_user(self.manager_user).action_revoke()
        certificate.with_user(self.manager_user).write(
            {"revocation_reason": "Issued in error"}
        )
        certificate.with_user(self.manager_user).action_revoke()
        self.assertEqual(certificate.state, "revoked")

    def test_34_certificate_print_uses_qweb_report(self):
        course = self.make_course(code="CERT-PRINT")
        session = self.make_session(course=course)
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        action = enrollment.with_user(self.officer_user).action_issue_certificate()
        certificate = self.env["onehr.learning.certificate"].browse(action["res_id"])
        report_action = certificate.with_user(self.officer_user).action_print_certificate()
        self.assertEqual(report_action["type"], "ir.actions.report")

    def test_35_document_push_never_bypasses_optional_document_authority(self):
        course = self.make_course(code="CERT-DOC")
        session = self.make_session(course=course)
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        action = enrollment.with_user(self.officer_user).action_issue_certificate()
        certificate = self.env["onehr.learning.certificate"].browse(action["res_id"])
        with self.assertRaises((AccessError, UserError)):
            certificate.with_user(self.officer_user).action_push_to_document()

    def test_36_certificate_expiry_scheduler_retains_history(self):
        course = self.make_course(
            code="CERT-EXP",
            certificate_validity_months=1,
            certificate_reminder_days=5,
        )
        session = self.make_session(course=course)
        enrollment = self.enrolled_participant(self.make_enrollment(session=session))
        session.with_user(self.officer_user).action_start()
        attendance = self.env["onehr.learning.attendance"].with_user(
            self.trainer_user
        ).create({"enrollment_id": enrollment.id})
        attendance.with_user(self.trainer_user).action_mark_present()
        enrollment.with_user(self.trainer_user).write({"post_test_score": 90.0})
        enrollment.with_user(self.trainer_user).action_evaluate_result()
        action = enrollment.with_user(self.officer_user).action_issue_certificate()
        certificate = self.env["onehr.learning.certificate"].browse(action["res_id"])

        # Test-only date travel setup; business users cannot write lifecycle evidence directly.
        certificate._write_governed(
            {"valid_to": fields.Date.today() - timedelta(days=1)}
        )
        self.env["onehr.learning.certificate"]._cron_process_certificate_expiry()
        certificate.invalidate_recordset()
        self.assertEqual(certificate.state, "expired")
        self.assertTrue(certificate.exists())
