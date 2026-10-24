
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRCoreHRCommon


@tagged("post_install", "-at_install", "onehr_corehr")
class TestProfileHistory(OneHRCoreHRCommon):
    def test_05_dependent_effective_history_and_delete_protection(self):
        dependent = self.env["onehr.employee.dependent"].with_user(self.officer).create(
            {
                "employee_id": self.employee.id,
                "name": "Dependent One",
                "relationship": "child",
                "birth_date": fields.Date.today() - timedelta(days=3650),
            }
        )
        self.assertTrue(dependent.active)
        dependent.with_user(self.officer).action_expire()
        self.assertFalse(dependent.active)
        self.assertTrue(dependent.valid_to)
        with self.assertRaises((AccessError, ValidationError)):
            dependent.with_user(self.manager).unlink()

    def test_06_emergency_contact_has_single_effective_primary(self):
        first = self.env["onehr.employee.emergency.contact"].with_user(self.officer).create(
            {
                "employee_id": self.employee.id,
                "name": "Primary Contact",
                "relationship": "Spouse",
                "phone": "+621111",
            }
        )
        second = self.env["onehr.employee.emergency.contact"].with_user(self.officer).create(
            {
                "employee_id": self.employee.id,
                "name": "Second Contact",
                "relationship": "Sibling",
                "phone": "+622222",
            }
        )
        first.with_user(self.officer).action_set_primary()
        second.with_user(self.officer).action_set_primary()
        first.invalidate_recordset(["is_primary"])
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_07_identifier_masking_verification_and_history(self):
        identifier = self.env["onehr.employee.identifier"].with_user(self.steward).create(
            {
                "employee_id": self.employee.id,
                "identifier_type": "tax",
                "identifier_value": "1234567890123456",
                "issuer": "Tax Authority",
            }
        )
        self.assertNotEqual(identifier.masked_value, identifier.identifier_value)
        self.assertTrue(identifier.masked_value.endswith("3456"))
        self.assertTrue(identifier.value_fingerprint)

        # Company-keyed settings contract must match the model reader.
        self.env["ir.config_parameter"].sudo().set_param(
            f"onehr_corehr.{self.company.id}.identifier_mask_visible_chars",
            "2",
        )
        identifier.invalidate_recordset(["masked_value"])
        self.assertTrue(identifier.masked_value.endswith("56"))

        identifier.with_user(self.steward).action_verify()
        self.assertTrue(identifier.verified)
        self.assertEqual(identifier.verified_by_id, self.steward)

        with self.assertRaises((AccessError, ValidationError)):
            identifier.with_user(self.steward).unlink()

    def test_08_identifier_uniqueness_by_type_and_company(self):
        values = {
            "employee_id": self.employee.id,
            "identifier_type": "employment",
            "identifier_value": "UNIQUE-EMP-ID-001",
        }
        self.env["onehr.employee.identifier"].with_user(self.steward).create(values)
        with self.assertRaises(ValidationError):
            self.env["onehr.employee.identifier"].with_user(self.steward).create(values)

    def test_09_education_completion_and_date_integrity(self):
        education = self.env["onehr.employee.education"].with_user(self.officer).create(
            {
                "employee_id": self.employee.id,
                "institution_name": "Enterprise University",
                "qualification_level": "bachelor",
                "qualification_name": "Bachelor of Computing",
                "study_start_date": fields.Date.today() - timedelta(days=1500),
                "study_end_date": fields.Date.today() - timedelta(days=100),
            }
        )
        education.with_user(self.officer).action_mark_completed()
        self.assertTrue(education.completed)
        self.assertTrue(education.award_date)

        with self.assertRaises(ValidationError):
            self.env["onehr.employee.education"].with_user(self.officer).create(
                {
                    "employee_id": self.employee.id,
                    "institution_name": "Bad Dates",
                    "qualification_level": "certificate",
                    "qualification_name": "Invalid",
                    "study_start_date": fields.Date.today(),
                    "study_end_date": fields.Date.today() - timedelta(days=1),
                }
            )

    def test_10_prior_employment_is_external_history_not_assignment(self):
        history = self.env["onehr.employee.employment.history"].with_user(self.officer).create(
            {
                "employee_id": self.employee.id,
                "employer_name": "Previous Employer",
                "job_title": "Engineer",
                "valid_from": fields.Date.today() - timedelta(days=1000),
                "valid_to": fields.Date.today() - timedelta(days=100),
            }
        )
        history.with_user(self.officer).action_verify()
        self.assertTrue(history.verified)

        with self.assertRaises(ValidationError):
            self.env["onehr.employee.employment.history"].with_user(self.officer).create(
                {
                    "employee_id": self.employee.id,
                    "employer_name": "Future Employer",
                    "job_title": "Future Role",
                    "valid_from": fields.Date.today() + timedelta(days=1),
                }
            )
