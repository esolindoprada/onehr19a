
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRJobDescriptionCommon


@tagged("post_install", "-at_install", "onehr_job_description")
class TestJDMasterAndTemplate(OneHRJobDescriptionCommon):
    def test_01_exact_two_models_present(self):
        self.assertIn("onehr.jd", self.env)
        self.assertIn("onehr.jd.version", self.env)
        self.assertNotIn(
            "onehr_job_description.onehr_job_description",
            self.env,
        )

    def test_02_jd_reference_uses_sequence(self):
        jd = self.make_jd()
        self.assertNotEqual(jd.code, "New")
        self.assertTrue(jd.code.startswith("JD/"))

    def test_03_non_template_requires_position(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.jd"].with_user(self.editor).create(
                {
                    "name": "Invalid Positionless JD",
                    "company_id": self.company.id,
                }
            )

    def test_04_template_requires_job_family(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.jd"].with_user(self.editor).create(
                {
                    "name": "Invalid Template",
                    "company_id": self.company.id,
                    "is_template": True,
                }
            )

    def test_05_only_one_active_template_per_family(self):
        self.make_template()
        with self.assertRaises(ValidationError):
            self.make_template(name="Duplicate Active Template")

    def test_06_position_identity_maps_job_family(self):
        jd = self.make_jd()
        self.assertEqual(jd.job_family_id, self.job_family)
        self.assertEqual(jd.job_name, self.job.name)
        self.assertEqual(jd.department_name, self.department.name)

    def test_07_first_version_number_is_one(self):
        version = self.make_version()
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.state, "draft")

    def test_08_only_one_inflight_version_allowed(self):
        jd = self.make_jd()
        self.make_version(jd)
        with self.assertRaises(UserError):
            self.make_version(jd)

