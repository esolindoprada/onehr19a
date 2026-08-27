from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRApprovalCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Approval Other Company"})

        approval_user_group = cls.env.ref("onehr_workflow_approval.group_onehr_approval_user")
        approver_group = cls.env.ref("onehr_workflow_approval.group_onehr_approver")
        manager_group = cls.env.ref("onehr_workflow_approval.group_onehr_workflow_manager")
        admin_group = cls.env.ref("onehr_workflow_approval.group_onehr_workflow_admin")
        security_manager_group = cls.env.ref("onehr_security.group_onehr_security_manager")

        def make_user(name, login, groups, company=None, companies=None):
            company = company or cls.company
            companies = companies or [company]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([item.id for item in companies])],
                    "group_ids": [Command.set([group.id for group in groups])],
                }
            )

        cls.requester = make_user("Approval Requester", "approval_requester", [approval_user_group])
        cls.approver1 = make_user("Approval Approver 1", "approval_approver_1", [approver_group])
        cls.approver2 = make_user("Approval Approver 2", "approval_approver_2", [approver_group])
        cls.approver3 = make_user("Approval Approver 3", "approval_approver_3", [approver_group])
        cls.manager = make_user(
            "Approval Manager",
            "approval_manager",
            [manager_group],
            companies=[cls.company, cls.other_company],
        )
        cls.workflow_admin = make_user(
            "Approval Administrator",
            "approval_admin",
            [admin_group],
            companies=[cls.company, cls.other_company],
        )
        cls.security_manager = make_user(
            "Approval Security Manager",
            "approval_security_manager",
            [security_manager_group],
        )
        cls.outsider = make_user("Approval Outsider", "approval_outsider", [approval_user_group])
        cls.other_company_user = make_user(
            "Other Company Approval User",
            "approval_other_company",
            [approval_user_group],
            company=cls.other_company,
            companies=[cls.other_company],
        )

        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.source = cls.env["res.partner"].create(
            {"name": "Approval Source Record", "company_id": cls.company.id}
        )
        cls.other_source = cls.env["res.partner"].create(
            {"name": "Other Company Source", "company_id": cls.other_company.id}
        )

    def make_rule(self, code="RULE", **overrides):
        values = {
            "code": code,
            "name": code.title(),
            "company_id": self.company.id,
            "model_id": self.partner_model.id,
            "valid_from": fields.Date.today(),
            "minimum_distinct_approvers": 1,
        }
        values.update(overrides)
        return self.env["onehr.approval.rule"].with_user(self.manager).create(values)

    def add_step(self, rule, name="Manager Approval", **overrides):
        values = {
            "rule_id": rule.id,
            "name": name,
            "level": 10,
            "sequence": 10,
            "approver_policy": "specific_users",
            "specific_user_ids": [Command.set(self.approver1.ids)],
            "decision_mode": "any",
            "quorum_count": 1,
            "valid_from": rule.valid_from,
            "sla_hours": 24,
        }
        values.update(overrides)
        return self.env["onehr.approval.step"].with_user(self.manager).create(values)

    def activate_rule(self, rule):
        rule.with_user(self.manager).action_activate()
        return rule

    def create_request(self, *, source=None, requester=None, context=None):
        source = source or self.source
        requester = requester or self.requester
        context = context or {
            "company_id": source.company_id.id,
            "document_type": "res.partner",
            "amount": 0.0,
            "currency_id": source.company_id.currency_id.id,
            "risk_level": "normal",
            "manager_user_ids": [],
            "approver_user_ids_by_key": {},
            "extra": {},
        }
        return self.env["onehr.approval.request"].with_user(self.manager).create(
            {
                "company_id": source.company_id.id,
                "source_model": source._name,
                "source_res_id": source.id,
                "requested_by_id": requester.id,
                "source_payload_json": {"name": source.display_name},
                "context_json": context,
            }
        )
