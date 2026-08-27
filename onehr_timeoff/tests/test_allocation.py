from odoo.fields import Command
from odoo.exceptions import AccessError, ValidationError

from .common import OneHRTimeOffCommon


class TestOneHRLeaveAllocation(OneHRTimeOffCommon):
    def test_05_single_allocation_confirm(self):
        allocation = self.make_allocation(days=12.0)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.available_on(self.future_monday), 12.0)

    def test_06_confirmed_allocation_is_immutable(self):
        allocation = self.make_allocation()
        with self.assertRaises(AccessError):
            allocation.with_user(self.hr_user).write({"allocated_days": 20.0})

    def test_07_mass_allocation_generates_audited_children(self):
        batch = self.env["onehr.leave.allocation"].with_user(self.hr_user).create({
            "company_id": self.company.id,
            "allocation_scope": "mass",
            "employee_ids": [Command.set([self.employee.id, self.manager_employee.id])],
            "leave_type_id": self.leave_type.id,
            "source": "mass",
            "period_start": self.year_start,
            "period_end": self.year_end,
            "allocated_days": 3.0,
        })
        batch.with_user(self.hr_user).action_generate_mass_allocations()
        self.assertEqual(batch.state, "confirmed")
        self.assertEqual(len(batch.generated_allocation_ids), 2)
        self.assertTrue(all(row.state == "confirmed" for row in batch.generated_allocation_ids))

    def test_08_duplicate_scheduler_source_key_rejected(self):
        self.make_allocation(source_key="TEST-IDEMPOTENCY")
        with self.assertRaises(Exception):
            self.env["onehr.leave.allocation"].with_user(self.hr_user).create({
                "company_id": self.company.id,
                "allocation_scope": "single",
                "employee_id": self.employee.id,
                "leave_type_id": self.leave_type.id,
                "source": "manual",
                "period_start": self.year_start,
                "period_end": self.year_end,
                "allocated_days": 1.0,
                "source_key": "TEST-IDEMPOTENCY",
            })

    def test_09_user_cannot_create_entitlement(self):
        with self.assertRaises(AccessError):
            self.env["onehr.leave.allocation"].with_user(self.employee_user).create({
                "company_id": self.company.id,
                "allocation_scope": "single",
                "employee_id": self.employee.id,
                "leave_type_id": self.leave_type.id,
                "source": "manual",
                "period_start": self.year_start,
                "period_end": self.year_end,
                "allocated_days": 1.0,
            })
