from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRLearningCommon


@tagged("post_install", "-at_install", "onehr_learning")
class TestLearningEnrollmentWorkflow(OneHRLearningCommon):
    def test_13_workflow_auto_approval_calls_source_hook(self):
        enrollment = self.make_enrollment()
        action = enrollment.with_user(self.officer_user).action_request_approval()
        self.assertEqual(action["res_model"], "onehr.approval.request")
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "approved")
        self.assertEqual(enrollment.onehr_latest_approval_state, "approved")

    def test_14_approval_execution_marks_request_executed(self):
        enrollment = self.approve_enrollment()
        enrollment.with_user(self.officer_user).action_enroll()
        enrollment.invalidate_recordset()
        self.assertIn(enrollment.state, {"enrolled", "waitlisted"})
        request = self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", enrollment._name),
                ("source_res_id", "=", enrollment.id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertEqual(request.state, "executed")

    def test_15_missing_prerequisite_blocks_request(self):
        prerequisite = self.make_course(code="REQ-BASE")
        course = self.make_course(code="REQ-ADV")
        course.with_user(self.officer_user).write(
            {"prerequisite_course_ids": [(6, 0, prerequisite.ids)]}
        )
        session = self.make_session(course=course)
        enrollment = self.make_enrollment(session=session)
        with self.assertRaises(ValidationError):
            enrollment.with_user(self.officer_user).action_request_approval()

    def test_16_manager_prerequisite_override_allows_request(self):
        prerequisite = self.make_course(code="OVR-BASE")
        course = self.make_course(code="OVR-ADV")
        course.with_user(self.officer_user).write(
            {"prerequisite_course_ids": [(6, 0, prerequisite.ids)]}
        )
        session = self.make_session(course=course)
        enrollment = self.make_enrollment(session=session)
        enrollment.with_user(self.officer_user).write(
            {"prerequisite_override_reason": "Equivalent external qualification"}
        )
        enrollment.with_user(self.manager_user).action_approve_prerequisite_override()
        enrollment.with_user(self.officer_user).action_request_approval()
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "approved")

    def test_17_enrollment_identity_frozen_after_submission(self):
        enrollment = self.approve_enrollment()
        with self.assertRaises(AccessError):
            enrollment.with_user(self.officer_user).write(
                {"external_reference": "CHANGED"}
            )

    def test_18_trainer_cannot_reassign_enrollment(self):
        enrollment = self.enrolled_participant()
        with self.assertRaises(AccessError):
            enrollment.with_user(self.trainer_user).write(
                {"session_id": enrollment.session_id.id}
            )

    def test_19_assigned_trainer_can_enter_scores(self):
        enrollment = self.enrolled_participant()
        enrollment.with_user(self.trainer_user).write(
            {"pre_test_score": 55.0, "post_test_score": 85.0}
        )
        self.assertEqual(enrollment.post_test_score, 85.0)

    def test_20_unassigned_trainer_cannot_enter_scores(self):
        enrollment = self.enrolled_participant()
        with self.assertRaises(AccessError):
            enrollment.with_user(self.other_trainer_user).write(
                {"post_test_score": 90.0}
            )

    def test_21_training_leave_requires_configured_leave_code(self):
        enrollment = self.approve_enrollment()
        with self.assertRaises(UserError):
            enrollment.with_user(self.officer_user).action_generate_training_leave()

    def test_22_external_enrollment_service_is_idempotent(self):
        session = self.make_session()
        payload = {
            "external_system": "LMS",
            "external_reference": "EXT-001",
            "employee_number": self.participant.onehr_employee_number,
            "session_reference": session.name,
            "request_reason": "LMS assignment",
        }
        first = self.env["onehr.learning.enrollment"].with_user(
            self.officer_user
        ).onehr_external_enroll(payload)
        second = self.env["onehr.learning.enrollment"].with_user(
            self.officer_user
        ).onehr_external_enroll(payload)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["enrollment_id"], second["enrollment_id"])

    def test_23_external_result_hash_is_retained(self):
        enrollment = self.make_enrollment(
            external_system="LMS",
            external_reference="RESULT-001",
        )
        payload = {
            "external_system": "LMS",
            "external_reference": "RESULT-001",
            "post_test_score": 88.0,
        }
        result = self.env["onehr.learning.enrollment"].with_user(
            self.officer_user
        ).onehr_ingest_external_result(payload)
        self.assertEqual(len(result["payload_sha256"]), 64)

    def test_24_cancel_draft_enrollment_retains_record(self):
        enrollment = self.make_enrollment()
        enrollment.with_user(self.officer_user).action_cancel()
        self.assertEqual(enrollment.state, "cancelled")
        self.assertTrue(enrollment.exists())
