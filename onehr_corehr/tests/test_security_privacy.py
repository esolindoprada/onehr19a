from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRCoreHRCommon


@tagged("post_install", "-at_install", "onehr_corehr")
class TestSecurityPrivacy(OneHRCoreHRCommon):
    def test_11_company_record_rules_isolate_profile_history(self):
        other_employee = self.env["hr.employee"].create(
            {"name": "Other Company Employee", "company_id": self.other_company.id}
        )
        other_dep = self.env["onehr.employee.dependent"].create(
            {
                "employee_id": other_employee.id,
                "name": "Other Company Dependent",
                "relationship": "other",
            }
        )
        visible = self.env["onehr.employee.dependent"].with_user(self.officer).search([])
        self.assertNotIn(other_dep, visible)

    def test_12_corehr_manager_does_not_inherit_occupational_health_access(self):
        self.assertFalse(
            self.manager.has_group("onehr_corehr.group_onehr_occupational_health_officer")
        )
        self.assertFalse(
            self.manager.has_group("onehr_security.group_onehr_restricted_data_reader")
        )

        with self.assertRaises(AccessError):
            self.env["onehr.work.incident"].with_user(self.manager).check_access("read")

    def test_13_security_admin_does_not_imply_occupational_health(self):
        security_admin_group = self.env.ref("onehr_security.group_onehr_security_admin")
        security_admin = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "OneHR Security Admin Without OH",
                "login": "onehr_corehr_security_admin_without_oh",
                "company_id": self.company.id,
                "company_ids": [Command.set(self.company.ids)],
                "group_ids": [Command.set(security_admin_group.ids)],
            }
        )
        self.assertFalse(
            security_admin.has_group("onehr_corehr.group_onehr_occupational_health_officer")
        )
        with self.assertRaises(AccessError):
            self.env["onehr.medical.assessment"].with_user(security_admin).check_access("read")
