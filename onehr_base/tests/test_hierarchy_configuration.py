from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import OneHRCommon


@tagged("post_install", "-at_install", "onehr_base")
class TestHierarchyConfiguration(OneHRCommon):
    def setUp(self):
        super().setUp()
        self.hierarchy = self.env["onehr.position.hierarchy"].create(
            {
                "code": "REPORT",
                "name": "Reporting",
                "company_id": self.company.id,
            }
        )

    def test_version_overlap_and_status_actions(self):
        today = fields.Date.today()
        first = self.env["onehr.position.hierarchy.version"].create(
            {
                "hierarchy_id": self.hierarchy.id,
                "version": 1,
                "valid_from": today,
                "valid_to": today + timedelta(days=10),
                "state": "active",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.position.hierarchy.version"].create(
                {
                    "hierarchy_id": self.hierarchy.id,
                    "version": 2,
                    "valid_from": today + timedelta(days=5),
                    "state": "active",
                }
            )
        first.action_retire()
        self.assertEqual(first.state, "retired")

    def test_node_duplicate_cycle_and_open_position(self):
        version = self.env["onehr.position.hierarchy.version"].create(
            {"hierarchy_id": self.hierarchy.id, "version": 1}
        )
        node = self.env["onehr.position.hierarchy.node"].create(
            {"version_id": version.id, "position_id": self.position.id}
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.position.hierarchy.node"].create(
                {"version_id": version.id, "position_id": self.position.id}
            )
        position2 = self.position.copy({"code": "POS-2", "name": "Second Seat"})
        child = self.env["onehr.position.hierarchy.node"].create(
            {
                "version_id": version.id,
                "position_id": position2.id,
                "parent_id": node.id,
            }
        )
        with self.assertRaises(ValidationError):
            node.parent_id = child
        action = node.action_open_position()
        self.assertEqual(action["res_model"], "onehr.position")
        self.assertEqual(action["res_id"], self.position.id)

    def test_sequence_delegation(self):
        sequence = self.env["ir.sequence"].create(
            {
                "name": "OneHR Test",
                "code": "onehr.test",
                "prefix": "T-",
                "padding": 3,
            }
        )
        rule = self.env["onehr.sequence.rule"].create(
            {
                "code": "TEST",
                "name": "Test",
                "purpose": "Test delegation",
                "sequence_id": sequence.id,
            }
        )
        self.assertEqual(rule.next_value(), "T-001")
        self.assertEqual(rule.next_value(), "T-002")

    def test_structured_eligibility(self):
        profile = self.env["onehr.eligibility.profile"].create(
            {
                "code": "ELIG",
                "name": "Eligible",
                "company_id": self.company.id,
                "department_ids": [(6, 0, self.department.ids)],
                "job_ids": [(6, 0, self.job.ids)],
                "classification_keys": "PERMANENT,CONTRACT",
                "min_service_months": 6,
                "max_service_months": 60,
            }
        )
        values = {
            "company_id": self.company.id,
            "department_id": self.department.id,
            "job_id": self.job.id,
            "classification_key": "PERMANENT",
            "service_months": 12,
        }
        self.assertTrue(profile.matches(values))
        self.assertFalse(profile.matches({**values, "service_months": 5}))
        self.assertFalse(
            profile.matches({**values, "classification_key": "INTERN"})
        )
