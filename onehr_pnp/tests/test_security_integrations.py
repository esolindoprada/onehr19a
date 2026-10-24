
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRPnPCommon


@tagged("post_install", "-at_install", "onehr_pnp")
class TestPnPSecurityIntegrations(OneHRPnPCommon):
    def test_33_reader_sees_only_assigned_policy(self):
        policy = self.publish_policy()
        visible = self.env["onehr.policy"].with_user(
            self.reader
        ).search([("id", "=", policy.id)])
        self.assertEqual(visible.id, policy.id)

        reader_ack = self.env["onehr.policy.ack"].with_user(
            self.reader
        ).search([("policy_id", "=", policy.id)])
        self.assertEqual(len(reader_ack), 1)
        self.assertEqual(reader_ack.employee_user_id, self.reader)

    def test_34_reader_cannot_see_draft_revision(self):
        policy = self.publish_policy()
        action = policy.with_user(self.compliance).action_create_revision()
        revision = self.env["onehr.policy"].browse(action["res_id"])
        visible = self.env["onehr.policy"].with_user(
            self.reader
        ).search([("id", "=", revision.id)])
        self.assertFalse(visible)

    def test_35_multi_company_policy_isolation(self):
        values = self.policy_values(
            name="Other Company Policy",
            company_id=self.other_company.id,
            owner_user_id=self.other_compliance.id,
            compliance_user_ids=[
                (6, 0, [self.other_compliance.id])
            ],
            target_department_ids=[
                (6, 0, [self.other_department.id])
            ],
            target_employee_ids=[(6, 0, [])],
            document_category_id=False,
        )
        other_policy = self.env["onehr.policy"].with_user(
            self.other_compliance
        ).create(values)
        visible = self.env["onehr.policy"].with_user(
            self.compliance
        ).search([("id", "=", other_policy.id)])
        self.assertFalse(visible)

    def test_36_ack_records_cannot_be_created_manually(self):
        policy = self.make_policy()
        with self.assertRaises(AccessError):
            self.env["onehr.policy.ack"].with_user(
                self.compliance
            ).create(
                {
                    "policy_id": policy.id,
                    "employee_id": self.employee.id,
                    "due_date": policy.review_due_date,
                }
            )

    def test_37_ack_records_cannot_be_deleted(self):
        policy = self.publish_policy()
        ack = self.own_ack(policy)
        with self.assertRaises(AccessError):
            ack.with_user(self.admin).unlink()

    def test_38_submitted_evidence_cannot_be_deleted(self):
        policy = self.publish_policy()
        evidence = self.create_note_evidence(policy)
        evidence.with_user(self.reader).action_submit()
        with self.assertRaises(AccessError):
            evidence.with_user(self.admin).unlink()

    def test_39_portal_payload_is_assignment_scoped(self):
        policy = self.publish_policy()
        payload = self.env["onehr.policy"].with_user(
            self.reader
        ).onehr_policy_portal_payload(policy.policy_code)
        self.assertEqual(payload["policy_reference"], policy.policy_code)
        self.assertEqual(payload["version"], policy.version_no)
        self.assertEqual(payload["ack_state"], "pending")
        self.assertIn("policy_statement", payload)

    def test_40_api_ack_status_defaults_to_self(self):
        policy = self.publish_policy()
        rows = self.env["onehr.policy"].with_user(
            self.reader
        ).onehr_pnp_ack_status(
            policy_code=policy.policy_code
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], "pending")

    def test_41_employee_number_query_requires_compliance(self):
        policy = self.publish_policy()
        with self.assertRaises(AccessError):
            self.env["onehr.policy"].with_user(
                self.reader
            ).onehr_pnp_ack_status(
                policy_code=policy.policy_code,
                employee_number=self.employee_two.onehr_employee_number,
            )

    def test_42_portal_service_can_submit_own_note_evidence(self):
        policy = self.publish_policy()
        result = self.env["onehr.policy"].with_user(
            self.reader
        ).onehr_pnp_submit_evidence(
            {
                "policy_code": policy.policy_code,
                "title": "Portal Note Evidence",
                "evidence_type": "note",
                "note": "Evidence submitted through the model-service contract.",
            }
        )
        evidence = self.env["onehr.policy.evidence"].browse(
            result["evidence_id"]
        )
        self.assertEqual(evidence.state, "submitted")
        self.assertEqual(evidence.employee_user_id, self.reader)

    def test_43_compliance_snapshot_returns_governed_metrics(self):
        policy = self.publish_policy()
        payload = self.env["onehr.policy"].with_user(
            self.compliance
        ).onehr_pnp_compliance_snapshot(self.company)
        self.assertEqual(payload["current_policy_count"], 1)
        self.assertEqual(payload["audience_count"], 2)
        self.assertIn("average_acknowledgement_rate", payload)
        self.assertIn("average_evidence_coverage_rate", payload)

    def test_44_soft_sop_reference_does_not_create_static_orm_dependency(self):
        policy = self.make_policy(
            related_sop_references="SOP/2026/00001"
        )
        self.assertEqual(
            policy.related_sop_references,
            "SOP/2026/00001",
        )

    def test_46_unit_evidence_can_cover_department_audience(self):
        policy = self.publish_policy()
        evidence = self.env["onehr.policy.evidence"].with_user(
            self.compliance
        ).create(
            {
                "policy_id": policy.id,
                "evidence_scope": "unit",
                "unit_department_id": self.department.id,
                "evidence_type": "note",
                "title": "Unit Control Evidence",
                "evidence_note": "Verified control applies to the complete target unit.",
            }
        )
        evidence.with_user(self.compliance).action_submit()
        evidence.with_user(self.compliance).action_verify()
        policy.invalidate_recordset()
        self.assertEqual(policy.evidence_coverage_rate, 100.0)

    def test_47_policy_wide_evidence_can_cover_complete_audience(self):
        policy = self.publish_policy()
        evidence = self.env["onehr.policy.evidence"].with_user(
            self.compliance
        ).create(
            {
                "policy_id": policy.id,
                "evidence_scope": "policy",
                "evidence_type": "note",
                "title": "Policy-wide Control Evidence",
                "evidence_note": "Verified policy-wide compliance control.",
            }
        )
        evidence.with_user(self.compliance).action_submit()
        evidence.with_user(self.compliance).action_verify()
        policy.invalidate_recordset()
        self.assertEqual(policy.evidence_coverage_rate, 100.0)

    def test_45_canonical_database_tables(self):
        self.assertEqual(self.env["onehr.policy"]._table, "onehr_policy")
        self.assertEqual(
            self.env["onehr.policy.ack"]._table,
            "onehr_policy_ack",
        )
        self.assertEqual(
            self.env["onehr.policy.evidence"]._table,
            "onehr_policy_evidence",
        )
        for table in (
            "onehr_policy",
            "onehr_policy_ack",
            "onehr_policy_evidence",
        ):
            self.assertLessEqual(len(table.encode("utf-8")), 63)

