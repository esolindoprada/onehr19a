import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRPayrollL10nIdCommon


@tagged("post_install", "-at_install", "onehr_payroll_l10n_id")
class TestIndonesiaPayrollBridgeIntegration(OneHRPayrollL10nIdCommon):
    def test_28_export_generation_freezes_reviewed_localization_snapshot(self):
        parameter = self.review_parameter()
        export = self.make_export()
        export.with_user(self.officer).action_generate_export()
        self.assertEqual(export.onehr_l10n_param_id, parameter)
        self.assertEqual(len(export.onehr_l10n_sha256), 64)
        snapshot = json.loads(export.onehr_l10n_snapshot_json)
        self.assertEqual(snapshot["parameter_sha256"], export.onehr_l10n_sha256)

    def test_29_employee_source_row_contains_compact_localization_reference(self):
        parameter = self.review_parameter()
        export = self.make_export()
        export.with_user(self.officer).action_generate_export()
        rows = json.loads(export.source_rows_json)
        localization = rows[0]["variables_json"]["indonesia_localization"]
        self.assertEqual(localization["parameter_id"], parameter.id)
        self.assertEqual(localization["sha256"], export.onehr_l10n_sha256)

    def test_30_reset_generation_clears_localization_evidence(self):
        self.review_parameter()
        export = self.make_export()
        export.with_user(self.officer).action_generate_export()
        export.with_user(self.officer).action_reset_generation()
        self.assertFalse(export.onehr_l10n_param_id)
        self.assertFalse(export.onehr_l10n_snapshot_json)
        self.assertFalse(export.onehr_l10n_sha256)

    def test_31_adapter_payload_includes_full_indonesia_localization(self):
        parameter = self.review_parameter()
        export = self.make_export()
        export.with_user(self.officer).action_generate_export()
        payload = export.with_user(self.officer).onehr_payroll_export_payload()
        self.assertEqual(
            payload["indonesia_localization"]["parameter_sha256"],
            parameter.parameter_sha256,
        )

    def test_32_export_without_effective_parameter_is_rejected(self):
        export = self.make_export()
        with self.assertRaises(ValidationError):
            export.with_user(self.officer).action_generate_export()

    def test_33_used_parameter_is_immutable(self):
        parameter = self.review_parameter()
        export = self.make_export()
        export.with_user(self.officer).action_generate_export()
        with self.assertRaises(AccessError):
            parameter.with_user(self.manager).write(
                {"bpjs_jp_wage_ceiling": parameter.bpjs_jp_wage_ceiling + 100}
            )
