from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OffboardingCase


@tagged("post_install", "-at_install", "onehr_retirement_offboarding")
class TestChecklistAndInterview(OffboardingCase):
    def test_01_clearance_catalogue_model_exists(self):
        self.assertEqual(self.env["onehr.clearance.item"]._name, "onehr.clearance.item")

    def test_02_checklist_model_exists(self):
        self.assertEqual(self.env["onehr.offboarding.checklist"]._name, "onehr.offboarding.checklist")

    def test_03_exit_interview_model_exists(self):
        self.assertEqual(self.env["onehr.exit.interview"]._name, "onehr.exit.interview")

    def test_04_checklist_cannot_be_created_outside_generator(self):
        with self.assertRaises(AccessError):
            self.Checklist.create(
                {
                    "offboarding_id": self.case.id,
                    "clearance_item_id": self.item.id,
                    "item_code": self.item.code,
                    "title": self.item.name,
                    "category": self.item.category,
                    "owner_role": self.item.owner_role,
                    "mandatory": True,
                }
            )

    def test_05_generated_snapshot_fields_are_immutable(self):
        task = self._task()
        with self.assertRaises(ValidationError):
            task.write({"title": "Changed historical duty"})

    def test_06_direct_task_state_write_is_blocked(self):
        task = self._task()
        with self.assertRaises(ValidationError):
            task.write({"state": "done"})

    def test_07_duplicate_case_clearance_item_is_blocked(self):
        self._task()
        with self.assertRaises(Exception):
            self._task()

    def test_08_exit_interview_unique_per_case(self):
        self.Interview.create({"offboarding_id": self.case.id})
        with self.assertRaises(Exception):
            self.Interview.create({"offboarding_id": self.case.id})

    def test_09_exit_interview_score_average_is_computed(self):
        interview = self.Interview.create({"offboarding_id": self.case.id})
        interview.write(
            {
                "manager_relationship_score": 5,
                "role_clarity_score": 5,
                "rewards_score": 5,
                "culture_score": 5,
                "growth_score": 5,
                "work_life_score": 5,
            }
        )
        self.assertEqual(interview.overall_score, 5.0)

    def test_10_interview_submit_requires_exit_reason(self):
        interview = self.Interview.create({"offboarding_id": self.case.id})
        with self.assertRaises(UserError):
            interview.action_submit()
