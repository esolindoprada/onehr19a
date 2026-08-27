# Indonesia Payroll Regulatory Baseline — build date 20 Aug 2026

This file documents the default values copied into a new parameter record. Defaults are never
automatically treated as reviewed: Payroll Bridge refuses to use a version until a Payroll Manager
records regulatory-review evidence.

## PPh21 / PTKP / TER

Current implementation basis:

- PMK 168 Tahun 2023 remains listed by JDIH Kementerian Keuangan as effective from
  1 January 2024 until revoked.
- Monthly TER mapping:
  - A: TK/0, TK/1, K/0
  - B: TK/2, TK/3, K/1, K/2
  - C: K/3
- TER daily: up to Rp450,000 = 0%; above Rp450,000 through Rp2,500,000 = 0.5%.
- Article 17 progressive layers:
  5% to Rp60m; 15% to Rp250m; 25% to Rp500m; 30% to Rp5b; 35% above Rp5b.
- PTKP base Rp54m; marriage/dependent increments Rp4.5m; maximum three dependents.
- spouse-combined-income addition represented separately at Rp54m.
- job expense 5%, maximum Rp500k/month or Rp6m/year.
- full TER A/B/C threshold tables are copied from current DJP PMK 168 guidance.
- TER is identified as regular/non-final tax-period logic; final tax-period annual reconciliation
  remains an external payroll-engine responsibility.
- `pph21_special_policy_json` exists for temporary programs such as government-borne PPh21
  incentives; no employee/sector eligibility is silently assumed.

## BPJS Kesehatan

Current PPU baseline:

- total 5%;
- employer 4%;
- employee 1%;
- private-PPU monthly wage ceiling Rp12,000,000;
- wage floor represented by regional minimum wage or a reviewed manual floor.

## BPJS Ketenagakerjaan

Baseline rates:

- JHT: employer 3.7%, worker 2.0%.
- JKM: employer 0.3%.
- JP: employer 2.0%, worker 1.0%.
- JKK: very low 0.24%; low 0.54%; medium 0.89%; high 1.27%; very high 1.74%.
- JKP payload: 0.46% total funding composition, with no direct employee/employer payroll
  deduction represented by this addon.

### JP wage ceiling 2026

The package default is Rp11,086,300 effective March 2026, based on 2026 BPJS
Ketenagakerjaan branch circular evidence applying the annual PP 45/2015 adjustment formula.
Generic BPJS web guidance may lag and still display a prior ceiling. For this reason:

- ceiling amount and effective date are editable;
- bundle validation forbids using this ceiling before its effective date;
- regulatory review is mandatory before Payroll Bridge generation;
- the next review date is recorded automatically and future payroll teams must re-verify.

## THR

Permenaker 6 Tahun 2016 remains listed as in force.

- continuous service >= 12 months: 1 month wage;
- continuous service >= 1 month and < 12 months: proportional service months / 12;
- one-month wage basis can be clean wage without allowance or basic wage + fixed allowance;
- THR payment deadline parameter defaults to 7 days before the religious holiday.

The company religious-holiday calendar is deliberately editable JSON rather than hard-coded
across years.

## Important implementation boundary

These are configurable reviewed parameters and formula metadata, not a substitute for statutory
advice, certified payroll calculation, employee eligibility determination, tax filing or BPJS
submission. Temporary rules and organization-specific interpretations should be reviewed before
each effective period.
