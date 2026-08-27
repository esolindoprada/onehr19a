from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRPayrollL10nIdCommon


@tagged("post_install", "-at_install", "onehr_payroll_l10n_id")
class TestIndonesiaPayrollLocalizationSecurity(OneHRPayrollL10nIdCommon):
    def test_34_plain_internal_user_has_no_localization_acl(self):
        parameter = self.make_parameter()
        with self.assertRaises(AccessError):
            parameter.with_user(self.plain_user).read(["name"])

    def test_35_officer_has_read_only_parameter_access(self):
        parameter = self.make_parameter()
        self.assertEqual(
            parameter.with_user(self.officer).read(["code"])[0]["code"],
            parameter.code,
        )
        with self.assertRaises(AccessError):
            parameter.with_user(self.officer).write({"regulatory_notes": "No"})

    def test_36_company_record_rule_isolates_officer(self):
        main = self.make_parameter(code="MAIN-SCOPE")
        other = self.env["onehr.payroll.l10n.param"].with_user(self.manager).create(
            {
                "name": "Other Company Parameters",
                "code": "OTHER-SCOPE",
                "company_id": self.other_company.id,
                "valid_from": fields.Date.today(),
            }
        )
        visible = self.env["onehr.payroll.l10n.param"].with_user(self.officer).search(
            [("id", "in", [main.id, other.id])]
        )
        self.assertIn(main, visible)
        self.assertNotIn(other, visible)
