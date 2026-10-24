
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import OneHRApprovalCommon


@tagged("post_install", "-at_install", "onehr_workflow_approval")
class TestRuleMatrix(OneHRApprovalCommon):
    def test_01_rule_version_overlap_is_rejected(self):
        # Registry setup must retain the Odoo 19-compatible policy for ir.model.
        self.assertEqual(
            self.env["onehr.approval.rule"]._fields["model_id"].ondelete,
            "cascade",
        )
        first = self.make_rule("OVERLAP")
        self.add_step(first)
        first.with_user(self.manager).write({"valid_to": fields.Date.today() + timedelta(days=10)})
        self.activate_rule(first)

        second = self.make_rule(
            "OVERLAP",
            version=2,
            valid_from=fields.Date.today() + timedelta(days=5),
        )
        self.add_step(second)
        with self.assertRaises(ValidationError):
            self.activate_rule(second)

    def test_02_safe_structured_matrix_and_ambiguity_guard(self):
        first = self.make_rule(
            "MATRIX-A",
            priority=100,
            risk_level="high",
            context_match_json={"grade_code": ["G1", "G2"], "employee_class": "PERM"},
        )
        self.add_step(first)
        self.activate_rule(first)
        context = {
            "company_id": self.company.id,
            "document_type": "res.partner",
            "risk_level": "high",
            "currency_id": self.company.currency_id.id,
            "amount": 0.0,
            "extra": {"grade_code": "G1", "employee_class": "PERM"},
        }
        self.assertEqual(
            self.env["onehr.approval.rule"].resolve_for_context("res.partner", context),
            first,
        )

        second = self.make_rule(
            "MATRIX-B",
            priority=100,
            risk_level="high",
            context_match_json={"grade_code": ["G1", "G2"], "employee_class": "PERM"},
        )
        self.add_step(second)
        self.activate_rule(second)
        with self.assertRaises(UserError):
            self.env["onehr.approval.rule"].resolve_for_context("res.partner", context)

    def test_03_step_configuration_guards(self):
        rule = self.make_rule("STEP-GUARD")
        with self.assertRaises(ValidationError):
            self.add_step(
                rule,
                approver_policy="specific_users",
                specific_user_ids=[Command.clear()],
            )
        with self.assertRaises(ValidationError):
            self.add_step(
                rule,
                name="Bad Quorum",
                sequence=20,
                decision_mode="any",
                quorum_count=2,
            )

    def test_04_new_rule_version_copies_steps_without_rewriting_old(self):
        rule = self.make_rule("VERSION")
        self.add_step(rule, name="First")
        self.add_step(rule, name="Second", sequence=20, level=20)
        self.activate_rule(rule)
        action = rule.with_user(self.manager).action_create_new_version()
        new_rule = self.env["onehr.approval.rule"].browse(action["res_id"])
        self.assertEqual(new_rule.version, 2)
        self.assertEqual(new_rule.state, "draft")
        self.assertEqual(len(new_rule.step_ids), 2)
        self.assertEqual(rule.state, "active")

    def test_05_amount_role_and_risk_threshold_matching(self):
        role = self.env["onehr.role"].with_user(self.security_manager).create(
            {"code": "REQ", "name": "Requester Role", "company_id": self.company.id}
        )
        assignment = self.env["onehr.user.role"].with_user(self.security_manager).create(
            {
                "user_id": self.requester.id,
                "role_id": role.id,
                "company_id": self.company.id,
                "valid_from": fields.Date.today(),
            }
        )
        assignment.with_user(self.security_manager).action_activate()

        rule = self.make_rule(
            "THRESHOLD",
            requester_role_id=role.id,
            min_amount=1000.0,
            max_amount=5000.0,
            currency_id=self.company.currency_id.id,
            risk_level="critical",
        )
        self.add_step(rule)
        self.activate_rule(rule)
        context = {
            "company_id": self.company.id,
            "document_type": "res.partner",
            "requester_role_ids": [role.id],
            "amount": 3000.0,
            "currency_id": self.company.currency_id.id,
            "risk_level": "critical",
            "extra": {},
        }
        self.assertEqual(
            self.env["onehr.approval.rule"].resolve_for_context("res.partner", context),
            rule,
        )
