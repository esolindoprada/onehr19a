
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRPortalCommon


@tagged("post_install", "-at_install", "onehr_portal_self_service")
class TestPortalSecurity(OneHRPortalCommon):
    def test_13_plain_internal_user_has_no_portal_request_access(self):
        with self.assertRaises(AccessError):
            self.env["onehr.portal.request"].with_user(self.plain_user).search([])

    def test_14_employee_cannot_create_request_for_another_employee(self):
        other_employee = self.env["hr.employee"].create(
            {"name": "Another Employee", "company_id": self.company.id}
        )
        request_type = self.make_type()
        with self.assertRaises(AccessError):
            self.env["onehr.portal.request"].with_user(self.employee_user).create(
                {
                    "employee_id": other_employee.id,
                    "type_id": request_type.id,
                    "subject": "Unauthorized",
                    "description": "Should fail.",
                }
            )

    def test_15_employee_cannot_write_lifecycle_directly(self):
        record = self.make_request()
        with self.assertRaises(AccessError):
            record.with_user(self.employee_user).write({"state": "done"})

    def test_16_manager_cannot_decide_other_managers_request(self):
        record = self.submit_request()
        with self.assertRaises(AccessError):
            record.with_user(self.other_manager_user).action_manager_approve()

    def test_17_manager_scope_contains_direct_report(self):
        record = self.submit_request()
        visible = self.env["onehr.portal.request"].with_user(self.manager_user).search(
            [("id", "=", record.id)]
        )
        self.assertEqual(visible, record)

    def test_18_employee_scope_does_not_expose_other_request(self):
        other_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Second Portal Employee",
                "login": f"second_{self._testMethodName}",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [(6, 0, [self.group_employee.id])],
            }
        )
        other_employee = self.env["hr.employee"].create(
            {
                "name": "Second Portal Employee",
                "company_id": self.company.id,
                "user_id": other_user.id,
                "parent_id": self.manager_employee.id,
            }
        )
        request_type = self.make_type()
        other_request = self.env["onehr.portal.request"].with_user(other_user).create(
            {
                "employee_id": other_employee.id,
                "type_id": request_type.id,
                "subject": "Other request",
                "description": "Private request.",
            }
        )
        visible = self.env["onehr.portal.request"].with_user(self.employee_user).search(
            [("id", "=", other_request.id)]
        )
        self.assertFalse(visible)

    def test_19_submitted_history_cannot_be_deleted(self):
        record = self.submit_request()
        with self.assertRaises(AccessError):
            record.with_user(self.admin_user).unlink()

    def test_20_only_admin_can_delete_unsubmitted_draft(self):
        record = self.make_request()
        with self.assertRaises(AccessError):
            record.with_user(self.hr_user).unlink()
        record.with_user(self.admin_user).unlink()
        self.assertFalse(record.exists())

    def test_21_request_type_history_blocks_delete(self):
        request_type = self.make_type()
        self.make_request(request_type=request_type)
        with self.assertRaises(AccessError):
            request_type.with_user(self.admin_user).unlink()

    def test_33_employee_group_uses_odoo19_portal_user_type(self):
        """Odoo 19 owns the Portal user-type group in base, not the portal addon."""
        self.assertTrue(self.employee_user.has_group("base.group_portal"))
        self.assertFalse(self.employee_user.has_group("base.group_user"))

    def test_34_bulk_action_uses_odoo19_group_ids_field(self):
        """The bound window action retains manager/HR visibility through group_ids."""
        action = self.env.ref(
            "onehr_portal_self_service.action_onehr_portal_bulk_approval_wizard"
        )
        self.assertIn(self.group_manager, action.group_ids)
        self.assertIn(self.group_hr, action.group_ids)
        self.assertNotIn(self.group_employee, action.group_ids)

