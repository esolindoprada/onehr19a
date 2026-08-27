from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRCareerSuccessionCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"Talent Other Company {cls.__name__}"}
        )

        cls.group_hrbp = cls.env.ref(
            "onehr_career_succession.group_onehr_career_hrbp"
        )
        cls.group_manager = cls.env.ref(
            "onehr_career_succession.group_onehr_talent_manager"
        )
        cls.group_internal = cls.env.ref("base.group_user")

        def make_user(name, login, groups, company):
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set(groups.ids)],
                }
            )

        suffix = cls.__name__.lower()
        cls.hrbp_user = make_user(
            "Career HRBP",
            f"career_hrbp_{suffix}",
            cls.group_hrbp,
            cls.company,
        )
        cls.talent_manager = make_user(
            "Talent Manager",
            f"career_manager_{suffix}",
            cls.group_manager,
            cls.company,
        )
        cls.plain_user = make_user(
            "Plain User",
            f"career_plain_{suffix}",
            cls.group_internal,
            cls.company,
        )

        cls.job = cls.env["hr.job"].create(
            {
                "name": "Talent Test Job",
                "company_id": cls.company.id,
            }
        )
        cls.department = cls.env["hr.department"].create(
            {
                "name": "Talent Test Department",
                "company_id": cls.company.id,
            }
        )
        cls.position = cls.env["onehr.position"].create(
            {
                "code": f"TAL-POS-{suffix}",
                "name": "Critical Talent Position",
                "company_id": cls.company.id,
                "job_id": cls.job.id,
                "department_id": cls.department.id,
                "authorized_fte": 1.0,
                "authorized_headcount": 1,
                "status": "filled",
                "valid_from": fields.Date.today(),
            }
        )
        cls.manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Talent Line Manager",
                "company_id": cls.company.id,
                "user_id": cls.talent_manager.id,
                "job_id": cls.job.id,
                "department_id": cls.department.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Talent Employee",
                "company_id": cls.company.id,
                "parent_id": cls.manager_employee.id,
                "job_id": cls.job.id,
                "department_id": cls.department.id,
                "onehr_employee_number": f"TAL-{suffix}",
            }
        )

    def make_competency(self, **extra):
        values = {
            "code": f"COMP-{self._testMethodName}",
            "name": "Strategic Leadership",
            "company_id": self.company.id,
            "category": "leadership",
            "level_min": 1,
            "level_max": 5,
        }
        values.update(extra)
        return self.env["onehr.competency"].with_user(
            self.hrbp_user
        ).create(values)

    def make_requirement(self, competency=None, **extra):
        competency = competency or self.make_competency()
        values = {
            "position_id": self.position.id,
            "competency_id": competency.id,
            "required_level": 4,
            "weight": 100.0,
            "mandatory": True,
        }
        values.update(extra)
        return self.env["onehr.position.competency"].with_user(
            self.hrbp_user
        ).create(values)

    def make_talent(self, **extra):
        values = {
            "pool_code": f"HIPOT-{self._testMethodName}",
            "company_id": self.company.id,
            "employee_id": self.employee.id,
            "target_position_id": self.position.id,
            "performance_score": 80.0,
            "potential_score": 90.0,
            "competency_score": 75.0,
            "learning_score": 85.0,
            "high_potential": True,
        }
        values.update(extra)
        return self.env["onehr.talent.pool"].with_user(
            self.hrbp_user
        ).create(values)

    def activate_talent(self, talent):
        talent.with_user(self.hrbp_user).action_propose()
        talent.with_user(self.talent_manager).action_approve()
        talent.with_user(self.talent_manager).action_activate()
        return talent

    def make_plan(self, talent=None, **extra):
        talent = talent or self.make_talent()
        values = {
            "title": f"Succession {self._testMethodName}",
            "company_id": self.company.id,
            "position_id": self.position.id,
            "incumbent_employee_id": self.manager_employee.id,
            "criticality": "critical",
            "vacancy_risk": "high",
            "business_impact": "critical",
            "review_date": fields.Date.today() + timedelta(days=30),
            "target_coverage": 1,
            "candidate_talent_ids": [Command.set([talent.id])],
        }
        values.update(extra)
        return self.env["onehr.succession.plan"].with_user(
            self.hrbp_user
        ).create(values)
