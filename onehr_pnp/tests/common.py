
from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRPnPCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"PnP Other Company {cls.__name__}"}
        )

        cls.group_reader = cls.env.ref("onehr_pnp.group_onehr_pnp_reader")
        cls.group_owner = cls.env.ref("onehr_pnp.group_onehr_pnp_owner")
        cls.group_compliance = cls.env.ref("onehr_pnp.group_onehr_pnp_compliance")
        cls.group_admin = cls.env.ref("onehr_pnp.group_onehr_pnp_admin")
        cls.group_plain = cls.env.ref("base.group_user")
        cls.group_workflow_manager = cls.env.ref(
            "onehr_workflow_approval.group_onehr_workflow_manager"
        )

        suffix = cls.__name__.lower()

        def make_user(name, login, group, company, companies=None):
            companies = companies or [company]
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": name,
                    "login": f"{login}_{suffix}",
                    "company_id": company.id,
                    "company_ids": [
                        Command.set([item.id for item in companies])
                    ],
                    "group_ids": [Command.set([group.id])],
                }
            )

        cls.reader = make_user(
            "PnP Reader",
            "pnp_reader",
            cls.group_reader,
            cls.company,
        )
        cls.reader_two = make_user(
            "PnP Reader Two",
            "pnp_reader_two",
            cls.group_reader,
            cls.company,
        )
        cls.owner = make_user(
            "PnP Policy Owner",
            "pnp_owner",
            cls.group_owner,
            cls.company,
        )
        cls.compliance = make_user(
            "PnP Compliance",
            "pnp_compliance",
            cls.group_compliance,
            cls.company,
        )
        cls.admin = make_user(
            "PnP Administrator",
            "pnp_admin",
            cls.group_admin,
            cls.company,
        )
        cls.plain_user = make_user(
            "PnP Plain Internal",
            "pnp_plain",
            cls.group_plain,
            cls.company,
        )
        cls.workflow_manager = make_user(
            "PnP Workflow Manager",
            "pnp_workflow_manager",
            cls.group_workflow_manager,
            cls.company,
            companies=[cls.company, cls.other_company],
        )
        cls.other_compliance = make_user(
            "Other Company PnP Compliance",
            "pnp_other_compliance",
            cls.group_compliance,
            cls.other_company,
        )

        cls.department = cls.env["hr.department"].create(
            {
                "name": "PnP Finance",
                "company_id": cls.company.id,
            }
        )
        cls.other_department = cls.env["hr.department"].create(
            {
                "name": "PnP Other Finance",
                "company_id": cls.other_company.id,
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "PnP Finance Analyst",
                "company_id": cls.company.id,
            }
        )
        cls.other_job = cls.env["hr.job"].create(
            {
                "name": "PnP Other Analyst",
                "company_id": cls.other_company.id,
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "PnP Employee One",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "user_id": cls.reader.id,
                "onehr_employee_number": f"PNP-E001-{suffix}",
                "work_email": f"pnp.employee1.{suffix}@example.com",
            }
        )
        cls.employee_two = cls.env["hr.employee"].create(
            {
                "name": "PnP Employee Two",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "job_id": cls.job.id,
                "user_id": cls.reader_two.id,
                "onehr_employee_number": f"PNP-E002-{suffix}",
                "work_email": f"pnp.employee2.{suffix}@example.com",
            }
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {
                "name": "PnP Other Employee",
                "company_id": cls.other_company.id,
                "department_id": cls.other_department.id,
                "job_id": cls.other_job.id,
                "user_id": cls.other_compliance.id,
                "onehr_employee_number": f"PNP-O001-{suffix}",
            }
        )

        cls.document_category = cls.env[
            "onehr.document.category"
        ].with_user(cls.compliance).create(
            {
                "code": f"PNP-{suffix}",
                "name": "PnP Controlled Policy Archive",
                "company_id": cls.company.id,
                "sensitivity": "internal",
                "employee_visible": False,
                "signature_required": False,
                "valid_from": fields.Date.today(),
            }
        )

        policy_model = cls.env["ir.model"]._get("onehr.policy")
        cls.approval_rule = cls.env["onehr.approval.rule"].with_user(
            cls.workflow_manager
        ).create(
            {
                "code": f"PNP-{suffix}",
                "name": "PnP Policy Approval",
                "company_id": cls.company.id,
                "model_id": policy_model.id,
                "document_type": "onehr.policy.policy",
                "risk_level": "normal",
                "valid_from": fields.Date.today(),
                "minimum_distinct_approvers": 1,
                "priority": 500,
            }
        )
        cls.approval_step = cls.env["onehr.approval.step"].with_user(
            cls.workflow_manager
        ).create(
            {
                "rule_id": cls.approval_rule.id,
                "name": "Compliance Approval",
                "level": 10,
                "sequence": 10,
                "approver_policy": "specific_users",
                "specific_user_ids": [
                    Command.set([cls.compliance.id])
                ],
                "decision_mode": "any",
                "quorum_count": 1,
                "valid_from": cls.approval_rule.valid_from,
                "sla_hours": 24,
            }
        )
        cls.approval_rule.with_user(
            cls.workflow_manager
        ).action_activate()

    def policy_values(self, **extra):
        values = {
            "name": f"Policy {self._testMethodName}",
            "policy_type": "policy",
            "company_id": self.company.id,
            "owner_user_id": self.owner.id,
            "compliance_user_ids": [
                Command.set([self.compliance.id])
            ],
            "effective_from": fields.Date.today(),
            "review_interval_months": 12,
            "ack_reminder_days": 7,
            "retention_years": 7,
            "risk_level": "normal",
            "target_department_ids": [
                Command.set([self.department.id])
            ],
            "acknowledgement_required": True,
            "evidence_required": True,
            "evidence_due_days": 14,
            "purpose": "<p>Define a controlled HR policy.</p>",
            "scope": "<p>Applies to the selected workforce audience.</p>",
            "policy_statement": "<p>Employees must comply with this policy.</p>",
            "responsibilities": "<p>Owner governs; employees comply; Compliance verifies.</p>",
            "controls": "<p>Approval, acknowledgement and evidence are mandatory.</p>",
            "exceptions": "<p>Exceptions require documented approval.</p>",
            "references": "<p>Applicable company governance references.</p>",
            "document_category_id": self.document_category.id,
        }
        values.update(extra)
        return values

    def make_policy(self, **extra):
        return self.env["onehr.policy"].with_user(
            self.owner
        ).create(self.policy_values(**extra))

    def latest_request(self, policy):
        return self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", "onehr.policy"),
                ("source_res_id", "=", policy.id),
            ],
            order="requested_at desc, id desc",
            limit=1,
        )

    def approve_policy(self, policy):
        policy.with_user(self.owner).action_submit_policy_approval()
        request = self.latest_request(policy)
        request.with_user(self.compliance).action_approve()
        policy.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(policy.state, "approved")
        self.assertEqual(request.state, "approved")
        return request

    def publish_policy(self, policy=None):
        policy = policy or self.make_policy()
        request = self.approve_policy(policy)
        policy.with_user(self.compliance).action_publish()
        policy.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(policy.state, "published")
        self.assertEqual(request.state, "executed")
        return policy

    def own_ack(self, policy, employee=None):
        employee = employee or self.employee
        return policy.ack_ids.filtered(
            lambda ack: ack.employee_id == employee
        )[:1]

    def create_note_evidence(self, policy, reader=None, employee=None):
        reader = reader or self.reader
        employee = employee or self.employee
        ack = self.own_ack(policy, employee)
        return self.env["onehr.policy.evidence"].with_user(reader).create(
            {
                "policy_id": policy.id,
                "ack_id": ack.id,
                "evidence_type": "note",
                "title": "Compliance Evidence",
                "evidence_note": "Employee confirms required compliance evidence.",
            }
        )

