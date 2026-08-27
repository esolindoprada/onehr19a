from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRCommon


@tagged("post_install", "-at_install", "onehr_base")
class TestChecklistSecurity(OneHRCommon):
    def test_template_overlap_dependency_cycle_and_new_version(self):
        today = fields.Date.today()
        first = self.active_template("MOVE", 1, today)
        first.write({"valid_to": today + timedelta(days=10), "state": "active"})
        second = self.active_template("MOVE", 2, today + timedelta(days=5))
        with self.assertRaises(ValidationError):
            second.action_activate()

        task1 = self.env["onehr.checklist.task.template"].create(
            {"template_id": first.id, "name": "First"}
        )
        task2 = self.env["onehr.checklist.task.template"].create(
            {
                "template_id": first.id,
                "name": "Second",
                "dependency_ids": [(6, 0, task1.ids)],
            }
        )
        with self.assertRaises(ValidationError):
            task1.dependency_ids = [(6, 0, task2.ids)]

        new_version_action = first.action_create_new_version()
        new_version = self.env["onehr.checklist.template"].browse(
            new_version_action["res_id"]
        )
        self.assertEqual(new_version.version, 3)
        self.assertEqual(new_version.state, "draft")
        self.assertEqual(
            len(new_version.task_template_ids), len(first.task_template_ids)
        )
        copied_second = new_version.task_template_ids.filtered(
            lambda row: row.name == "Second"
        )
        self.assertEqual(len(copied_second), 1)
        self.assertTrue(copied_second.dependency_ids)
        self.assertEqual(copied_second.dependency_ids.template_id, new_version)

    def test_allocation_freezes_actions_and_completion_idempotency(self):
        template = self.active_template()
        source = self.env["onehr.checklist.task.template"].create(
            {
                "template_id": template.id,
                "name": "Collect Documents",
                "instructions": "Original",
                "due_offset_days": 2,
                "performer_policy": "specific_user",
                "performer_user_id": self.manager.id,
            }
        )
        template.action_activate()
        instance = self.env["onehr.checklist.instance"].create(
            {
                "employee_id": self.employee.id,
                "company_id": self.company.id,
                "template_id": template.id,
                "event_date": fields.Date.today(),
            }
        )
        self.assertEqual(instance.task_count, 1)
        self.assertEqual(instance.pending_task_count, 1)
        frozen = instance.task_ids
        self.assertEqual(frozen.name, "Collect Documents")
        self.assertEqual(
            frozen.due_date, fields.Date.today() + timedelta(days=2)
        )
        source.write({"name": "Changed", "instructions": "Changed"})
        self.assertEqual(frozen.name, "Collect Documents")

        instance.action_schedule_outstanding_activities()
        self.assertTrue(frozen.activity_id)
        frozen.action_done(note="Done")
        completed_at = frozen.completed_at
        frozen.action_done(note="Ignored")
        self.assertEqual(frozen.completed_at, completed_at)
        instance.action_complete()
        self.assertEqual(instance.state, "completed")
        with self.assertRaises(UserError):
            frozen.write({"completion_note": "Rewritten"})

    def test_multi_company_rule_and_access(self):
        hidden = self.env["onehr.grade"].create(
            {
                "code": "HIDDEN",
                "name": "Hidden",
                "company_id": self.other_company.id,
            }
        )
        visible_ids = self.env["onehr.grade"].with_user(self.officer).search([]).ids
        self.assertNotIn(hidden.id, visible_ids)

        with self.assertRaises(AccessError):
            self.env["onehr.job.family"].with_user(self.officer).create(
                {"code": "OFFICER-CREATE", "name": "Not Allowed"}
            )
        managed = self.env["onehr.job.family"].with_user(self.manager).create(
            {"code": "MGR", "name": "Manager"}
        )
        managed.with_user(self.manager).write({"name": "Manager Updated"})
        managed.with_user(self.manager).unlink()

    def test_completed_history_and_source_reference_protected(self):
        template = self.active_template("PROTECT")
        self.env["onehr.checklist.task.template"].create(
            {"template_id": template.id, "name": "Task"}
        )
        template.action_activate()

        with self.assertRaises(ValidationError):
            self.env["onehr.checklist.instance"].create(
                {
                    "employee_id": self.employee.id,
                    "company_id": self.company.id,
                    "template_id": template.id,
                    "source_model": "hr.employee",
                }
            )

        instance = self.env["onehr.checklist.instance"].create(
            {
                "employee_id": self.employee.id,
                "company_id": self.company.id,
                "template_id": template.id,
                "source_model": "hr.employee",
                "source_res_id": self.employee.id,
            }
        )
        task = instance.task_ids
        task.action_done()
        instance.action_complete()
        with self.assertRaises(UserError):
            instance.with_user(self.manager).unlink()
        with self.assertRaises(UserError):
            task.with_user(self.manager).unlink()
