from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRPayrollBridgeCommon


@tagged("post_install", "-at_install", "onehr_payroll_bridge")
class TestPayrollBridgeSecurity(OneHRPayrollBridgeCommon):
    def test_33_plain_internal_user_has_no_payroll_bridge_acl(self):
        config = self.make_config()
        with self.assertRaises(AccessError):
            config.with_user(self.plain_user).read(["name"])

    def test_34_officer_is_restricted_to_allowed_company_records(self):
        main = self.make_config(code="PAY-MAIN-SCOPE")
        other = self.env["onehr.payroll.bridge.config"].with_user(self.manager).create(
            {
                "name": "Other Company Payroll",
                "code": "PAY-OTHER",
                "company_id": self.other_company.id,
                "currency_id": self.other_company.currency_id.id,
                "external_system_code": "OTHER",
                "include_attendance": False,
                "include_overtime": False,
                "include_timeoff": False,
                "include_assignment_costing": False,
            }
        )
        visible = self.env["onehr.payroll.bridge.config"].with_user(self.officer).search(
            [("id", "in", [main.id, other.id])]
        )
        self.assertIn(main, visible)
        self.assertNotIn(other, visible)
