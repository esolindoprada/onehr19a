from datetime import datetime

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRAttendanceCommon


@tagged("post_install", "-at_install", "onehr_attendance")
class TestImportReconciliation(OneHRAttendanceCommon):
    def test_19_import_requires_nonblank_idempotency_key(self):
        csv_text = "employee,check_in,check_out\nATT-0001,2026-08-18 08:00:00,2026-08-18 17:00:00\n"
        with self.assertRaises(ValidationError):
            self.make_import_batch(csv_text, key="   ")

    def test_20_csv_parse_and_validate_produces_canonical_candidate_payload(self):
        csv_text = "employee,check_in,check_out,external_reference\nATT-0001,2026-08-18 08:00:00,2026-08-18 17:00:00,FP-001\n"
        batch = self.make_import_batch(csv_text, key="BATCH-VALID")
        batch.action_parse()
        self.assertEqual(batch.state, "parsed")
        self.assertEqual(batch.raw_row_count, 1)
        batch.action_validate()
        self.assertEqual(batch.state, "validated")
        self.assertEqual(batch.valid_row_count, 1)
        self.assertEqual(batch.validation_payload[0]["employee_id"], self.employee.id)
        self.assertEqual(batch.validation_payload[0]["external_reference"], "FP-001")

    def test_21_csv_local_timezone_is_converted_to_naive_utc(self):
        csv_text = "employee,check_in,check_out\nATT-0001,2026-08-18 08:00:00,2026-08-18 17:00:00\n"
        batch = self.make_import_batch(csv_text, key="BATCH-TZ", timezone="Asia/Jakarta")
        parsed = batch._local_csv_datetime_to_utc("2026-08-18 08:00:00")
        self.assertEqual(parsed, datetime(2026, 8, 18, 1, 0, 0))

    def test_22_import_source_facts_freeze_after_parse(self):
        csv_text = "employee,check_in\nATT-0001,2026-08-18 08:00:00\n"
        batch = self.make_import_batch(csv_text, key="BATCH-FREEZE")
        batch.action_parse()
        with self.assertRaises(AccessError):
            batch.write({"source_system": "CHANGED"})

    def test_23_reconciliation_validation_requires_retry_safe_external_reference(self):
        reconciliation = self.env["onehr.attendance.reconciliation"].with_user(self.officer).create({
            "company_id": self.company.id,
            "source_type": "device",
            "source_system": "DEVICE-X",
            "candidate_payload": [{
                "employee_id": self.employee.id,
                "check_in": "2026-08-18 08:00:00",
                "check_out": "2026-08-18 17:00:00",
            }],
        })
        with self.assertRaises(ValidationError):
            reconciliation.with_user(self.officer).action_validate_candidates()

    def test_24_reconciliation_post_is_idempotent_through_canonical_ingestion(self):
        candidate = {
            "employee_id": self.employee.id,
            "check_in": "2026-08-20 08:00:00",
            "check_out": "2026-08-20 17:00:00",
            "source_channel": "fingerprint",
            "source_system": "FP-POST",
            "external_reference": "FP-POST-001",
        }
        reconciliation = self.env["onehr.attendance.reconciliation"].with_user(self.officer).create({
            "company_id": self.company.id,
            "source_type": "device",
            "source_system": "FP-POST",
            "candidate_payload": [candidate],
        })
        reconciliation.with_user(self.officer).action_submit_review()
        reconciliation.with_user(self.manager).action_approve()
        reconciliation.with_user(self.manager).action_post()
        self.assertEqual(reconciliation.state, "posted")
        self.assertEqual(reconciliation.attendance_count, 1)
        retried = self.env["hr.attendance"].with_user(self.officer).onehr_ingest_interval(candidate)
        self.assertEqual(retried, reconciliation.attendance_ids)
