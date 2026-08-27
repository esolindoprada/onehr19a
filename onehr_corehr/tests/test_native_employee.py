from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import OneHRCoreHRCommon


@tagged("post_install", "-at_install", "onehr_corehr")
class TestNativeEmployeeArchitecture(OneHRCoreHRCommon):
    def test_01_registry_and_native_employee_contract(self):
        for model_name in (
            "hr.employee",
            "hr.employee.public",
            "hr.version",
            "onehr.employee.dependent",
            "onehr.employee.emergency.contact",
            "onehr.employee.identifier",
            "onehr.employee.education",
            "onehr.employee.employment.history",
            "onehr.engagement.type",
            "onehr.work.incident",
            "onehr.medical.assessment",
            "onehr.disability.record",
            "res.config.settings",
        ):
            self.assertIn(model_name, self.env)

        self.assertNotIn("onehr.employee", self.env)
        self.assertIn("onehr_engagement_type_id", self.env["hr.version"]._fields)
        self.assertIn("onehr_primary_position_id", self.env["hr.version"]._fields)

    def test_02_public_employee_boundary_is_safe(self):
        public = self.env["hr.employee.public"].browse(self.employee.id)
        self.assertTrue(public.exists())
        self.assertEqual(public.onehr_employee_number, self.employee.onehr_employee_number)

        for restricted_field in (
            "onehr_identifier_ids",
            "onehr_work_incident_count",
            "onehr_medical_assessment_count",
            "onehr_disability_record_count",
            "onehr_profile_completeness",
            "onehr_accommodation_required",
        ):
            self.assertNotIn(restricted_field, self.env["hr.employee.public"]._fields)

    def test_03_employee_number_and_profile_completeness(self):
        self.assertTrue(self.employee.onehr_employee_number)
        self.assertGreaterEqual(self.employee.onehr_profile_completeness, 0)
        self.assertLessEqual(self.employee.onehr_profile_completeness, 100)
        self.assertIn(self.employee.onehr_profile_status, ("incomplete", "basic", "ready"))

        with self.assertRaises(ValidationError):
            self.env["hr.employee"].create(
                {
                    "name": "Duplicate Worker Number",
                    "company_id": self.company.id,
                    "onehr_employee_number": self.employee.onehr_employee_number,
                }
            )

    def test_04_versioned_engagement_maps_to_native_employee_type(self):
        engagement = self.env["onehr.engagement.type"].create(
            {
                "code": "PERM",
                "name": "Permanent Employee",
                "native_employee_type": "employee",
                "company_id": self.company.id,
            }
        )
        version = self.employee.version_id
        version.write(
            {
                "employee_type": "employee",
                "onehr_engagement_type_id": engagement.id,
            }
        )
        self.assertEqual(version.onehr_engagement_type_id, engagement)

        contractor = self.env["onehr.engagement.type"].create(
            {
                "code": "CONTRACT",
                "name": "Contractor",
                "native_employee_type": "contractor",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(ValidationError):
            version.write({"onehr_engagement_type_id": contractor.id})
