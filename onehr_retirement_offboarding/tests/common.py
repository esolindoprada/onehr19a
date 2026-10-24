from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class OffboardingCase(TransactionCase):
    """Small deterministic runtime fixture shared by post-install tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env["hr.employee"].sudo()
        cls.Clearance = cls.env["onehr.clearance.item"].sudo()
        cls.Case = cls.env["onehr.offboarding"].sudo()
        cls.Checklist = cls.env["onehr.offboarding.checklist"].sudo()
        cls.Interview = cls.env["onehr.exit.interview"].sudo()
        cls.employee = cls.Employee.create(
            {"name": "OneHR Offboarding Runtime Employee", "company_id": cls.env.company.id}
        )
        cls.item = cls.Clearance.create(
            {
                "name": "Return Company Access Card",
                "code": "TEST-CARD",
                "category": "security",
                "owner_role": "hr",
                "mandatory": True,
                "sla_days": 1,
                "offboarding_type": "all",
            }
        )
        cls.case = cls.Case.create(
            {
                "employee_id": cls.employee.id,
                "offboarding_type": "resignation",
                "request_date": fields.Date.today(),
                "proposed_exit_date": fields.Date.today() + timedelta(days=14),
                "exit_reason_code": "career",
            }
        )

    def _task(self, **overrides):
        values = {
            "offboarding_id": self.case.id,
            "clearance_item_id": self.item.id,
            "sequence": 10,
            "item_code": self.item.code,
            "title": self.item.name,
            "category": self.item.category,
            "owner_role": self.item.owner_role,
            "mandatory": True,
            "due_date": self.case.proposed_exit_date,
            "return_status": "not_applicable",
        }
        values.update(overrides)
        return self.Checklist.with_context(onehr_offboarding_generate_tasks=True).create(values)
