from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRSOPCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"SOP Other Company {cls.__name__}"}
        )

        cls.group_reader = cls.env.ref("onehr_sop.group_onehr_sop_reader")
        cls.group_editor = cls.env.ref("onehr_sop.group_onehr_sop_editor")
        cls.group_approver = cls.env.ref("onehr_sop.group_onehr_sop_approver")
        cls.group_admin = cls.env.ref("onehr_sop.group_onehr_sop_admin")
        cls.group_internal = cls.env.ref("base.group_user")

        suffix = cls.__name__.lower()

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

        cls.reader = make_user(
            "SOP Reader",
            f"sop_reader_{suffix}",
            cls.group_reader,
            cls.company,
        )
        cls.reader_two = make_user(
            "SOP Reader Two",
            f"sop_reader2_{suffix}",
            cls.group_reader,
            cls.company,
        )
        cls.editor = make_user(
            "SOP QA Editor",
            f"sop_editor_{suffix}",
            cls.group_editor,
            cls.company,
        )
        cls.approver = make_user(
            "SOP Approver",
            f"sop_approver_{suffix}",
            cls.group_approver,
            cls.company,
        )
        cls.second_approver = make_user(
            "SOP Second Approver",
            f"sop_approver2_{suffix}",
            cls.group_approver,
            cls.company,
        )
        cls.admin = make_user(
            "SOP Administrator",
            f"sop_admin_{suffix}",
            cls.group_admin,
            cls.company,
        )
        cls.plain_user = make_user(
            "Plain Internal User",
            f"sop_plain_{suffix}",
            cls.group_internal,
            cls.company,
        )
        cls.other_editor = make_user(
            "Other Company SOP Editor",
            f"sop_other_editor_{suffix}",
            cls.group_editor,
            cls.other_company,
        )

        cls.department = cls.env["hr.department"].create(
            {
                "name": "SOP Finance Department",
                "company_id": cls.company.id,
            }
        )
        cls.other_department = cls.env["hr.department"].create(
            {
                "name": "SOP Other Company Department",
                "company_id": cls.other_company.id,
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "SOP Finance Analyst",
                "company_id": cls.company.id,
            }
        )
        cls.other_job = cls.env["hr.job"].create(
            {
                "name": "SOP Other Company Analyst",
                "company_id": cls.other_company.id,
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "SOP Employee One",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "user_id": cls.reader.id,
                "onehr_employee_number": f"SOP-E001-{suffix}",
                "work_email": f"sop.employee1.{suffix}@example.com",
            }
        )
        cls.employee_two = cls.env["hr.employee"].create(
            {
                "name": "SOP Employee Two",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "user_id": cls.reader_two.id,
                "onehr_employee_number": f"SOP-E002-{suffix}",
                "work_email": f"sop.employee2.{suffix}@example.com",
            }
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {
                "name": "SOP Other Employee",
                "company_id": cls.other_company.id,
                "department_id": cls.other_department.id,
                "job_id": cls.other_job.id,
                "user_id": cls.other_editor.id,
                "onehr_employee_number": f"SOP-O001-{suffix}",
            }
        )

        cls.document_category = cls.env["onehr.document.category"].with_user(
            cls.approver
        ).create(
            {
                "code": f"SOP-CAT-{suffix}",
                "name": "SOP Controlled Archive",
                "company_id": cls.company.id,
                "sensitivity": "internal",
                "employee_visible": False,
                "signature_required": False,
                "default_validity_days": 0,
                "default_reminder_days": 0,
                "default_grace_days": 0,
                "retention_days_after_expiry": 0,
                "valid_from": fields.Date.today(),
            }
        )
        cls.other_document_category = cls.env[
            "onehr.document.category"
        ].create(
            {
                "code": f"SOP-CAT-OTHER-{suffix}",
                "name": "Other SOP Archive",
                "company_id": cls.other_company.id,
                "sensitivity": "internal",
                "employee_visible": False,
                "signature_required": False,
                "valid_from": fields.Date.today(),
            }
        )

    def make_sop(self, **extra):
        values = {
            "name": f"SOP {self._testMethodName}",
            "company_id": self.company.id,
            "owner_user_id": self.editor.id,
            "document_category_id": self.document_category.id,
            "review_interval_months": 12,
            "retention_years": 7,
            "ack_reminder_days": 7,
        }
        values.update(extra)
        return self.env["onehr.sop"].with_user(self.editor).create(values)

    def complete_content(self, **extra):
        values = {
            "purpose": "<p>Standardize a controlled enterprise process.</p>",
            "scope": "<p>Applies to the defined company audience.</p>",
            "definitions": "<p>SOP means Standard Operating Procedure.</p>",
            "roles_responsibilities": "<p>Employees execute; QA owns control; Compliance approves.</p>",
            "procedure_steps": "<ol><li>Prepare.</li><li>Execute.</li><li>Verify.</li></ol>",
            "controls": "<p>Four-eyes review and documented evidence.</p>",
            "records_evidence": "<p>Retain required records according to policy.</p>",
            "training_requirements": "<p>Role training before execution.</p>",
            "safety_notes": "<p>Follow applicable HSE/K3 controls.</p>",
            "references": "<p>Related OneHR governance documents.</p>",
            "target_employee_ids": [
                Command.set([self.employee.id, self.employee_two.id])
            ],
        }
        values.update(extra)
        return values

    def make_version(self, sop=None, **extra):
        sop = sop or self.make_sop()
        values = {
            "sop_id": sop.id,
            **self.complete_content(),
        }
        values.update(extra)
        return self.env["onehr.sop.version"].with_user(
            self.editor
        ).create(values)

    def approve_version(self, version):
        version.with_user(self.editor).action_submit_review()
        version.with_user(self.approver).action_approve()
        return version

    def publish_version(self, version):
        self.approve_version(version)
        version.with_user(self.approver).action_publish()
        return version
