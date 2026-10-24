
# OneHR Demo — Enterprise Development Guardrail

GUARDRAIL_ID: `ONEHR-EDG-DEMO-MP02-MP04-V1`  
ROOT_GUARDRAIL_SHA256: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`  
TARGET_ADDON: `onehr_demo`  
TARGET_PLATFORM: Odoo 19 Community Edition  
ATTEMPT: `1 / 2`

This addon inherits the root OneHR Enterprise Development Guardrail in full.

## HARD GATE 0 — Project Identity Preflight
Freeze project, target, Odoo version, latest composite source, Master Prompt and
Guardrail checksum before implementation.

## HARD GATE 1 — Codex is not architect
Role is `BOUNDED_IMPLEMENTATION_WORKER`. Architecture, simplification, deletion,
ownership and dependency-change authority are `NONE`.

## HARD GATE 2 — Existing Function Preservation
No production sibling is edited. `onehr_demo` owns only the six approved demo
control-plane models.

## HARD GATE 3 — Enterprise Completeness
Static/source PASS never implies runtime, business generation, reset/idempotency,
security, analytics or presentation certification.

## HARD GATE 4 — Full Structural Inventory
Persistent model footprint is exactly Scenario, Run, Generator, Checkpoint,
Reference and Log.

## HARD GATE 5 — Human-Friendly Coding Structure
Models, contracts, deterministic helpers, compatibility, orchestration, reset,
security, UI, tests and evidence are separated by responsibility.

## HARD GATE 6 — Professional Form Design
Control Center uses statusbar, action buttons, smart buttons, progress, warning
ribbon, compatibility evidence and operational tabs.

## HARD GATE 7 — UI/UX Matrix per Model
All persistent models have explicit List/Form/Search decisions.

## HARD GATE 8 — Search View Mandatory
All six persistent models have dedicated search views.

## HARD GATE 9 — Enterprise List Quality
Lists expose identifiers, states, scope, timing, counts and bounded navigation.

## HARD GATE 10 — Security Cannot Lose to UI
Server-side Demo Administrator/System Administrator checks remain authoritative.
No production ACL/record-rule weakening is permitted.

## HARD GATE 11 — Database Identifier & ORM Naming Safety
Odoo 19 `models.Constraint` is used. Legacy `_sql_constraints` is forbidden.
PostgreSQL identifiers are bounded.

## HARD GATE 12 — Human-Friendly Code
No arbitrary configured Python, arbitrary model/method dispatch, `eval`,
`safe_eval`, dynamic imports, or shell/command execution.

## HARD GATE 13 — Useful Comments
Comments explain source ownership, determinism, evidence immutability, atomicity,
compatibility lock and reset boundaries.

## HARD GATE 14 — Bounded Retry
`MAX_ATTEMPTS=2`, `MAX_REPEAT_OF_SAME_ROOT_CAUSE=1`. Environment/harness failures
do not authorize business source mutation.

## HARD GATE 15 — Completeness Matrix
Static, runtime, business, reset, security, analytics and presentation evidence are
separate acceptance dimensions.

`END_GUARDRAIL: ONEHR-EDG-DEMO-MP02-MP04-V1`

