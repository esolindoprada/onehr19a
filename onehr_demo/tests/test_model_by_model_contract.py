
from odoo.tests.common import TransactionCase

from ..services.contracts import GENERATOR_CONTRACTS, IMPLEMENTED_GENERATOR_KEYS


class TestModelByModelContract(TransactionCase):
    def test_frozen_contract_order_is_phase_key(self):
        ordered = tuple(sorted(GENERATOR_CONTRACTS, key=lambda row: (row["phase"], row["key"])))
        self.assertEqual(ordered[0]["key"], "foundation.enterprise")
        self.assertEqual(ordered[1]["key"], "organization.jobs_positions")

    def test_mp05_mp06_are_implemented(self):
        self.assertIn("foundation.enterprise", IMPLEMENTED_GENERATOR_KEYS)
        self.assertIn("organization.jobs_positions", IMPLEMENTED_GENERATOR_KEYS)

