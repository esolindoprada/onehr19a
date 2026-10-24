
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from unittest.mock import patch
from .common import DemoCommon

@tagged("post_install", "-at_install")
class TestDemoControlPlane(DemoCommon):
    def test_01_exact_generator_registry_is_loaded(self):
        generators = self.env["onehr.demo.generator"].search([])
        self.assertEqual(len(generators), 20)
        implemented = generators.filtered("implemented")
        self.assertEqual(implemented.mapped("key"), ["foundation.enterprise"])

    def test_02_scenario_starts_compatibility_required_and_generation_disabled(self):
        scenario = self.create_scenario()
        self.assertEqual(scenario.state, "compatibility_required")
        self.assertEqual(scenario.compatibility_status, "unverified")
        self.assertFalse(scenario.generation_enabled)
        self.assertTrue(scenario.generation_available)
        self.assertEqual(scenario.implemented_generator_count, 1)

    def test_03_run_cannot_be_manually_created(self):
        scenario = self.create_scenario()
        with self.assertRaises(AccessError):
            self.env["onehr.demo.run"].with_user(self.system_demo_admin).create({
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

    def test_04_generation_requires_compatibility_and_readiness(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario.safety_acknowledged = True
        scenario.action_enable_demo_generation()
        with self.assertRaises(UserError):
            scenario.action_generate_quick()

    def test_05_reset_preview_uses_zero_provenance_without_broad_cleanup(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario.safety_acknowledged = True
        scenario.action_enable_demo_generation()
        action = scenario.action_reset_preview()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(scenario.reference_count, 0)

    def test_06_identity_change_invalidates_compatibility(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario._controlled_write({
            "compatibility_status":"compatible",
            "compatibility_fingerprint":"frozen",
            "state":"compatible",
        })
        scenario.profile = "standard"
        self.assertFalse(scenario.compatibility_fingerprint)
        self.assertEqual(scenario.state, "compatibility_required")

    def test_07_scenario_identity_freezes_after_provenance_exists(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario.safety_acknowledged = True
        scenario.action_enable_demo_generation()
        scenario._controlled_write({
            "compatibility_status":"compatible",
            "compatibility_fingerprint":"runtime-test-fingerprint",
            "readiness_status":"ready",
            "state":"ready",
        })
        run = scenario._new_run("generation")
        from ..services.orchestrator import DemoOrchestrator
        DemoOrchestrator(scenario, run).execute()
        with self.assertRaises(ValidationError):
            scenario.write({"reference_date":"2026-10-01"})

    def test_08_demo_control_center_is_reachable_creatable_leaf(self):
        parent = self.env.ref("onehr_demo.menu_onehr_enterprise_demo_dataset")
        control = self.env.ref("onehr_demo.menu_onehr_demo_control_center")
        evidence = self.env.ref("onehr_demo.menu_onehr_demo_evidence")
        action = self.env.ref("onehr_demo.action_onehr_demo_scenarios")

        self.assertFalse(parent.action, "Parent must remain a pure navigation container when it has children.")
        self.assertEqual(control.parent_id, parent)
        self.assertEqual(evidence.parent_id, parent)
        self.assertTrue(control.action)
        self.assertEqual(control.action.id, action.id)
        self.assertEqual(action.res_model, "onehr.demo.scenario")
        self.assertNotIn("create", (action.context or "").lower())

        scenario = self.create_scenario().with_user(self.system_demo_admin)
        self.assertTrue(scenario.exists(), "Demo Administrator must be able to create the Control Center scenario.")

    def test_09_evidence_actions_remain_non_creation_surfaces(self):
        for xmlid in (
            "onehr_demo.action_onehr_demo_generators",
            "onehr_demo.action_onehr_demo_runs",
            "onehr_demo.action_onehr_demo_checkpoints",
            "onehr_demo.action_onehr_demo_references",
            "onehr_demo.action_onehr_demo_logs",
        ):
            action = self.env.ref(xmlid)
            compact = (action.context or "").replace('"', "'").replace(" ", "").lower()
            self.assertIn("'create':false", compact, f"{xmlid} must remain an evidence-only action.")


    def test_10_lifecycle_notifications_request_control_center_reload(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        action = scenario._notification("State Sync", "Reload the control center.", "success", reload_form=True)
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["next"], {"type": "ir.actions.client", "tag": "reload"})

    def test_11_validate_readiness_returns_reload_after_persisting_ready_state(self):
        scenario = self.create_scenario().with_user(self.system_demo_admin)
        scenario._controlled_write({
            "safety_acknowledged": True,
            "generation_enabled": True,
            "compatibility_status": "compatible",
            "compatibility_fingerprint": "runtime-test-fingerprint",
            "state": "compatible",
        })
        audit = {
            "compatible": True,
            "fingerprint": "runtime-test-fingerprint",
            "failure_count": 0,
            "first_failure": None,
        }
        with patch("onehr_demo.models.demo_scenario.CompatibilityAudit.run", return_value=audit):
            action = scenario.action_validate_readiness()
        self.assertEqual(scenario.readiness_status, "ready")
        self.assertEqual(scenario.state, "ready")
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["next"], {"type": "ir.actions.client", "tag": "reload"})

