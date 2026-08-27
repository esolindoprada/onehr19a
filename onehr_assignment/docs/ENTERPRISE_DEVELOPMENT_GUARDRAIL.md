# OneHR Assignment — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V9-ASSIGNMENT-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_assignment
TARGET_PLATFORM: Odoo 19 Community Edition
PRIMARY_DELIVERY_METHOD: DIRECT_FULL_ADDON_BUILD
CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY: NONE
SIMPLIFICATION_AUTHORITY: NONE
DELETION_AUTHORITY: NONE
MODEL_OWNERSHIP_CHANGE_AUTHORITY: NONE
DEPENDENCY_CHANGE_AUTHORITY: NONE
MAX_CODEX_ATTEMPTS_PER_TASK: 2
MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1
STATIC_RUNTIME_PASS_IS_NOT_FUNCTIONAL_COMPLETENESS: TRUE
MOVE_FORWARD_REQUIRES_ALL_HARD_GATES: TRUE

## Purpose

This Guardrail is mandatory for design, implementation, runtime remediation, upgrade,
migration and acceptance of `onehr_assignment`. It is a hard gate, not advisory text.
No source worker or repair tool may reduce the approved enterprise scope merely to make
installation or tests pass.

## Architecture authority

Architecture remains owned outside Codex. The authoritative order is:

1. OneHR Enterprise Architecture v2.
2. OneHR Master Model Registry v1.
3. Approved OneHR 25-addon topology and dependency ownership.
4. Odoo 19 CE native-model ownership.
5. Current accepted contracts of `onehr_base`, `onehr_corehr`, `onehr_security` and
   `onehr_workflow_approval`.
6. OneHR 25 Addons Specification and Oracle HRMS functional benchmark where compatible
   with the frozen OneHR Registry.

A conflict with those authorities is an architecture conflict. Implementation stops;
Codex may not invent a new owner/model/dependency to escape it.

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

Before editing, verify all seven items:

- PROJECT: OneHR NEW
- ADDON: `onehr_assignment`
- AUTHORITATIVE BASELINE: Architecture v2 + Registry v1 + approved topology + latest
  accepted sibling contracts + latest user source dump
- PRESERVATION RULE: preserve the seven Registry-owned Assignment models, Odoo-native
  `hr.employee/hr.version`, placement history, primary/secondary assignment, FTE,
  movement, costing, position capacity and workforce planning
- ALLOWED CHANGE: full replacement of the obsolete generic scaffold with the approved
  enterprise implementation; compatibility hardening; professional UI; security; tests
- FORBIDDEN CHANGE: new unapproved business models, duplicate employee/job/department,
  ownership transfer, hard dependency drift, security weakening, history deletion
- CURRENT VERIFIED STATUS: source acceptance and Windows runtime status must be reported
  separately

Failure of any item blocks implementation.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is a bounded implementation worker only. It may implement an already-approved
contract or fix one proven source defect. It may not redesign ownership, dependencies,
workflow, model registry, security boundaries or enterprise scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

The following capabilities are non-negotiable preservation targets:

- effective-dated primary/secondary assignment history;
- organizational/job/position/grade/work-location projection from the approved Position;
- direct-manager/reporting relationship;
- employee and position FTE/headcount control;
- governed single and batch movement;
- assignment cost allocation without taking payroll/accounting ownership;
- workforce plan versioning and position budgets;
- approval evidence, activity/chatter and historical immutability;
- approved primary assignment synchronization to Odoo-native `hr.version`;
- company isolation and future branch-extension compatibility.

A feature is never removed because it is inconvenient to test.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax PASS, XML PASS, install PASS, upgrade PASS or unit-test PASS is evidence only.
Enterprise completion additionally requires workflow behavior, ownership integrity,
security, effective dating, history, capacity, costing, planning, UI quality and
integration contracts to be complete with no applicable PENDING/FAIL item.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

The implementation inventory must include exactly these Assignment-owned persistent
Registry models:

1. `onehr.assignment` — ED2
2. `onehr.assignment.change.request` — ED3
3. `onehr.assignment.change.line` — ED3
4. `onehr.assignment.cost.allocation` — ED1
5. `onehr.workforce.plan` — ED2
6. `onehr.workforce.plan.line` — ED2
7. `onehr.position.budget` — ED1

`hr.version` is a shared/native reference, not re-owned. No replacement `onehr.employee`,
`onehr.job`, `onehr.department`, `onehr.location`, branch master, payroll object or
unregistered mass-move wizard may be invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Business areas remain separated into readable modules: assignment, costing, movement,
workforce, native extensions, action helpers and authority helpers. Files must favor
explicit business methods and named constants over compressed generic abstractions.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Transaction forms must provide meaningful statusbar/header actions, smart navigation,
well-labeled groups/notebooks, body operational actions and chatter. Buttons must
represent real business actions; decorative complexity is prohibited.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Each of the seven custom persistent models must have a documented UX purpose and the
appropriate list/form/search surface. Transaction/planning models additionally receive
statusbar, smart/body/row actions, analytical views only where business-useful.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every custom persistent Registry model must have an explicit search view with relevant
filters and group-by options. Relying only on Odoo default search generation is not
accepted.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Lists must expose operational decision columns, states/badges/decorations, company
context when useful, totals where meaningful and row actions where they reduce user
navigation. Generic tutorial list views fail this gate.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

UI visibility never substitutes for ACL, record rule or model-level authority checks.
No broad `base.group_user` CRUD is allowed. Unit-manager proposers see only governed
direct-report assignment history and own movement requests; Officer and Manager
powers remain explicit. Business methods must not use `sudo()` to bypass authorization.
Final approval routes must resolve to users with source-model authority required by the
workflow callback.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

Gate 11 is intentionally undefined because the user did not define one. No worker may
invent its meaning.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use clear model/field/action names, short business helpers, conventional Odoo patterns,
explicit state transitions and readable validation messages. Avoid metaprogramming or
clever compression that makes manual maintenance difficult.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments must explain ownership boundaries, effective-dating decisions, security,
history or non-obvious Odoo behavior. Comments that merely restate a field or line of
code are not a substitute for readable structure.

## HARD GATE 14 — CODEX RETRY LIMIT

Codex limits are mandatory:

- maximum attempts per bounded task: 2;
- maximum repeat of the same root cause: 1;
- no automatic retry after a repeated root cause;
- diagnose/classify before any retry.

Root-cause classes are: `HARNESS_FAILURE`, `ENVIRONMENT_FAILURE`,
`ODOO_VERSION_COMPATIBILITY_FAILURE`, `ADDON_SOURCE_FAILURE`, `TEST_DEFECT`,
`DATA/MIGRATION_FAILURE`, `ARCHITECTURE_CONFLICT`.

Harness/environment defects must not trigger addon source edits unless a separate,
reproducible addon source defect is proven.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

Move-forward readiness requires all applicable matrix rows PASS, including Registry,
dependencies, install/upgrade, security, primary/secondary placement, effective dating,
native HR sync, movement, costing, position capacity, workforce planning, reporting,
UI, historical immutability and regression evidence.

## Final release rule

`ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: YES` is legal only after source acceptance,
Windows/Odoo 19 fresh install/upgrade/runtime tests and the final Enterprise Completeness
Matrix all pass. Until then the correct status is `NO`.
