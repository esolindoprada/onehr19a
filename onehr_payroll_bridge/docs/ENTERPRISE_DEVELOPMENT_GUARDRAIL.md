# OneHR Payroll Bridge — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-PAYROLL-BRIDGE-DIRECT-FULL
STATUS: APPROVED_HARD_GATE_FOR_BUILD
PROJECT: OneHR NEW
ADDON: onehr_payroll_bridge
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

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

Project, addon, baseline, preservation rule, allowed change, forbidden change and current
verified status are recorded in `PROJECT_IDENTITY_PREFLIGHT.md`. Failure blocks work.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is an implementation worker only. It cannot redesign payroll ownership, add an
engine, invent Registry models, change hard dependencies, own tax/accounting/API
credentials or reduce enterprise scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Preserve the product-specified three-model Payroll Bridge contract, Draft → Posted to
Payroll → Reconciled lifecycle, work-variable export, vendor payslip-result import,
mapping, reconciliation, costing output, audit evidence and current sibling boundaries.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax/XML/source/test PASS is only evidence. Completion separately requires runtime
install/upgrade, workflow UAT, security, cross-addon integration, reconciliation,
history/revision integrity and the final completeness matrix.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Exactly three product-approved custom persistent models:

1. `onehr.payroll.bridge.config`
2. `onehr.payroll.export`
3. `onehr.payroll.import`

No fourth staging/line/payslip/accounting/API model is invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Configuration, export workflow, import/revision workflow, action helpers and authority
helpers are separate readable files. Business helpers are named after payroll concepts;
no compressed metaprogramming is used.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Forms use meaningful lifecycle headers, smart navigation, body operational actions,
grouped business sections, notebooks, immutable evidence and chatter. Decorative buttons
without business purpose are prohibited.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every custom model is mapped in `UI_UX_MATRIX.md`; analytical views are used only where
operationally useful.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every custom persistent model has an explicit search view with meaningful filters and
group-by options.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Lists expose payroll period, employee/vendor reference, reconciliation metrics, monetary
totals, state badges/decorations and useful row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

ACL/rules/model authority are mandatory. No broad `base.group_user` CRUD; no sensitive
Core HR role is implied; no business `sudo()` bypass; state/evidence writes are governed.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

The user did not define Gate 11. No implementation worker may invent its meaning.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use explicit constants, readable field/action names, short business helpers, conventional
Odoo patterns and actionable validation errors suitable for manual maintenance.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain ownership boundaries, historical immutability, soft integration,
transport limits and non-obvious compatibility/security decisions rather than restating code.

## HARD GATE 14 — CODEX RETRY LIMIT

Maximum two bounded attempts per task and maximum one repeat of the same root cause.
Classify failures before repair. Harness/environment errors do not authorize source edits.
After attempt 2, STOP and report evidence.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

Move-forward requires every applicable row in `ENTERPRISE_COMPLETENESS_MATRIX.md` to
PASS, including Registry, dependencies, fresh install, repeat upgrade, security,
workflow, CSV round-trip, reconciliation, history/revision, cross-addon integration and
post-upgrade smoke.

## Final rule

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: YES` is legal only after all required runtime
and Registry evidence is complete.

Until then:

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: NO`
