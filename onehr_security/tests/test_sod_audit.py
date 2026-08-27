from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRSecurityCommon


@tagged("post_install", "-at_install", "onehr_security")
class TestSoDAndAuditEvidence(OneHRSecurityCommon):
    def test_05_deny_sod_blocks_role_and_records_evidence(self):
        role_a = self._role("PREPARER", group=self.functional_group_a)
        role_b = self._role("FINAL-APPROVER", group=self.functional_group_b)
        matrix = self.env["onehr.sod.matrix"].create(
            {
                "code": "PREP-FINAL",
                "name": "Preparation versus Final Approval",
                "company_id": self.company.id,
                "role_a_id": role_a.id,
                "role_b_id": role_b.id,
                "severity": "critical",
                "enforcement": "deny",
            }
        )

        first = self._assignment(role_a)
        first.with_user(self.manager).action_activate()

        with self.assertRaises((AccessError, ValidationError)):
            matrix.with_user(self.admin).unlink()

        second = self._assignment(role_b)
        second.with_user(self.manager).action_activate()

        self.target_user.invalidate_recordset(["group_ids"])
        self.assertEqual(second.state, "blocked")
        self.assertNotIn(self.functional_group_b, self.target_user.group_ids)

        conflict = self.env["onehr.sod.conflict.log"].search(
            [("matrix_id", "=", matrix.id), ("user_id", "=", self.target_user.id)]
        )
        self.assertEqual(len(conflict), 1)
        self.assertEqual(conflict.enforcement, "deny")
        self.assertEqual(conflict.state, "open")

    def test_06_warn_sod_records_evidence_but_allows_access(self):
        role_a = self._role("WARN-A", group=self.functional_group_a)
        role_b = self._role("WARN-B", group=self.functional_group_b)
        matrix = self.env["onehr.sod.matrix"].create(
            {
                "code": "WARN-PAIR",
                "name": "Warning Pair",
                "company_id": self.company.id,
                "role_a_id": role_a.id,
                "role_b_id": role_b.id,
                "severity": "high",
                "enforcement": "warn",
            }
        )

        first = self._assignment(role_a)
        first.with_user(self.manager).action_activate()
        second = self._assignment(role_b)
        second.with_user(self.manager).action_activate()

        self.target_user.invalidate_recordset(["group_ids"])
        self.assertEqual(second.state, "active")
        self.assertIn(self.functional_group_b, self.target_user.group_ids)
        self.assertTrue(
            self.env["onehr.sod.conflict.log"].search_count(
                [("matrix_id", "=", matrix.id), ("user_id", "=", self.target_user.id)]
            )
        )

    def test_07_conflict_resolution_becomes_immutable(self):
        role_a = self._role("IMM-A")
        role_b = self._role("IMM-B")
        matrix = self.env["onehr.sod.matrix"].create(
            {
                "code": "IMM-PAIR",
                "name": "Immutable Pair",
                "company_id": self.company.id,
                "role_a_id": role_a.id,
                "role_b_id": role_b.id,
                "enforcement": "deny",
            }
        )
        conflict = self.env["onehr.sod.conflict.log"]._record_conflict(
            matrix=matrix,
            user=self.target_user,
            company=self.company,
            details="Test evidence",
        )

        conflict.with_user(self.compliance).write(
            {"resolution_comment": "Dual review introduced and evidenced."}
        )
        conflict.with_user(self.compliance).action_mark_mitigated()
        self.assertEqual(conflict.state, "mitigated")
        self.assertEqual(conflict.resolution_note, "Dual review introduced and evidenced.")
        self.assertTrue(conflict.resolved_at)
        self.assertEqual(conflict.resolved_by_id, self.compliance)

        with self.assertRaises(AccessError):
            conflict.with_user(self.compliance).write({"resolution_note": "rewrite"})

        with self.assertRaises(AccessError):
            conflict.with_user(self.compliance).write({"resolution_comment": "rewrite"})

        with self.assertRaises(AccessError):
            conflict.with_user(self.admin).unlink()

    def test_08_audit_is_append_only_and_controlled_anonymization_works(self):
        audit = self.env["onehr.audit.log"]._log_event(
            action="other",
            summary="Sensitive audit payload",
            severity="high",
            record=self.target_user,
            company=self.company,
            before={"secret": "before"},
            after={"secret": "after"},
        )

        with self.assertRaises(AccessError):
            audit.with_user(self.admin).write({"summary": "rewrite"})

        audit.with_user(self.compliance).action_anonymize_payload()
        self.assertTrue(audit.is_anonymized)
        self.assertFalse(audit.before_json)
        self.assertFalse(audit.after_json)

        with self.assertRaises(AccessError):
            audit.with_user(self.admin).unlink()
