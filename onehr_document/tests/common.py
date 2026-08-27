from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRDocumentCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "OneHR Document Other Company"}
        )

        def make_user(name, login, groups, companies=None):
            companies = companies or [cls.company]
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": companies[0].id,
                    "company_ids": [Command.set([company.id for company in companies])],
                    "group_ids": [
                        Command.link(cls.env.ref(group_xmlid).id)
                        for group_xmlid in groups
                    ],
                }
            )

        cls.self_user = make_user(
            "Document Employee User",
            "onehr_document_self",
            ["onehr_document.group_onehr_document_user"],
        )
        cls.officer = make_user(
            "Document Officer",
            "onehr_document_officer",
            ["onehr_document.group_onehr_document_officer"],
        )
        cls.manager = make_user(
            "Document Manager",
            "onehr_document_manager",
            ["onehr_document.group_onehr_document_manager"],
        )
        cls.compliance = make_user(
            "Document Compliance",
            "onehr_document_compliance",
            ["onehr_document.group_onehr_document_compliance"],
        )
        cls.restricted_manager = make_user(
            "Restricted Document Manager",
            "onehr_document_restricted_manager",
            [
                "onehr_document.group_onehr_document_manager",
                "onehr_document.group_onehr_document_compliance",
            ],
        )
        cls.other_officer = make_user(
            "Other Company Document Officer",
            "onehr_document_other_officer",
            ["onehr_document.group_onehr_document_officer"],
            companies=[cls.other_company],
        )
        cls.other_manager = make_user(
            "Other Company Document Manager",
            "onehr_document_other_manager",
            ["onehr_document.group_onehr_document_manager"],
            companies=[cls.other_company],
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Document Employee",
                "company_id": cls.company.id,
                "user_id": cls.self_user.id,
                "work_email": "employee@example.test",
            }
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {
                "name": "Other Document Employee",
                "company_id": cls.other_company.id,
            }
        )

        today = fields.Date.today()
        Category = cls.env["onehr.document.category"]
        cls.internal_category = Category.with_user(cls.manager).create(
            {
                "code": "INTERNAL",
                "name": "Internal HR Document",
                "company_id": cls.company.id,
                "sensitivity": "internal",
                "employee_visible": True,
                "default_validity_days": 365,
                "default_reminder_days": 30,
                "retention_days_after_expiry": 365,
                "valid_from": today,
            }
        )
        cls.confidential_category = Category.with_user(cls.manager).create(
            {
                "code": "CONFIDENTIAL",
                "name": "Confidential HR Document",
                "company_id": cls.company.id,
                "sensitivity": "confidential",
                "employee_visible": False,
                "valid_from": today,
            }
        )
        cls.restricted_category = Category.with_user(
            cls.restricted_manager
        ).create(
            {
                "code": "RESTRICTED",
                "name": "Restricted HR Document",
                "company_id": cls.company.id,
                "sensitivity": "restricted",
                "employee_visible": False,
                "valid_from": today,
            }
        )

        cls.template = cls.env["onehr.document.template"].with_user(
            cls.manager
        ).create(
            {
                "code": "EMP-LETTER",
                "name": "Employee Letter",
                "category_id": cls.internal_category.id,
                "company_id": cls.company.id,
                "valid_from": today,
            }
        )
        cls.template_version = cls.env[
            "onehr.document.template.version"
        ].with_user(cls.manager).create(
            {
                "template_id": cls.template.id,
                "version": 1,
                "subject_template": "Letter - {{ employee.name }}",
                "body_html": (
                    "<p>Employee {{ employee.name }} "
                    "({{ employee.onehr_employee_number }})</p>"
                ),
                "filename_template": "{{ employee.onehr_employee_number }}-letter.pdf",
                "valid_from": today,
            }
        )
        cls.template_version.with_user(cls.manager).action_activate()

    def create_document(self, *, category=None, user=None, employee=None, source=False):
        category = category or self.internal_category
        user = user or self.officer
        employee = self.employee if employee is None else employee
        values = {
            "name": "Employment Letter",
            "category_id": category.id,
            "company_id": self.company.id,
            "employee_id": employee.id if employee else False,
            "responsible_user_id": user.id,
            "valid_from": fields.Date.today(),
        }
        if source:
            values.update(
                {
                    "source_model_id": self.env["ir.model"]._get("hr.employee").id,
                    "source_res_id": self.employee.id,
                }
            )
        return self.env["onehr.document"].with_user(user).create(values)

    def create_draft_version(self, document=None, user=None, **extra):
        document = document or self.create_document(user=user)
        user = user or self.officer
        values = {
            "document_id": document.id,
            "effective_from": fields.Date.today(),
            "rendered_subject": "Controlled Letter",
            "rendered_content_html": "<p>Controlled content</p>",
        }
        values.update(extra)
        return self.env["onehr.document.version"].with_user(user).create(values)
