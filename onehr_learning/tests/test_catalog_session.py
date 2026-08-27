import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRLearningCommon


@tagged("post_install", "-at_install", "onehr_learning")
class TestLearningCatalogAndSession(OneHRLearningCommon):
    def test_01_course_catalog_create_and_publish(self):
        course = self.make_course(code="CAT-01")
        self.assertTrue(course.published)
        self.assertTrue(course.active)

    def test_02_officer_cannot_publish_course(self):
        course = self.make_course(code="CAT-02", publish=False)
        with self.assertRaises(AccessError):
            course.with_user(self.officer_user).action_publish()

    def test_03_published_course_cannot_be_archived_directly(self):
        course = self.make_course(code="CAT-03")
        with self.assertRaises(ValidationError):
            course.with_user(self.officer_user).write({"active": False})

    def test_04_direct_prerequisite_cycle_is_rejected(self):
        first = self.make_course(code="PR-01")
        second = self.make_course(code="PR-02")
        first.with_user(self.officer_user).write(
            {"prerequisite_course_ids": [(6, 0, second.ids)]}
        )
        with self.assertRaises(ValidationError):
            second.with_user(self.officer_user).write(
                {"prerequisite_course_ids": [(6, 0, first.ids)]}
            )

    def test_05_vendor_rating_validation(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.learning.vendor"].with_user(self.officer_user).create(
                {
                    "name": "Invalid Vendor",
                    "code": "V-INVALID",
                    "company_id": self.company.id,
                    "rating": 6.0,
                }
            )

    def test_06_session_open_requires_published_course(self):
        course = self.make_course(code="SES-UNPUB", publish=False)
        session = self.make_session(course=course, open_enrollment=False)
        with self.assertRaises(UserError):
            session.with_user(self.manager_user).action_open_enrollment()

    def test_07_session_datetime_validation(self):
        course = self.make_course(code="SES-DATE")
        now = fields.Datetime.now() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.make_session(
                course=course,
                open_enrollment=False,
                start_datetime=now,
                end_datetime=now,
            )

    def test_08_session_start_requires_enrolled_participant(self):
        session = self.make_session()
        with self.assertRaises(UserError):
            session.with_user(self.officer_user).action_start()

    def test_09_session_lifecycle_open_start_complete(self):
        session = self.make_session()
        enrollment = self.enrolled_participant(
            self.make_enrollment(session=session)
        )
        self.assertEqual(enrollment.state, "enrolled")
        session.with_user(self.officer_user).action_start()
        self.assertEqual(session.state, "in_progress")
        session.with_user(self.officer_user).action_complete()
        self.assertEqual(session.state, "completed")
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "no_show")

    def test_10_participant_csv_import_creates_draft_only(self):
        session = self.make_session()
        content = (
            "employee_number,request_reason\n"
            f"{self.participant.onehr_employee_number},Imported development\n"
        ).encode("utf-8")
        session.with_user(self.officer_user).write(
            {
                "participant_import_file": base64.b64encode(content),
                "participant_import_filename": "participants.csv",
            }
        )
        session.with_user(self.officer_user).action_import_participants_csv()
        enrollment = self.env["onehr.learning.enrollment"].search(
            [("session_id", "=", session.id), ("employee_id", "=", self.participant.id)]
        )
        self.assertEqual(enrollment.state, "draft")

    def test_11_results_csv_export_is_generated(self):
        session = self.make_session()
        self.make_enrollment(session=session)
        action = session.with_user(self.officer_user).action_export_results_csv()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(session.result_download_file)

    def test_12_session_capacity_waitlist_processing(self):
        session = self.make_session(capacity=1)
        first = self.enrolled_participant(self.make_enrollment(session=session))
        second = self.approve_enrollment(
            self.make_enrollment(session=session, employee=self.participant2)
        )
        second.with_user(self.officer_user).action_enroll()
        self.assertEqual(first.state, "enrolled")
        self.assertEqual(second.state, "waitlisted")
        first.with_user(self.officer_user).action_cancel()
        session.with_user(self.officer_user).action_process_waitlist()
        second.invalidate_recordset()
        self.assertEqual(second.state, "enrolled")
