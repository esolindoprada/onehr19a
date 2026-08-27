# OneHR Time Off — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-TIMEOFF-DIRECT-FULL-V1
STATUS: APPROVED_HARD_GATE_FOR_SOURCE_BUILD
PROJECT: OneHR NEW
ADDON: onehr_timeoff
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

This Guardrail is mandatory for design, implementation, runtime remediation, upgrade, migration and acceptance of `onehr_timeoff`. It is a HARD GATE, not advisory guidance. No implementation worker may delete or simplify approved enterprise functionality merely to obtain an install/test PASS.

## Architecture authority

The authority order is:

1. OneHR Enterprise Architecture v2.
2. OneHR Master Model Registry v1.
3. Approved OneHR 25-addon topology and ownership.
4. Odoo 19 CE native-model ownership where the architecture designates it canonical.
5. Current accepted contracts of `onehr_corehr`, `onehr_security`, and `onehr_workflow_approval`.
6. OneHR 25 Addons Specification and Oracle HRMS benchmark where compatible with the frozen Registry.

A conflict is an architecture conflict. Codex must STOP; it may not invent a model, owner, dependency or simplification to escape it.

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

Before editing or repairing, verify:

- PROJECT: OneHR NEW.
- ADDON: `onehr_timeoff`.
- AUTHORITATIVE BASELINE: Architecture v2 + Registry v1 + approved topology + latest accepted sibling contracts + latest user source export + OneHR Time Off product baseline + Oracle HRMS blueprint.
- PRESERVATION RULE: preserve leave policy, request, allocation, accrual, carry-over, team calendar, workflow, entitlement evidence, security and soft integration boundaries.
- ALLOWED CHANGE: full replacement of obsolete tutorial scaffold; Odoo 19 compatibility; enterprise UI/security/tests/docs.
- FORBIDDEN CHANGE: new unapproved model ownership, duplicate HR masters, reverse Attendance/Payroll dependency, security weakening, history deletion, business `sudo()` bypass.
- CURRENT VERIFIED STATUS: source/static and Windows runtime status must always be reported separately.

Failure of any identity item blocks implementation.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is a bounded implementation worker only. It may implement the approved contract or correct a proven defect inside that contract. It may not redesign model ownership, dependency direction, security boundaries, approval ownership, enterprise scope or effective-dating policy.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Non-negotiable capabilities:

- annual/sick/special/training leave intent;
- effective leave policy history;
- grade/tenure eligibility;
- automatic accrual and carry-over with caps;
- opening balances and HR adjustments;
- team calendar/conflict governance;
- employee self-service, manager team scope, HR administration;
- Workflow Approval integration;
- entitlement validation and frozen reservation evidence;
- paid/unpaid downstream payroll hook;
- Attendance soft validation hook;
- balance/utilization/approval-lead analytics;
- professional List/Form/Search/Calendar/Pivot/Graph UI;
- immutable governed history.

A capability is never removed because runtime repair is difficult.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax PASS, XML PASS, install PASS, upgrade PASS and unit-test PASS are evidence only. Enterprise completion additionally requires functional workflows, accrual/carry-over correctness, balance integrity, approval ownership, security, history, analytics, integration contracts, UI quality and registry alignment.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

The explicit Time Off product baseline names exactly three custom core business models:

1. `onehr.leave.type`
2. `onehr.leave.request`
3. `onehr.leave.allocation`

No extra balance/accrual/carry-over/mass-wizard business model is created without an approved Registry row. `hr.employee` is inherited narrowly and remains Odoo/Core HR owned.

Exact ED-number labels must be verified against the authoritative Registry before final freeze; absent labels must never be guessed.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Policy, request, allocation, native extension, authority helpers and action helpers remain separate readable modules. Business methods are explicit and named by purpose. No metaprogramming, opaque generic engine or compressed cleverness may replace readable HR rules.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Forms must expose real business workflow, not decorative buttons. Required where relevant:

