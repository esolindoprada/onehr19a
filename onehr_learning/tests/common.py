from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRLearningCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"Learning Other Company {cls.__name__}"}
        )

        cls.group_officer = cls.env.ref("onehr_learning.group_onehr_learning_officer")
        cls.group_trainer = cls.env.ref("onehr_learning.group_onehr_learning_trainer")
        cls.group_manager = cls.env.ref(
            "onehr_learning.group_onehr_learning_manager_approver"
        )
        cls.group_internal = cls.env.ref("base.group_user")

        def make_user(name, login, groups, company):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set(groups.ids)],
                }
            )

        suffix = cls.__name__.lower()
        cls.manager_user = make_user(
            "Learning Manager",
            f"learning_manager_{suffix}",
            cls.group_manager,
            cls.company,
        )
        cls.officer_user = make_user(
            "Learning Officer",
            f"learning_officer_{suffix}",
            cls.group_officer,
            cls.company,
        )
        cls.trainer_user = make_user(
            "Learning Trainer",
            f"learning_trainer_{suffix}",
            cls.group_trainer,
            cls.company,
        )
        cls.other_trainer_user = make_user(
            "Other Learning Trainer",
            f"learning_other_trainer_{suffix}",
            cls.group_trainer,
            cls.company,
        )
        cls.plain_user = make_user(
            "Learning Plain User",
            f"learning_plain_{suffix}",
            cls.group_internal,
            cls.company,
        )

        cls.manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Learning Line Manager",
                "company_id": cls.company.id,
                "user_id": cls.manager_user.id,
                "onehr_employee_number": f"LM-{suffix[:10]}",
            }
        )
        cls.trainer_employee = cls.env["hr.employee"].create(
            {
                "name": "Learning Trainer Employee",
                "company_id": cls.company.id,
                "user_id": cls.trainer_user.id,
                "onehr_employee_number": f"LT-{suffix[:10]}",
            }
        )
        cls.participant = cls.env["hr.employee"].create(
            {
                "name": "Learning Participant",
                "company_id": cls.company.id,
                "parent_id": cls.manager_employee.id,
                "onehr_employee_number": f"LP-{suffix[:10]}",
            }
        )
        cls.participant2 = cls.env["hr.employee"].create(
            {
                "name": "Learning Participant 2",
                "company_id": cls.company.id,
                "parent_id": cls.manager_employee.id,
                "onehr_employee_number": f"LP2-{suffix[:10]}",
            }
        )

        # Workflow engine configuration is administrative test setup, not Learning
        # business execution. Auto-approval keeps test focus on the source hook contract.
        model = cls.env["ir.model"]._get("onehr.learning.enrollment")
        cls.approval_rule = cls.env["onehr.approval.rule"].create(
            {
                "code": f"LEARN-{suffix[:16]}",
                "name": f"Learning Enrollment {cls.__name__}",
                "company_id": cls.company.id,
                "model_id": model.id,
                "document_type": "learning_enrollment",
                "valid_from": fields.Date.today(),
                "minimum_distinct_approvers": 0,
                "auto_approve": True,
            }
        )
        cls.approval_rule.action_activate()

    def make_course(self, *, code="COURSE", publish=True, **values):
        vals = {
            "name": values.pop("name", f"Course {code}"),
            "code": code,
            "company_id": values.pop("company_id", self.company.id),
            "course_type": values.pop("course_type", "technical"),
            "duration_hours": values.pop("duration_hours", 2.0),
            "pass_score": values.pop("pass_score", 70.0),
        }
        vals.update(values)
        course = self.env["onehr.learning.course"].with_user(self.officer_user).create(vals)
        if publish:
            course.with_user(self.manager_user).action_publish()
        return course

    def make_session(self, *, course=None, capacity=2, open_enrollment=True, **values):
        course = course or self.make_course(code=f"C-{self.id()[-6:]}")
        start = values.pop("start_datetime", fields.Datetime.now() + timedelta(days=1))
        vals = {
            "title": values.pop("title", f"Session {course.code}"),
            "course_id": course.id,
            "company_id": course.company_id.id,
            "start_datetime": start,
            "end_datetime": values.pop("end_datetime", start + timedelta(hours=2)),
            "capacity": capacity,
            "waitlist_capacity": values.pop("waitlist_capacity", 2),
            "trainer_type": "internal",
            "trainer_employee_id": self.trainer_employee.id,
        }
        vals.update(values)
        session = self.env["onehr.learning.session"].with_user(self.officer_user).create(vals)
        if open_enrollment:
            session.with_user(self.manager_user).action_open_enrollment()
        return session

    def make_enrollment(self, session=None, employee=None, **values):
        session = session or self.make_session()
        employee = employee or self.participant
        vals = {
            "session_id": session.id,
            "employee_id": employee.id,
            "request_reason": values.pop("request_reason", "Development plan"),
        }
        vals.update(values)
        return self.env["onehr.learning.enrollment"].with_user(self.officer_user).create(vals)

    def approve_enrollment(self, enrollment=None):
        enrollment = enrollment or self.make_enrollment()
        enrollment.with_user(self.officer_user).action_request_approval()
        enrollment.invalidate_recordset()
        self.assertEqual(enrollment.state, "approved")
        return enrollment

    def enrolled_participant(self, enrollment=None):
        enrollment = self.approve_enrollment(enrollment)
        enrollment.with_user(self.officer_user).action_enroll()
        enrollment.invalidate_recordset()
        return enrollment

    def make_budget(self, *, allocated_amount=1000.0, activate=True, **values):
        today = fields.Date.today()
        vals = {
            "name": values.pop("name", "Learning Budget"),
            "code": values.pop("code", f"BUD-{self.id()[-6:]}"),
            "company_id": self.company.id,
            "period_start": values.pop("period_start", today),
            "period_end": values.pop("period_end", today + timedelta(days=365)),
            "allocated_amount": allocated_amount,
        }
        vals.update(values)
        budget = self.env["onehr.learning.budget"].with_user(self.manager_user).create(vals)
        if activate:
            budget.with_user(self.manager_user).action_activate()
        return budget
