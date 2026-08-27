import json

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import OneHRPayrollL10nIdCommon


@tagged("post_install", "-at_install", "onehr_payroll_l10n_id")
class TestIndonesiaPayrollRegulatoryPayload(OneHRPayrollL10nIdCommon):
    def test_16_ptkp_defaults_cover_supported_statuses(self):
        parameter = self.make_parameter()
        ptkp = json.loads(parameter.ptkp_map_json)
        self.assertEqual(ptkp["TK/0"], 54_000_000)
        self.assertEqual(ptkp["K/3"], 72_000_000)

    def test_17_ter_category_mapping_matches_ptkp_groups(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.onehr_ter_category_for_ptkp("TK/0"), "A")
        self.assertEqual(parameter.onehr_ter_category_for_ptkp("TK/2"), "B")
        self.assertEqual(parameter.onehr_ter_category_for_ptkp("K/3"), "C")

    def test_18_ter_a_lookup_matches_official_table_example(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.onehr_ter_monthly_rate("A", 17_500_000), 8.0)

    def test_19_ter_b_lookup_uses_open_ended_final_band(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.onehr_ter_monthly_rate("B", 2_000_000_000), 34.0)

    def test_20_ter_c_lookup_matches_mid_band(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.onehr_ter_monthly_rate("C", 40_000_000), 15.0)

    def test_21_article17_progressive_brackets_have_35_percent_top_rate(self):
        parameter = self.make_parameter()
        rows = json.loads(parameter.article17_brackets_json)
        self.assertEqual(rows[0]["max_taxable_income"], 60_000_000)
        self.assertEqual(rows[-1]["rate_percent"], 35.0)
        self.assertIsNone(rows[-1]["max_taxable_income"])

    def test_22_bpjs_health_ppu_default_total_is_five_percent(self):
        parameter = self.make_parameter()
        self.assertEqual(
            parameter.bpjs_health_employer_rate_percent
            + parameter.bpjs_health_employee_rate_percent,
            5.0,
        )
        self.assertEqual(parameter.bpjs_health_wage_ceiling, 12_000_000)

    def test_23_bpjs_employment_core_rates_are_explicit(self):
        parameter = self.make_parameter()
        self.assertAlmostEqual(
            parameter.bpjs_jht_employer_rate_percent
            + parameter.bpjs_jht_employee_rate_percent,
            5.7,
        )
        self.assertAlmostEqual(
            parameter.bpjs_jp_employer_rate_percent
            + parameter.bpjs_jp_employee_rate_percent,
            3.0,
        )
        self.assertEqual(parameter.bpjs_jkm_employer_rate_percent, 0.3)
        self.assertEqual(parameter.bpjs_jp_wage_ceiling, 11_086_300)

    def test_24_jkk_risk_rates_are_explicit(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.bpjs_jkk_very_low_rate_percent, 0.24)
        self.assertEqual(parameter.bpjs_jkk_low_rate_percent, 0.54)
        self.assertEqual(parameter.bpjs_jkk_medium_rate_percent, 0.89)
        self.assertEqual(parameter.bpjs_jkk_high_rate_percent, 1.27)
        self.assertEqual(parameter.bpjs_jkk_very_high_rate_percent, 1.74)

    def test_25_thr_prorata_helper_uses_service_months_over_twelve(self):
        parameter = self.make_parameter()
        self.assertEqual(parameter.onehr_thr_multiplier(0), 0.0)
        self.assertEqual(parameter.onehr_thr_multiplier(6), 0.5)
        self.assertEqual(parameter.onehr_thr_multiplier(12), 1.0)

    def test_26_parameter_payload_has_stable_hash(self):
        parameter = self.review_parameter()
        first = parameter.onehr_parameter_payload()
        second = parameter.onehr_parameter_payload()
        self.assertEqual(first["parameter_sha256"], second["parameter_sha256"])
        self.assertEqual(len(first["parameter_sha256"]), 64)
        self.assertEqual(first["pph21"]["ter_monthly"]["A"][17]["rate_percent"], 8.0)

    def test_27_unreviewed_parameter_is_rejected_for_payroll_use(self):
        parameter = self.make_parameter()
        with self.assertRaises(ValidationError):
            parameter.onehr_parameter_payload(require_review=True)
