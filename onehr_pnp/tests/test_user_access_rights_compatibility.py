
from xml.etree import ElementTree as ET

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "onehr_pnp")
class TestPnPUserAccessRightsCompatibility(TransactionCase):
    """Regression for Odoo 19 native Settings > Users Access Rights rendering."""

    def _onehr_privilege_categories(self):
        model_data = self.env["ir.model.data"].search([
            ("model", "=", "ir.module.category"),
        ])
        onehr_category_ids = {
            row.res_id
            for row in model_data
            if row.module.startswith("onehr_") and row.res_id
        }
        if not onehr_category_ids:
            return self.env["ir.module.category"]
        privilege_category_ids = set(
            self.env["res.groups.privilege"].search([
                ("category_id", "in", list(onehr_category_ids)),
            ]).mapped("category_id").ids
        )
        return self.env["ir.module.category"].browse(sorted(privilege_category_ids)).exists()

    def test_01_owned_category_is_render_safe_and_privilege_label_is_preserved(self):
        category = self.env.ref("onehr_pnp.module_category_onehr_pnp")
        privilege = self.env.ref("onehr_pnp.privilege_onehr_pnp")
        self.assertEqual(category.name, 'OneHR Policies and Procedures')
        self.assertEqual(privilege.name, 'OneHR Policies & Procedures')
        self.assertEqual(privilege.category_id, category)

    def test_02_all_installed_onehr_privilege_categories_parse_in_dynamic_xml(self):
        failures = []
        for category in self._onehr_privilege_categories():
            # Mirrors the Odoo 19 web-client failure class: the category label is
            # interpolated into a generated XML attribute before parseXML().
            dynamic_arch = f'<t><group string="{category.name}"/></t>'
            try:
                ET.fromstring(dynamic_arch)
            except ET.ParseError as exc:
                failures.append(f"{category.display_name}: {exc}")
        self.assertFalse(
            failures,
            "OneHR privilege categories must remain safe for Odoo 19 dynamic "
            "Access Rights XML: " + "; ".join(failures),
        )

