from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRPayrollBridgeCommon


@tagged("post_install", "-at_install", "onehr_payroll_bridge")
class TestPayrollImportReconciliation(OneHRPayrollBridgeCommon):
    def test_18_import_snapshots_employee_context(self):
        result = self.make_import()
        self.assertEqual(result.employee_number_snapshot, self.employee.onehr_employee_number)
        self.assertEqual(result.employee_name_snapshot, self.employee.name)
        self.assertEqual(result.department_snapshot, self.department.name)
        self.assertTrue(result.is_current_revision)

    def test_19_import_evidence_requires_posted_export(self):
        export = self.generate_export(employees=self.employee)
        with self.assertRaises(ValidationError):
            self.make_import(export=export)

    def test_20_valid_import_can_be_validated(self):
        export = self.post_export(employees=self.employee)
        result = self.make_import(export=export)
        result.with_user(self.officer).action_validate()
        self.assertEqual(result.state, "validated")
        self.assertFalse(result.validation_message)

    def test_21_net_equation_tolerance_can_reject_vendor_result(self):
        config = self.make_config(
            code="PAY-NET-CHECK",
            validate_net_equation=True,
            net_reconciliation_tolerance=0.01,
        )
        export = self.post_export(
            export=self.make_export(config=config, employees=self.employee)
        )
        result = self.make_import(
            export=export,
            gross_amount=1000.0,
            deduction_amount=100.0,
            net_amount=850.0,
        )
        result.with_user(self.officer).action_validate()
        self.assertEqual(result.state, "error")
        self.assertTrue(result.validation_message)

    def test_22_direct_revision_lineage_create_is_blocked(self):
        export = self.post_export(employees=self.employee)
        with self.assertRaises(AccessError):
            self.env["onehr.payroll.import"].with_user(self.manager).create(
                {
                    "export_id": export.id,
                    "employee_id": self.employee.id,
                    "external_reference": "ILLEGAL-REVISION",
                    "revision": 2,
                    "currency_id": export.currency_id.id,
                }
            )

    def test_23_manager_correction_supersedes_prior_revision(self):
        export = self.post_export(employees=self.employee)
        result = self.make_import(export=export)
        result.with_user(self.officer).action_validate()
        action = result.with_user(self.manager).action_create_correction()
        correction = self.env["onehr.payroll.import"].browse(action["res_id"])
        self.assertEqual(result.state, "superseded")
        self.assertEqual(correction.revision, 2)
        self.assertEqual(correction.supersedes_id, result)
        self.assertTrue(correction.is_current_revision)

    def test_24_reconcile_requires_validated_results(self):
        export = self.post_export(employees=self.employee)
        self.make_import(export=export)
        with self.assertRaises(UserError):
            export.with_user(self.manager).action_reconcile()

    def test_25_full_reconciliation_rejects_missing_employee_result(self):
        export = self.post_export(employees=self.employee | self.employee_2)
        result = self.make_import(export=export, employee=self.employee)
        result.with_user(self.officer).action_validate()
        with self.assertRaises(UserError):
            export.with_user(self.manager).action_reconcile()

    def test_26_reconciliation_closes_batch_and_builds_costing_payload(self):
        export = self.post_export(employees=self.employee | self.employee_2)
        first = self.make_import(export=export, employee=self.employee)
        second = self.make_import(
            export=export,
            employee=self.employee_2,
            external_reference="EXT-PAY-EMP-002",
            gross_amount=2000.0,
            deduction_amount=200.0,
            net_amount=1800.0,
            employer_cost=2200.0,
        )
        first.with_user(self.officer).action_validate()
        second.with_user(self.officer).action_validate()
        export.with_user(self.manager).action_reconcile()
        self.assertEqual(export.state, "reconciled")
        self.assertEqual(first.state, "reconciled")
        self.assertEqual(second.state, "reconciled")
        self.assertIn(self.department.name, export.costing_payload_json)
        self.assertEqual(export.reconciliation_accuracy, 100.0)

    def test_27_api_ingest_service_is_idempotent_for_current_draft(self):
        export = self.post_export(employees=self.employee)
        payload = {
            "export_id": export.id,
            "employee_number": self.employee.onehr_employee_number,
            "external_reference": "API-001",
            "gross_amount": 1000,
            "deduction_amount": 100,
            "net_amount": 900,
            "employer_cost": 1100,
        }
        first = self.env["onehr.payroll.import"].with_user(self.officer).onehr_ingest_payroll_result(payload)
        payload["net_amount"] = 901
        second = self.env["onehr.payroll.import"].with_user(self.officer).onehr_ingest_payroll_result(payload)
        self.assertEqual(first, second)
        self.assertEqual(second.net_amount, 901)

    def test_28_employee_safe_payload_contains_no_raw_vendor_json(self):
        result = self.make_import(raw_payload_json='{"private_vendor_debug":"x"}')
        payload = result.onehr_portal_payslip_payload()
        self.assertEqual(payload["employee_id"], self.employee.id)
        self.assertNotIn("raw_payload_json", payload)
        self.assertNotIn("employer_cost", payload)

    def test_29_vendor_csv_import_creates_result_and_hashes_exact_file(self):
        export = self.post_export(employees=self.employee)
        mapping = export.config_id._parse_mapping("import_field_mapping")
        vendor_row = {
            mapping["employee_number"]: self.employee.onehr_employee_number,
            mapping["external_reference"]: "CSV-001",
            mapping["payslip_number"]: "PS-CSV-001",
            mapping["payment_date"]: "2026-08-20",
            mapping["gross_amount"]: "1000",
            mapping["deduction_amount"]: "100",
            mapping["net_amount"]: "900",
            mapping["employer_cost"]: "1100",
            mapping["currency_code"]: export.currency_id.name,
        }
        payload = self.vendor_csv_binary([vendor_row], export.config_id)
        export.with_user(self.officer).write(
            {
                "vendor_import_file": payload,
                "vendor_import_filename": "vendor_result.csv",
            }
        )
        export.with_user(self.officer).action_import_vendor_results()
        result = self.env["onehr.payroll.import"].search(
            [("export_id", "=", export.id), ("external_reference", "=", "CSV-001")],
            limit=1,
        )
        self.assertTrue(result)
        self.assertEqual(result.employee_id, self.employee)
        self.assertEqual(result.net_amount, 900.0)
        self.assertEqual(len(export.vendor_import_sha256), 64)
        self.assertTrue(export.vendor_imported_at)

    def test_30_vendor_csv_rejects_unknown_currency(self):
        export = self.post_export(employees=self.employee)
        mapping = export.config_id._parse_mapping("import_field_mapping")
        vendor_row = {
            mapping["employee_number"]: self.employee.onehr_employee_number,
            mapping["external_reference"]: "CSV-BAD-CURRENCY",
            mapping["net_amount"]: "900",
            mapping["currency_code"]: "ZZZ",
        }
        payload = self.vendor_csv_binary([vendor_row], export.config_id)
        export.with_user(self.officer).write(
            {
                "vendor_import_file": payload,
                "vendor_import_filename": "vendor_bad_currency.csv",
            }
        )
        with self.assertRaises(ValidationError):
            export.with_user(self.officer).action_import_vendor_results()

    def test_31_posted_export_uses_frozen_reconciliation_policy(self):
        config = self.make_config(
            code="PAY-FROZEN-POLICY",
            validate_net_equation=True,
            net_reconciliation_tolerance=0.01,
        )
        export = self.post_export(
            export=self.make_export(config=config, employees=self.employee)
        )
        config.with_user(self.manager).write(
            {
                "validate_net_equation": False,
                "net_reconciliation_tolerance": 9999.0,
            }
        )
        result = self.make_import(
            export=export,
            gross_amount=1000.0,
            deduction_amount=100.0,
            net_amount=850.0,
        )
        result.with_user(self.officer).action_validate()
        self.assertEqual(result.state, "error")

    def test_32_validated_vendor_file_cannot_be_silently_replaced(self):
        export = self.post_export(employees=self.employee)
        mapping = export.config_id._parse_mapping("import_field_mapping")
        first_row = {
            mapping["employee_number"]: self.employee.onehr_employee_number,
            mapping["external_reference"]: "CSV-FROZEN-001",
            mapping["net_amount"]: "900",
            mapping["currency_code"]: export.currency_id.name,
        }
        first_file = self.vendor_csv_binary([first_row], export.config_id)
        export.with_user(self.officer).write(
            {
                "vendor_import_file": first_file,
                "vendor_import_filename": "vendor_frozen.csv",
            }
        )
        export.with_user(self.officer).action_import_vendor_results()
        result = self.env["onehr.payroll.import"].search(
            [("export_id", "=", export.id), ("external_reference", "=", "CSV-FROZEN-001")],
            limit=1,
        )
        result.with_user(self.officer).action_validate()

        changed_row = dict(first_row)
        changed_row[mapping["net_amount"]] = "901"
        changed_file = self.vendor_csv_binary([changed_row], export.config_id)
        with self.assertRaises(AccessError):
            export.with_user(self.officer).write(
                {
                    "vendor_import_file": changed_file,
                    "vendor_import_filename": "vendor_changed.csv",
                }
            )
