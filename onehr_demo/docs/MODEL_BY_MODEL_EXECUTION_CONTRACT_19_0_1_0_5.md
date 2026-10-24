
# OneHR Demo — Model-by-Model Execution Contract 19.0.1.0.7

## Purpose

The Control Center now advances through the frozen `GENERATOR_CONTRACTS` registry one deterministic contract at a time.

The order authority is:

1. contract `phase`
2. contract `key`

It is **not** derived from mutable Odoo production sequence counters, next numbers, or live sequence state.

## Current bounded implementation

| Phase | Contract | Status |
|---:|---|---|
| 5 | `foundation.enterprise` | IMPLEMENTED |
| 6 | `organization.jobs_positions` | IMPLEMENTED |
| 7–24 | remaining frozen contracts | PLANNED / FAIL-CLOSED |

## Operator flow

`Refresh Source Compatibility` → `Enable Demo Generation` → `Validate Readiness` → `Execute Next Model` or `Execute Next 10` → repeat.

Each Execute Next Model creates exactly one generation run and one bounded checkpoint for the selected generator. The next generator is selected from scenario-wide PASS evidence, so restarting the browser, server, or run does not change the deterministic next step.

## Failure semantics

A failed generator remains failed with root-cause evidence. Earlier PASS checkpoints remain reusable. No later contract is silently executed.

If the next frozen contract is not implemented, the Control Center remains fail-closed and records the blocker rather than skipping the requirement.

## Current target

After MP05 PASS, MP06 creates/reuses deterministic:

- `hr.job`
- `onehr.grade`
- `hr.work.location`
- `onehr.position`

All records use stable demo identifiers and `onehr.demo.reference` provenance.



## Execute Next 10

`Execute Next 10` is a bounded batch over the same deterministic engine. Maximum batch size is 10. The batch stops immediately on the first failure or on a next contract whose producer is not implemented. No later contract is skipped. Runtime failure notifications intentionally do not auto-reload the Control Center, while the failed checkpoint and run retain root-cause evidence.
