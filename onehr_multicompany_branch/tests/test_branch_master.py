
# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import OneHRBranchCommon


@tagged("post_install", "-at_install", "onehr_multicompany_branch")
class TestBranchMaster(OneHRBranchCommon):
    def test_01_registry_models_and_native_extensions(self):
        self.assertIn("onehr.branch", self.env)
        self.assertIn("onehr.mixin.branch", self.env)
        self.assertIn("onehr_allowed_branch_ids", self.env["res.users"]._fields)
        self.assertIn("onehr_default_branch_id", self.env["res.users"]._fields)
        self.assertIn("onehr_branch_ids", self.env["res.company"]._fields)
        self.assertIn("branch_id", self.env["onehr.user.role"]._fields)
        self.assertNotIn("onehr_multicompany_branch.onehr_multicompany_branch", self.env)

    def test_02_branch_code_normalization_and_unique_company_key(self):
        branch = self.env["onehr.branch"].create(
            {
                "code": "  bali-01  ",
                "name": "Bali 01",
                "company_id": self.company.id,
            }
        )
        self.assertEqual(branch.code, "BALI-01")

        with self.assertRaises(ValidationError):
            self.env["onehr.branch"].create(
                {
                    "code": "bali-01",
                    "name": "Duplicate",
                    "company_id": self.company.id,
                }
            )

        other = self.env["onehr.branch"].create(
            {
                "code": "bali-01",
                "name": "Same Code Other Company",
                "company_id": self.other_company.id,
            }
        )
        self.assertEqual(other.code, "BALI-01")

    def test_03_hierarchy_company_and_cycle_guards(self):
        child = self.env["onehr.branch"].create(
            {
                "code": "A-CHILD",
                "name": "A Child",
                "company_id": self.company.id,
                "parent_id": self.branch_a.id,
                "valid_from": self.branch_a.valid_from,
            }
        )
        with self.assertRaises(ValidationError):
            self.branch_a.write({"parent_id": child.id})

        with self.assertRaises(ValidationError):
            child.write({"parent_id": self.other_branch.id})

    def test_04_parent_effective_period_must_cover_children(self):
        parent = self.env["onehr.branch"].create(
            {
                "code": "PARENT",
                "name": "Parent",
                "company_id": self.company.id,
                "valid_from": self.today,
                "valid_to": self.today + timedelta(days=60),
            }
        )
        with self.assertRaises(ValidationError):
            self.env["onehr.branch"].create(
                {
                    "code": "EARLY",
                    "name": "Early Child",
                    "company_id": self.company.id,
                    "parent_id": parent.id,
                    "valid_from": self.today - timedelta(days=1),
                }
            )

        child = self.env["onehr.branch"].create(
            {
                "code": "CHILD",
                "name": "Child",
                "company_id": self.company.id,
                "parent_id": parent.id,
                "valid_from": self.today,
                "valid_to": self.today + timedelta(days=30),
            }
        )
        self.assertTrue(child)
        with self.assertRaises(ValidationError):
            parent.write({"valid_to": self.today + timedelta(days=10)})

    def test_05_archive_and_delete_preserve_branch_history(self):
        self.target_user.write({"onehr_default_branch_id": self.branch_a.id})
        with self.assertRaises(ValidationError):
            self.branch_a.with_user(self.branch_admin).action_archive()

        self.target_user.write({"onehr_default_branch_id": False})
        role = self.make_role("ARCHIVE-GUARD")
        assignment = self.make_assignment(role, branch=self.branch_a)
        assignment.with_user(self.security_manager_all).action_activate()
        with self.assertRaises(ValidationError):
            self.branch_a.with_user(self.branch_admin).action_archive()

        with self.assertRaises(AccessError):
            self.branch_b.with_user(self.branch_admin).unlink()

    def test_06_branch_master_audit_evidence_is_created(self):
        branch = self.env["onehr.branch"].with_user(self.branch_admin).create(
            {
                "code": "AUDIT",
                "name": "Audit Branch",
                "company_id": self.company.id,
            }
        )
        branch.with_user(self.branch_admin).write({"name": "Audit Branch Renamed"})
        events = self.env["onehr.audit.log"].search(
            [("model_name", "=", "onehr.branch"), ("res_id", "=", branch.id)]
        )
        self.assertGreaterEqual(len(events), 2)

