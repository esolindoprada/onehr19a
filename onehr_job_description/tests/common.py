import base64

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRJobDescriptionCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"JD Other Company {cls.__name__}"}
        )

        cls.group_reader = cls.env.ref(
            "onehr_job_description.group_onehr_jd_reader"
        )
        cls.group_editor = cls.env.ref(
            "onehr_job_description.group_onehr_jd_editor"
        )
        cls.group_approver = cls.env.ref(
            "onehr_job_description.group_onehr_jd_approver"
        )
        cls.group_admin = cls.env.ref(
            "onehr_job_description.group_onehr_jd_admin"
        )
        cls.group_internal = cls.env.ref("base.group_user")

        def make_user(name, login, group, company):
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set([group.id])],
                }
            )

        suffix = cls.__name__.lower()
        cls.reader = make_user(
            "JD Reader",
            f"jd_reader_{suffix}",
            cls.group_reader,
            cls.company,
        )
        cls.editor = make_user(
            "JD Editor",
            f"jd_editor_{suffix}",
            cls.group_editor,
            cls.company,
        )
        cls.approver = make_user(
            "JD Approver",
            f"jd_approver_{suffix}",
            cls.group_approver,
            cls.company,
        )
        cls.second_approver = make_user(
            "JD Second Approver",
            f"jd_approver2_{suffix}",
            cls.group_approver,
            cls.company,
        )
        cls.admin = make_user(
            "JD Administrator",
            f"jd_admin_{suffix}",
            cls.group_admin,
            cls.company,
        )
        cls.plain_user = make_user(
            "Plain Internal User",
            f"jd_plain_{suffix}",
            cls.group_internal,
            cls.company,
        )
        cls.other_editor = make_user(
            "Other Company JD Editor",
            f"jd_other_editor_{suffix}",
            cls.group_editor,
            cls.other_company,
        )

        cls.job_family = cls.env["onehr.job.family"].create(
            {
                "code": f"JD-FAM-{suffix}",
                "name": "Finance Leadership",
                "company_id": cls.company.id,
                "valid_from": fields.Date.today(),
            }
        )
        cls.other_job_family = cls.env["onehr.job.family"].create(
            {
                "code": f"JD-FAM-OTHER-{suffix}",
                "name": "Other Company Family",
                "company_id": cls.other_company.id,
                "valid_from": fields.Date.today(),
            }
        )
        cls.department = cls.env["hr.department"].create(
            {
                "name": "JD Finance Department",
                "company_id": cls.company.id,
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "JD Finance Director",
                "company_id": cls.company.id,
                "onehr_job_family_id": cls.job_family.id,
            }
        )
        cls.grade = cls.env["onehr.grade"].create(
            {
                "code": f"JD-GRADE-{suffix}",
                "name": "JD Grade",
                "company_id": cls.company.id,
                "valid_from": fields.Date.today(),
            }
        )
        cls.position = cls.env["onehr.position"].create(
            {
                "code": f"JD-POS-{suffix}",
                "name": "Finance Director",
                "company_id": cls.company.id,
                "job_id": cls.job.id,
                "department_id": cls.department.id,
                "grade_id": cls.grade.id,
                "authorized_fte": 1.0,
                "authorized_headcount": 1,
                "status": "filled",
                "valid_from": fields.Date.today(),
            }
        )

    def make_jd(self, **extra):
        values = {
            "name": f"JD {self._testMethodName}",
            "company_id": self.company.id,
            "position_id": self.position.id,
        }
        values.update(extra)
        return self.env["onehr.jd"].with_user(self.editor).create(values)

    def make_template(self, **extra):
        values = {
            "name": f"Template {self._testMethodName}",
            "company_id": self.company.id,
            "is_template": True,
            "job_family_id": self.job_family.id,
        }
        values.update(extra)
        return self.env["onehr.jd"].with_user(self.editor).create(values)

    def complete_content(self, **extra):
        values = {
            "purpose": "<p>Lead the finance function and enterprise stewardship.</p>",
            "key_responsibilities": "<ul><li>Own planning, control and reporting.</li></ul>",
            "kpi_expectations": "<p>Close quality, forecast accuracy and control effectiveness.</p>",
            "kpi_codes": "FIN-KPI-01, FIN-KPI-02",
            "competency_requirements": "<p>Strategic leadership and financial governance.</p>",
            "competency_codes": "LEAD-01, FIN-01",
            "qualification_requirements": "<p>Professional finance qualification.</p>",
            "education_requirements": "<p>Bachelor degree or equivalent.</p>",
            "experience_requirements": "<p>Relevant leadership experience.</p>",
            "skills_requirements": "<p>Financial leadership, analytics and communication.</p>",
            "authority_scope": "<p>Decision rights within approved delegations.</p>",
            "accountability": "<p>Accountable for finance governance outcomes.</p>",
            "reporting_relationships": "<p>Reports to executive leadership.</p>",
            "working_conditions": "<p>Office and business travel as required.</p>",
            "hse_risk_level": "low",
            "hse_risks": "<p>Ergonomic and travel exposure.</p>",
            "hse_controls": "<p>Follow company HSE controls.</p>",
            "ppe_requirements": "<p>As site conditions require.</p>",
        }
        values.update(extra)
        return values

    def make_version(self, jd=None, **extra):
        jd = jd or self.make_jd()
        values = {
            "jd_id": jd.id,
            **self.complete_content(),
        }
        values.update(extra)
        return self.env["onehr.jd.version"].with_user(
            self.editor
        ).create(values)

    def publish_version(self, version):
        version.with_user(self.editor).action_submit_review()
        version.with_user(self.approver).action_approve()
        version.with_user(self.approver).action_publish()
        return version
