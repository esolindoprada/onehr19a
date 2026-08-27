from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRRecruitmentCommon


@tagged("post_install", "-at_install", "onehr_recruitment")
class TestRecruitmentInterview(OneHRRecruitmentCommon):
    def test_06_template_version_and_effective_identity(self):
        self.assertEqual(self.template.code, "INT-ENG")
        self.assertEqual(self.template.version, 1)
        self.assertEqual(self.template.state, "active")
        action = self.template.with_user(self.manager).action_create_new_version()
        self.assertEqual(action["res_model"], "onehr.interview.template")
        version2 = self.env["onehr.interview.template"].browse(action["res_id"])
        self.assertEqual(version2.version, 2)
        self.assertEqual(version2.state, "draft")

    def test_07_session_freezes_template_identity(self):
        session = self.make_session()
        self.assertEqual(session.template_code_snapshot, self.template.code)
        self.assertEqual(session.template_version_snapshot, self.template.version)

    def test_08_session_schedule_validation(self):
        session = self.make_session()
        with self.assertRaises(ValidationError):
            session.with_user(self.manager).write({"scheduled_end": session.scheduled_start})

    def test_09_assigned_interviewer_can_score_and_finalize(self):
        session = self.make_session()
        session.with_user(self.manager).action_confirm()
        score = self.env["onehr.interview.score"].with_user(self.hiring_manager).create({
            "session_id": session.id,
            "rater_user_id": self.hiring_manager.id,
            "overall_score": 4.2,
            "recommendation": "yes",
        })
        score.with_user(self.hiring_manager).action_finalize()
        self.assertEqual(score.state, "final")
        with self.assertRaises(AccessError):
            score.with_user(self.hiring_manager).write({"comments": "rewrite"})

    def test_10_score_correction_supersedes_without_rewriting(self):
        session = self.make_session()
        session.with_user(self.manager).action_confirm()
        score = self.env["onehr.interview.score"].with_user(self.manager).create({
            "session_id": session.id,
            "rater_user_id": self.hiring_manager.id,
            "overall_score": 4.0,
            "recommendation": "yes",
        })
        score.with_user(self.manager).action_finalize()
        action = score.with_user(self.manager).action_create_correction()
        correction = self.env["onehr.interview.score"].browse(action["res_id"])
        self.assertEqual(score.state, "superseded")
        self.assertEqual(correction.state, "draft")
        self.assertEqual(correction.supersedes_id, score)
