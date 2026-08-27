from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import OneHRCommon


@tagged("post_install", "-at_install", "onehr_base")
class TestEffectiveOrganization(OneHRCommon):
    def test_invalid_interval_and_as_of_helper(self):
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.env["onehr.job.family"].create(
                {
                    "code": "BAD",
                    "name": "Bad",
                    "valid_from": today,
                    "valid_to": today - timedelta(days=1),
                }
            )
        family = self.env["onehr.job.family"].create(
            {
                "code": "FAM",
                "name": "Family",
                "valid_from": today,
                "valid_to": today + timedelta(days=2),
            }
        )
        self.assertTrue(family.is_effective_on(today))
        self.assertFalse(family.is_effective_on(today + timedelta(days=3)))
        self.assertIn(
            family,
            self.env["onehr.job.family"].search(family.effective_domain(today)),
        )

    def test_native_first_extensions_and_native_interval_constraints(self):
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        self.assertIn("onehr_code", self.env["hr.department"]._fields)
        self.assertIn("onehr_job_family_id", self.env["hr.job"]._fields)
        self.assertIn("onehr_site_code", self.env["hr.work.location"]._fields)
        self.assertNotIn("onehr.org.unit", self.env)
        self.assertNotIn("onehr.job", self.env)
        self.assertNotIn("onehr.location", self.env)
        self.assertNotIn("onehr.employee", self.env)

        invalid_native_rows = (
            (
                "hr.department",
                {
                    "name": "Bad Department Interval",
                    "onehr_valid_from": today,
                    "onehr_valid_to": yesterday,
                },
            ),
            (
                "hr.job",
                {
                    "name": "Bad Job Interval",
                    "onehr_valid_from": today,
                    "onehr_valid_to": yesterday,
                },
            ),
            (
                "hr.work.location",
                {
                    "name": "Bad Location Interval",
                    "onehr_valid_from": today,
                    "onehr_valid_to": yesterday,
                },
            ),
        )
        for model_name, values in invalid_native_rows:
            with self.assertRaises(ValidationError):
                self.env[model_name].create(values)

        self.assertTrue(self.job.onehr_is_effective_on(today))
        self.assertEqual(self.job.onehr_position_count, 1)
        self.assertEqual(self.department.onehr_position_count, 1)
        self.assertEqual(self.location.onehr_position_count, 1)

    def test_company_global_code_constraints(self):
        self.env["onehr.job.family"].create({"code": "GLOBAL", "name": "Global"})
        with self.assertRaises(ValidationError):
            self.env["onehr.job.family"].create(
                {"code": "global", "name": "Duplicate"}
            )
        self.env["onehr.grade"].create(
            {"code": "LOCAL", "name": "Local", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.grade"].create(
                {
                    "code": "local",
                    "name": "Duplicate",
                    "company_id": self.company.id,
                }
            )
        self.env["onehr.grade"].create(
            {
                "code": "LOCAL",
                "name": "Other",
                "company_id": self.other_company.id,
            }
        )

    def test_position_company_validity_capacity_and_action(self):
        other_department = self.env["hr.department"].create(
            {"name": "Other", "company_id": self.other_company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.position"].create(
                {
                    "code": "BAD-COMPANY",
                    "name": "Bad",
                    "company_id": self.company.id,
                    "department_id": other_department.id,
                    "job_id": self.job.id,
                }
            )

        tomorrow = fields.Date.today() + timedelta(days=1)
        future_grade = self.env["onehr.grade"].create(
            {
                "code": "FUTURE",
                "name": "Future",
                "company_id": self.company.id,
                "valid_from": tomorrow,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.position"].create(
                {
                    "code": "BAD-DATE",
                    "name": "Bad Date",
                    "company_id": self.company.id,
                    "department_id": self.department.id,
                    "job_id": self.job.id,
                    "grade_id": future_grade.id,
                    "valid_from": fields.Date.today(),
                }
            )
        with self.assertRaises(ValidationError):
            self.position.copy({"code": "NEGATIVE", "authorized_fte": -1})

        action = self.position.action_open_hierarchy_nodes()
        self.assertEqual(action["res_model"], "onehr.position.hierarchy.node")
