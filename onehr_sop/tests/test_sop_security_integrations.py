from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRSOPCommon


@tagged("post_install", "-at_install", "onehr_sop")
class TestSOPSecurityAndIntegrations(OneHRSOPCommon):
    def test_29_reader_sees_only_assigned_current_publication(self):
        version = self.publish_version(self.make_version())
        visible = self.env["onehr.sop.version"].with_user(
            self.reader
        ).search([("sop_id", "=", version.sop_id.id)])
        self.assertEqual(visible, version)

        own_ack = self.env["onehr.sop.ack"].with_user(
            self.reader
        ).search([("version_id", "=", version.id)])
        self.assertEqual(len(own_ack), 1)
        self.assertEqual(own_ack.employee_user_id, self.reader)

    def test_30_reader_does_not_see_draft_successor(self):
        sop = self.make_sop()
        current = self.publish_version(self.make_version(sop))
        successor = self.env["onehr.sop.version"].with_user(
            self.editor
        ).create(
            {
                "sop_id": sop.id,
                **current._copy_content_values(),
                "change_summary": "Draft successor.",
            }
        )
        visible = self.env["onehr.sop.version"].with_user(
            self.reader
        ).search([("id", "=", successor.id)])
        self.assertFalse(visible)

    def test_31_ack_records_cannot_be_created_manually(self):
        version = self.make_version()
        with self.assertRaises(AccessError):
            self.env["onehr.sop.ack"].with_user(
                self.approver
            ).create(
                {
                    "version_id": version.id,
                    "employee_id": self.employee.id,
                }
            )

    def test_32_ack_evidence_cannot_be_deleted(self):
        version = self.publish_version(self.make_version())
        ack = version.ack_ids[:1]
        with self.assertRaises(AccessError):
            ack.with_user(self.admin).unlink()

    def test_33_ack_rate_updates_after_employee_agreement(self):
        version = self.publish_version(self.make_version())
        ack = version.ack_ids.filtered(
            lambda item: item.employee_id == self.employee
        )
        ack.with_user(self.reader).action_acknowledge()
        self.assertEqual(version.acknowledged_count, 1)
        self.assertEqual(version.pending_count, 1)
        self.assertEqual(version.ack_rate, 50.0)

    def test_34_days_to_90_ack_computes_when_threshold_reached(self):
        version = self.publish_version(self.make_version())
        for ack in version.ack_ids:
            user = ack.employee_user_id
            ack.with_user(user).action_acknowledge()
        self.assertEqual(version.ack_rate, 100.0)
        self.assertTrue(version.reached_90_at)
        self.assertGreaterEqual(version.days_to_90_ack, 0.0)

    def test_35_ack_csv_export_is_prepared_for_audit(self):
        version = self.publish_version(self.make_version())
        version.with_user(self.approver).action_export_ack_csv()
        self.assertTrue(version.export_file)
        self.assertTrue(version.export_filename.endswith("_ack.csv"))

    def test_36_portal_payload_returns_current_published_business_content(self):
        version = self.publish_version(self.make_version())
        payload = self.env["onehr.sop"].with_user(
            self.reader
        ).onehr_sop_portal_payload(version.sop_id.code)
        self.assertEqual(payload["sop_reference"], version.sop_id.code)
        self.assertEqual(payload["version"], version.version_no)
        self.assertIn("procedure_steps", payload)
        self.assertEqual(payload["ack_state"], "pending")

    def test_37_api_status_defaults_to_current_user_scope(self):
        version = self.publish_version(self.make_version())
        status = self.env["onehr.sop"].with_user(
            self.reader
        ).onehr_sop_ack_status(sop_code=version.sop_id.code)
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0]["employee_number"], self.employee.onehr_employee_number)

    def test_38_querying_other_employee_status_requires_approver(self):
        version = self.publish_version(self.make_version())
        with self.assertRaises(AccessError):
            self.env["onehr.sop"].with_user(
                self.reader
            ).onehr_sop_ack_status(
                employee_number=self.employee_two.onehr_employee_number,
                sop_code=version.sop_id.code,
            )

    def test_39_kpi_snapshot_reports_ack_and_review_metrics(self):
        version = self.publish_version(self.make_version())
        payload = self.env["onehr.sop"].with_user(
            self.approver
        ).onehr_sop_kpi_snapshot(self.company)
        self.assertEqual(payload["published_sop_count"], 1)
        self.assertEqual(payload["audience_count"], 2)
        self.assertIn("acknowledgement_rate", payload)
        self.assertIn("average_days_to_90_ack", payload)

    def test_40_database_tables_are_safe_and_canonical(self):
        self.assertEqual(self.env["onehr.sop"]._table, "onehr_sop")
        self.assertEqual(
            self.env["onehr.sop.version"]._table,
            "onehr_sop_version",
        )
        self.assertEqual(
            self.env["onehr.sop.ack"]._table,
            "onehr_sop_ack",
        )
        for table in (
            "onehr_sop",
            "onehr_sop_version",
            "onehr_sop_ack",
        ):
            self.assertLessEqual(len(table.encode()), 63)
