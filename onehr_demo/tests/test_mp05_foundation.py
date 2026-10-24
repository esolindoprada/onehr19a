
from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from ..generators.foundation_enterprise import expected_foundation_shape, _branch_code
from ..services.orchestrator import DemoOrchestrator
from ..services.reset import DemoResetService
from .common import DemoCommon


@tagged("post_install", "-at_install")
class TestDemoMP05Foundation(DemoCommon):
    def _ready_scenario(self, profile="quick"):
        scenario = self.create_scenario(profile=profile).with_user(self.system_demo_admin)
        scenario.safety_acknowledged = True
        scenario.action_enable_demo_generation()
        scenario._controlled_write({
            "compatibility_status": "compatible",
            "compatibility_fingerprint": "runtime-test-fingerprint",
            "readiness_status": "ready",
            "state": "ready",
        })
        return scenario

    def _run_generation(self, scenario):
        run = scenario._new_run("generation")
        result = DemoOrchestrator(scenario, run).execute()
        run._controlled_write({
            "state": "pass",
            "finished_at": fields.Datetime.now(),
            "created_count": result.get("created", 0),
            "reused_count": result.get("reused", 0),
            "updated_count": result.get("updated", 0),
            "skipped_count": result.get("skipped", 0),
            "protected_count": result.get("protected", 0),
        })
        return run, result

    def test_01_quick_profile_shape_and_provenance(self):
        scenario = self._ready_scenario("quick")
        run, result = self._run_generation(scenario)
        shape = expected_foundation_shape("quick")
        self.assertEqual(result["created"], shape["branches"] + shape["departments"])
        self.assertEqual(result["reused"], 1)  # selected legal company
        refs = self.env["onehr.demo.reference"].search([
            ("scenario_id", "=", scenario.id),
            ("generator_key", "=", "foundation.enterprise"),
            ("state", "=", "active"),
        ])
        self.assertEqual(len(refs), 1 + shape["branches"] + shape["departments"])
        self.assertTrue(all(row.reset_policy == "REUSE_ON_REBUILD" for row in refs))
        self.assertEqual(run.checkpoint_ids.mapped("state"), ["pass"])

    def test_02_second_generation_is_idempotent(self):
        scenario = self._ready_scenario("quick")
        self._run_generation(scenario)
        branch_count = self.env["onehr.branch"].search_count([
            ("company_id", "=", scenario.company_id.id),
        ])
        department_count = self.env["hr.department"].search_count([
            ("company_id", "=", scenario.company_id.id),
        ])

        _run2, result2 = self._run_generation(scenario)
        self.assertEqual(result2["created"], 0)
        self.assertEqual(result2["reused"], 1 + 2 + 7)
        self.assertEqual(
            self.env["onehr.branch"].search_count([("company_id", "=", scenario.company_id.id)]),
            branch_count,
        )
        self.assertEqual(
            self.env["hr.department"].search_count([("company_id", "=", scenario.company_id.id)]),
            department_count,
        )

    def test_03_reset_retains_masters_and_invalidates_references(self):
        scenario = self._ready_scenario("quick")
        self._run_generation(scenario)
        before_branches = self.env["onehr.branch"].search_count([
            ("company_id", "=", scenario.company_id.id),
        ])
        before_departments = self.env["hr.department"].search_count([
            ("company_id", "=", scenario.company_id.id),
        ])

        rows = DemoResetService(scenario).preview()
        self.assertTrue(rows)
        self.assertTrue(all(row["planned_action"] == "RETAIN_FOR_REBUILD" for row in rows))
        result = DemoResetService(scenario).execute()
        self.assertEqual(result["protected"], 0)
        self.assertEqual(
            self.env["onehr.demo.reference"].search_count([
                ("scenario_id", "=", scenario.id),
                ("state", "=", "active"),
            ]),
            0,
        )
        self.assertEqual(
            self.env["onehr.branch"].search_count([("company_id", "=", scenario.company_id.id)]),
            before_branches,
        )
        self.assertEqual(
            self.env["hr.department"].search_count([("company_id", "=", scenario.company_id.id)]),
            before_departments,
        )

    def test_04_rebuild_reuses_exact_retained_targets(self):
        scenario = self._ready_scenario("quick")
        self._run_generation(scenario)
        original = {
            row.stable_key: (row.target_model, row.target_res_id)
            for row in self.env["onehr.demo.reference"].search([
                ("scenario_id", "=", scenario.id),
                ("generator_key", "=", "foundation.enterprise"),
            ])
        }
        DemoResetService(scenario).execute()
        self._run_generation(scenario)
        rebuilt = {
            row.stable_key: (row.target_model, row.target_res_id)
            for row in self.env["onehr.demo.reference"].search([
                ("scenario_id", "=", scenario.id),
                ("generator_key", "=", "foundation.enterprise"),
            ])
        }
        self.assertEqual(rebuilt, original)

    def test_05_profile_shapes_are_monotonic(self):
        quick = expected_foundation_shape("quick")
        standard = expected_foundation_shape("standard")
        full = expected_foundation_shape("full")
        self.assertLess(quick["branches"], standard["branches"])
        self.assertLess(standard["branches"], full["branches"])
        self.assertLess(quick["departments"], standard["departments"])
        self.assertLess(standard["departments"], full["departments"])

    def test_06_archived_deterministic_branch_is_detected_before_duplicate_create(self):
        scenario = self._ready_scenario("quick")
        code = _branch_code(scenario, "hq_jakarta")
        self.env["onehr.branch"].with_user(self.system_demo_admin).create({
            "code": code,
            "name": "Kantor Pusat Jakarta",
            "company_id": scenario.company_id.id,
            "branch_type": "head_office",
            "active": False,
            "valid_from": "2024-09-01",
        })
        with self.assertRaises(ValidationError):
            self._run_generation(scenario)
        self.assertEqual(
            self.env["onehr.branch"].with_context(active_test=False).search_count([
                ("company_id", "=", scenario.company_id.id),
                ("code", "=", code),
            ]),
            1,
        )