- statusbar and meaningful header actions;
- smart navigation/count buttons;
- body operational review actions;
- notebook sections grouped by business purpose;
- One2many row actions on durable mass-allocation children;
- chatter/activity evidence.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every custom persistent model requires a documented role/persona, List, Form and Search surface. Request additionally uses Calendar/Pivot/Graph; Allocation uses Pivot/Graph. See `UI_UX_MATRIX.md`.

## HARD GATE 8 — SEARCH VIEW WAJIB

Explicit Search view is mandatory for all three custom models. Required filters/group-by must address state, leave type/category, company, dates/periods, source and operational queues as applicable.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

List views must show decision-making columns, status badges/decorations, totals where meaningful, company context and row actions where they reduce navigation. Tutorial/basic lists fail this gate.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

Button invisibility never substitutes for ACL, record rules or business-method authority checks.

- No broad `base.group_user` custom CRUD.
- Employee self-service is own-record only.
- Manager scope is own + direct reports/team only.
- HR is allowed-company scoped.
- Time Off Manager does not receive broad Core HR private-data authority merely to render a form.
- Normal RPC writes cannot mutate lifecycle/evidence fields; private server-side transition writers are used only by governed business actions.
- No business `sudo()` is used to make access errors disappear.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

The user's Hard Gate list does not define Gate 11. No implementation worker may invent its meaning.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use readable names, conventional Odoo patterns, short helpers, explicit validations and clear error messages. Prefer visible deterministic policy fields over JSON formulas or executable expressions. The code must remain practical for manual maintenance.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments/docstrings explain ownership boundaries, historical immutability, soft integration, idempotency, effective dating or non-obvious Odoo behavior. Comments that merely restate a line do not satisfy the gate.

## HARD GATE 14 — CODEX RETRY LIMIT

- Maximum attempts per bounded repair task: 2.
- Maximum repeat of the same root cause: 1.
- Attempt 2 is allowed only with new evidence of a distinct or incompletely resolved defect.
- No autonomous third attempt.

Classify failures before edits:

- `HARNESS_FAILURE`
- `ENVIRONMENT_FAILURE`
- `ODOO_VERSION_COMPATIBILITY_FAILURE`
- `ADDON_SOURCE_FAILURE`
- `TEST_DEFECT`
- `DATA/MIGRATION_FAILURE`
- `ARCHITECTURE_CONFLICT`

Required STOP markers include:

- `STOP_REASON: ARCHITECTURE_DECISION_REQUIRED`
- `STOP_REASON: BASELINE_MISSING`
- `STOP_REASON: OWNERSHIP_CONFLICT`
- `STOP_REASON: REPEATED_ROOT_CAUSE`
- `STOP_REASON: DESTRUCTIVE_CHANGE_NOT_APPROVED`
- `STOP_REASON: OUT_OF_SCOPE_CHANGE_REQUIRED`
- `STOP_REASON: MAX_ATTEMPTS_REACHED`

Harness/environment failure does not authorize business-source modification unless a separate source defect is proven.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

`ONEHR_TIMEOFF_MOVE_FORWARD_READY: YES` is legal only when all applicable matrix rows pass, including:

- architecture/registry alignment;
- preservation;
- exact dependencies;
- source/static acceptance;
- fresh install;
- 20 runtime tests;
- first + repeat upgrade;
- self/manager/HR security;
- accrual/carry-over/idempotency;
- balance reservation/cancellation;
- approval/rejection/reset/completion;
- team conflict/calendar;
- mass allocation;
- paid/unpaid/Attendance soft integration;
- UI/reporting;
- cross-addon regression;
- complete evidence.

Until then:

`ONEHR_TIMEOFF_MOVE_FORWARD_READY: NO`

## Codex bounded implementation contract

Every future Codex prompt touching this addon must state at minimum:

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MAX_ATTEMPTS = 2
TARGET_ADDON = onehr_timeoff
WRITE_SCOPE = onehr_timeoff only unless separately approved
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

END_GUARDRAIL: ONEHR-EDG-TIMEOFF-DIRECT-FULL-V1
