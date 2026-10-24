
from odoo.tests import tagged
from onehr_demo.services.contracts import GENERATOR_CONTRACTS, IMPLEMENTED_GENERATOR_KEYS, SEQUENCE_POLICIES
from onehr_demo.services.deterministic import deterministic_rng, stable_demo_key, stable_identifier
from .common import DemoCommon

@tagged("post_install", "-at_install")
class TestDemoDeterminismContract(DemoCommon):
    def test_01_stable_demo_key_is_repeatable(self):
        a = stable_demo_key("onehr_demo.enterprise","workforce","employee","hero_hipo_01")
        b = stable_demo_key("onehr_demo.enterprise","workforce","employee","hero_hipo_01")
        self.assertEqual(a,b)

    def test_02_stable_identifier_is_repeatable_and_bounded(self):
        a = stable_identifier("EMP","onehr_demo.enterprise.workforce.employee.hero_hipo_01",32)
        b = stable_identifier("EMP","onehr_demo.enterprise.workforce.employee.hero_hipo_01",32)
        self.assertEqual(a,b)
        self.assertLessEqual(len(a),32)

    def test_03_seeded_rng_is_repeatable(self):
        a = deterministic_rng(247,"workforce.tenure")
        b = deterministic_rng(247,"workforce.tenure")
        self.assertEqual([a.randint(1,100) for _ in range(10)],[b.randint(1,100) for _ in range(10)])

    def test_04_contract_inventory_is_whole_path(self):
        self.assertEqual(len(GENERATOR_CONTRACTS),20)
        self.assertEqual(len(SEQUENCE_POLICIES),34)
        self.assertEqual(IMPLEMENTED_GENERATOR_KEYS,("foundation.enterprise",))

    def test_05_every_sequence_policy_forbids_direct_demo_sequence_use(self):
        self.assertTrue(all(row["direct_demo_next_by_code"] == "FORBIDDEN" for row in SEQUENCE_POLICIES))

    def test_06_each_generator_has_explicit_safety_and_reset_classification(self):
        self.assertTrue(all(row["side_effect"] != "UNVERIFIED" for row in GENERATOR_CONTRACTS))
        self.assertTrue(all(row["reset_policy"] != "UNVERIFIED" for row in GENERATOR_CONTRACTS))

