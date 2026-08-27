import base64
import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRPayrollL10nIdCommon


@tagged("post_install", "-at_install", "onehr_payroll_l10n_id")
class TestIndonesiaPayrollParameterGovernance(OneHRPayrollL10nIdCommon):
    def test_01_manager_can_create_parameter(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.company_id, self.company)
        self.assertEqual(parameter.code, "ID-PAYROLL")
        self.assertFalse(parameter.regulatory_reviewed_on)

    def test_02_officer_cannot_create_parameter(self):
        with self.assertRaises(AccessError):
            self.env["onehr.payroll.l10n.param"].with_user(self.officer).create(
                {
                    "name": "Unauthorized",
                    "code": "NOPE",
                    "company_id": self.company.id,
                    "valid_from": fields.Date.today(),
                }
            )

    def test_03_invalid_effective_period_is_rejected(self):
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.make_parameter(
                code="BAD-DATE",
                valid_from=today,
                valid_to=today - timedelta(days=1),
            )

    def test_04_overlapping_active_versions_are_rejected(self):
        today = fields.Date.today()
        self.make_parameter(code="OVERLAP", valid_from=today)
        with self.assertRaises(ValidationError):
            self.make_parameter(code="OVERLAP-2", valid_from=today)

    def test_05_regulatory_review_action_records_evidence(self):
        parameter = self.make_parameter()
        parameter.with_user(self.manager).action_mark_regulatory_reviewed()
        self.assertTrue(parameter.regulatory_reviewed_on)
        self.assertEqual(parameter.regulatory_reviewed_by_id, self.manager)
        self.assertTrue(parameter.next_regulatory_review_date)

    def test_06_parameter_edit_invalidates_prior_review(self):
        parameter = self.review_parameter()
        parameter.with_user(self.manager).write({"regulatory_notes": "Reviewed note changed"})
        self.assertFalse(parameter.regulatory_reviewed_on)
        self.assertFalse(parameter.regulatory_reviewed_by_id)

    def test_07_direct_review_evidence_write_is_blocked(self):
        parameter = self.make_parameter()
        with self.assertRaises(AccessError):
            parameter.with_user(self.manager).write(
                {"regulatory_reviewed_on": fields.Date.today()}
            )

    def test_08_create_new_version_closes_predecessor(self):
        parameter = self.review_parameter()
        new_date = parameter.valid_from + timedelta(days=31)
        parameter.with_user(self.manager).next_version_effective_from = new_date
        action = parameter.with_user(self.manager).action_create_new_version()
        successor = self.env["onehr.payroll.l10n.param"].browse(action["res_id"])
        self.assertEqual(parameter.valid_to, new_date - timedelta(days=1))
        self.assertEqual(successor.valid_from, new_date)
        self.assertEqual(successor.predecessor_id, parameter)
        self.assertEqual(successor.revision, 2)
        self.assertFalse(successor.regulatory_reviewed_on)

    def test_09_governed_correction_supersedes_prior_version(self):
        parameter = self.review_parameter()
        parameter.with_user(self.manager).correction_reason = "Correct statutory reference"
        action = parameter.with_user(self.manager).action_create_correction()
        correction = self.env["onehr.payroll.l10n.param"].browse(action["res_id"])
        self.assertFalse(parameter.active)
        self.assertTrue(correction.active)
        self.assertEqual(correction.valid_from, parameter.valid_from)
        self.assertEqual(correction.predecessor_id, parameter)
        self.assertFalse(correction.regulatory_reviewed_on)

    def test_10_effective_or_historical_parameter_cannot_be_deleted(self):
        parameter = self.make_parameter()
        with self.assertRaises(AccessError):
            parameter.with_user(self.manager).unlink()

    def test_11_unused_future_parameter_can_be_deleted(self):
        future = fields.Date.today() + timedelta(days=90)
        parameter = self.make_parameter(code="FUTURE-DELETE", valid_from=future)
        parameter.with_user(self.manager).unlink()
        self.assertFalse(parameter.exists())

    def test_12_json_export_is_generated_inside_same_model(self):
        parameter = self.review_parameter()
        action = parameter.with_user(self.manager).action_download_json()
        self.assertEqual(action["type"], "ir.actions.act_url")
        document = json.loads(base64.b64decode(parameter.download_file).decode("utf-8"))
        self.assertEqual(document["schema"], "onehr.payroll.l10n.param-import/v1")
        self.assertIn("ter_a_json", document["parameters"])

    def test_13_csv_export_is_generated_inside_same_model(self):
        parameter = self.review_parameter()
        action = parameter.with_user(self.manager).action_download_csv()
        self.assertEqual(action["type"], "ir.actions.act_url")
        content = base64.b64decode(parameter.download_file).decode("utf-8-sig")
        self.assertTrue(content.startswith("parameter,value"))
        self.assertIn("bpjs_jp_wage_ceiling", content)

    def test_14_json_import_creates_unreviewed_new_version(self):
        parameter = self.review_parameter()
        parameter.with_user(self.manager).action_download_json()
        effective_from = parameter.valid_from + timedelta(days=60)
        parameter.with_user(self.manager).write(
            {
                "import_file": parameter.download_file,
                "import_filename": "parameters.json",
                "import_effective_from": effective_from,
            }
        )
        action = parameter.with_user(self.manager).action_import_as_new_version()
        imported = self.env["onehr.payroll.l10n.param"].browse(action["res_id"])
        self.assertEqual(imported.valid_from, effective_from)
        self.assertEqual(imported.predecessor_id, parameter)
        self.assertFalse(imported.regulatory_reviewed_on)

    def test_15_review_expiry_blocks_future_payroll_resolution(self):
        parameter = self.review_parameter()
        future_date = parameter.next_regulatory_review_date + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.env["onehr.payroll.l10n.param"].with_user(
                self.officer
            ).onehr_find_effective_parameter(
                self.company,
                future_date,
                require_review=True,
            )
