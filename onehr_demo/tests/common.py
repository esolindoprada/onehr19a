
from odoo import Command
from odoo.tests.common import TransactionCase

class DemoCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_viewer = cls.env.ref("onehr_demo.group_onehr_demo_viewer")
        cls.group_admin = cls.env.ref("onehr_demo.group_onehr_demo_admin")
        cls.group_system = cls.env.ref("base.group_system")
        cls.group_hr_manager = cls.env.ref("hr.group_hr_manager")
        cls.group_branch_admin = cls.env.ref("onehr_multicompany_branch.group_onehr_branch_admin")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.viewer = Users.create({
            "name":"OneHR Demo Evidence Viewer",
            "login":"onehr.demo.viewer@example.invalid",
            "email":"onehr.demo.viewer@example.invalid",
            "company_id":cls.company.id,
            "company_ids":[Command.set([cls.company.id])],
            "group_ids":[Command.set([cls.group_viewer.id])],
        })
        cls.demo_admin = Users.create({
            "name":"OneHR Demo Administrator",
            "login":"onehr.demo.admin@example.invalid",
            "email":"onehr.demo.admin@example.invalid",
            "company_id":cls.company.id,
            "company_ids":[Command.set([cls.company.id])],
            "group_ids":[Command.set([cls.group_admin.id])],
        })
        cls.system_demo_admin = Users.create({
            "name":"OneHR Demo System Administrator",
            "login":"onehr.demo.sysadmin@example.invalid",
            "email":"onehr.demo.sysadmin@example.invalid",
            "company_id":cls.company.id,
            "company_ids":[Command.set([cls.company.id])],
            "group_ids":[Command.set([
                cls.group_admin.id,
                cls.group_system.id,
                cls.group_hr_manager.id,
                cls.group_branch_admin.id,
            ])],
        })

    def create_scenario(self, **overrides):
        values = {
            "name":"Enterprise Demo",
            "code":"onehr_demo.enterprise",
            "company_id":self.company.id,
            "profile":"quick",
            "reference_date":"2026-09-01",
            "reference_datetime":"2026-09-01 02:00:00",
            "timezone":"Asia/Jakarta",
            "deterministic_seed":247,
        }
        values.update(overrides)
        return self.env["onehr.demo.scenario"].with_user(self.system_demo_admin).create(values)

