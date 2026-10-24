
from odoo.exceptions import AccessError
from odoo.tests import tagged
from .common import DemoCommon

@tagged("post_install", "-at_install")
class TestDemoSecuritySafety(DemoCommon):
    def test_01_viewer_cannot_create_scenario(self):
        with self.assertRaises(AccessError):
            self.env["onehr.demo.scenario"].with_user(self.viewer).create({
                "name":"Denied","code":"denied.demo","company_id":self.company.id
            })

    def test_02_demo_admin_without_system_authority_cannot_enable(self):
        scenario = self.env["onehr.demo.scenario"].with_user(self.demo_admin).create({
            "name":"Admin but not System","code":"demo.admin_only","company_id":self.company.id
        })
        scenario.safety_acknowledged = True
        with self.assertRaises(AccessError):
            scenario.action_enable_demo_generation()

    def test_03_system_demo_admin_can_enable_and_disable(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario.safety_acknowledged = True
        scenario.action_enable_demo_generation()
        self.assertTrue(scenario.generation_enabled)
        scenario.action_disable_demo_generation()
        self.assertFalse(scenario.generation_enabled)

    def test_04_log_sanitizes_secrets(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        log = self.env["onehr.demo.log"].with_user(self.system_demo_admin).log_event(
            scenario_id=scenario.id,
            company_id=scenario.company_id.id,
            category="system",
            severity="error",
            message="token=super-secret-value",
            technical_detail="Authorization: Bearer abc.def.ghi password=hidden",
        )
        self.assertNotIn("super-secret-value", log.message)
        self.assertNotIn("abc.def.ghi", log.technical_detail)
        self.assertNotIn("password=hidden", log.technical_detail)

    def test_05_evidence_models_reject_manual_unlink(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        run = self.env["onehr.demo.run"].with_user(self.system_demo_admin)._controlled_create({
            "scenario_id":scenario.id,
            "company_id":scenario.company_id.id,
            "run_type":"readiness",
            "profile":scenario.profile,
            "reference_date":scenario.reference_date,
            "reference_datetime":scenario.reference_datetime,
            "timezone":scenario.timezone,
            "deterministic_seed":scenario.deterministic_seed,
            "scenario_version":scenario.scenario_version,
        })
        with self.assertRaises(AccessError):
            run.unlink()

    def test_06_generator_registry_is_not_user_editable(self):
        generator = self.env["onehr.demo.generator"].search([], limit=1)
        with self.assertRaises(AccessError):
            generator.with_user(self.demo_admin).write({"name":"Tampered"})

