from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRAppraisalCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"Appraisal Other Company {cls.__name__}"}
        )

        cls.group_participant = cls.env.ref(
            "onehr_appraisal.group_onehr_appraisal_participant"
        )
        cls.group_manager = cls.env.ref(
            "onehr_appraisal.group_onehr_appraisal_manager"
        )
        cls.group_hr = cls.env.ref("onehr_appraisal.group_onehr_appraisal_hr")
        cls.group_admin = cls.env.ref("onehr_appraisal.group_onehr_appraisal_admin")
        cls.group_internal = cls.env.ref("base.group_user")

        def make_user(name, login, group, company):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set(group.ids)],
                }
            )

        suffix = cls.__name__.lower()
        cls.hr_user = make_user(
            "Appraisal HR", f"appraisal_hr_{suffix}", cls.group_hr, cls.company
        )
        cls.admin_user = make_user(
            "Appraisal Admin", f"appraisal_admin_{suffix}", cls.group_admin, cls.company
        )
        cls.manager_user = make_user(
            "Appraisal Manager",
            f"appraisal_manager_{suffix}",
            cls.group_manager,
            cls.company,
        )
        cls.employee_user = make_user(
            "Appraisal Employee",
            f"appraisal_employee_{suffix}",
            cls.group_participant,
            cls.company,
        )
        cls.peer_user = make_user(
            "Appraisal Peer",
            f"appraisal_peer_{suffix}",
            cls.group_participant,
            cls.company,
        )
        cls.other_manager_user = make_user(
            "Other Appraisal Manager",
            f"appraisal_other_manager_{suffix}",
            cls.group_manager,
            cls.company,
        )
        cls.plain_user = make_user(
            "Plain Internal User",
            f"appraisal_plain_{suffix}",
            cls.group_internal,
            cls.company,
        )

        cls.manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Appraisal Line Manager",
                "company_id": cls.company.id,
                "user_id": cls.manager_user.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Appraisal Employee",
                "company_id": cls.company.id,
                "user_id": cls.employee_user.id,
                "parent_id": cls.manager_employee.id,
            }
        )
        cls.peer_employee = cls.env["hr.employee"].create(
            {
                "name": "Appraisal Peer",
                "company_id": cls.company.id,
                "user_id": cls.peer_user.id,
                "parent_id": cls.manager_employee.id,
            }
        )
        cls.other_manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Other Appraisal Manager",
                "company_id": cls.company.id,
                "user_id": cls.other_manager_user.id,
            }
        )

    def make_cycle(self, **extra):
        today = fields.Date.today()
        values = {
            "name": "Annual Performance Review",
            "code": f"APR-{self._testMethodName}",
            "company_id": self.company.id,
            "cycle_type": "annual",
            "date_start": today,
            "date_end": today + timedelta(days=90),
            "self_review_deadline": today + timedelta(days=30),
            "manager_review_deadline": today + timedelta(days=45),
            "consolidation_deadline": today + timedelta(days=60),
            "self_weight": 20.0,
            "manager_weight": 60.0,
            "peer_weight": 20.0,
        }
        values.update(extra)
        return self.env["onehr.appraisal.cycle"].with_user(self.hr_user).create(values)

    def add_template(self, cycle, **extra):
        values = {
            "cycle_id": cycle.id,
            "is_template": True,
            "rater_type": "target",
            "line_type": "kpi",
            "item_code": "KPI-01",
            "title": "Service Quality",
            "weight": 100.0,
            "target_value": 100.0,
        }
        values.update(extra)
        return self.env["onehr.appraisal.score"].with_user(self.hr_user).create(values)

    def make_form(self, cycle=None):
        cycle = cycle or self.make_cycle()
        if not cycle.template_score_ids:
            self.add_template(cycle)

        form = self.env["onehr.appraisal.form"].with_user(self.hr_user).create(
            {
                "cycle_id": cycle.id,
                "employee_id": self.employee.id,
                "manager_employee_id": self.manager_employee.id,
            }
        )
        target = self.env["onehr.appraisal.score"].with_user(self.hr_user).create(
            {
                "cycle_id": cycle.id,
                "form_id": form.id,
                "line_type": "kpi",
                "item_code": "KPI-01",
                "title": "Service Quality",
                "weight": 100.0,
                "target_value": 100.0,
                "rater_type": "target",
            }
        )
        self.env["onehr.appraisal.score"].with_user(self.hr_user).create(
            {
                "cycle_id": cycle.id,
                "form_id": form.id,
                "parent_score_id": target.id,
                "line_type": "kpi",
                "item_code": "KPI-01",
                "title": "Service Quality",
                "weight": 100.0,
                "rater_type": "self",
                "reviewer_employee_id": self.employee.id,
            }
        )
        self.env["onehr.appraisal.score"].with_user(self.hr_user).create(
            {
                "cycle_id": cycle.id,
                "form_id": form.id,
                "parent_score_id": target.id,
                "line_type": "kpi",
                "item_code": "KPI-01",
                "title": "Service Quality",
                "weight": 100.0,
                "rater_type": "manager",
                "reviewer_employee_id": self.manager_employee.id,
            }
        )
        return form

    def start_form(self, form):
        if form.cycle_id.state == "draft":
            form.cycle_id.with_user(self.hr_user).action_open_cycle()
        form.with_user(self.manager_user).action_start_review()
        return form
