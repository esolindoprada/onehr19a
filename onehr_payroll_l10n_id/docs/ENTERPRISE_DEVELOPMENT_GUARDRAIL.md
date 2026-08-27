# OneHR Payroll Localization Indonesia — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-PAYROLL-L10N-ID-DIRECT-FULL
STATUS: APPROVED_HARD_GATE_FOR_BUILD
PROJECT: OneHR NEW
ADDON: onehr_payroll_l10n_id
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

Project, exact addon, authoritative baseline, preservation rule, allowed/forbidden change and
verified source status are recorded in `PROJECT_IDENTITY_PREFLIGHT.md`. Ambiguity blocks work.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex only implements the approved one-model localization contract or a proven bounded repair.
It cannot decide new models, payroll-engine ownership, employee tax identity, dependency
direction, legal policy, public API ownership or accounting ownership.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Preserve all product baseline responsibilities: PPh21/PTKP/gross-gross-up parameters, BPJS
Kesehatan/Ketenagakerjaan, THR prorata/calendar, parameter history, JSON/CSV interchange,
Payroll Bridge hook, manager security and company isolation.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax/XML/source/runtime-test PASS does not prove statutory or enterprise completion.
Final acceptance separately requires exact Registry ED review, Windows install/upgrade,
security UAT, effective-date/history UAT, current-regulation review, bridge-generation
roundtrip and cross-addon regression.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Exactly one custom persistent model: `onehr.payroll.l10n.param`.
No custom transient model is added. Payroll Bridge extensions use `_inherit` only.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Business configuration, bridge extension, regulatory defaults and UI helpers live in separate,
explicitly named files. Regulatory tables are readable JSON defaults, not opaque metaprogramming.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Form uses effective-dated identity, regulatory evidence, PPh21/PTKP/TER/BPJS/THR notebooks,
smart buttons, meaningful body actions, governed history/import, One2many row navigation,
effective-period ribbons and chatter.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Documented in `UI_UX_MATRIX.md`. Existing Payroll Bridge surfaces are extended without redesign.

## HARD GATE 8 — SEARCH VIEW WAJIB

The one custom persistent model has an explicit Search view with current/future/historical,
review-required/review-due, date and group-by controls.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

List exposes effective dates, revision, review evidence, tax method, BPJS/THR status, JP ceiling,
company, hash and useful Validate/History row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

No `base.group_user` CRUD, no business `sudo()`, explicit company rule, Manager mutation
authority, Officer read-only integration access, model-level immutable history, no secret fields.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

The user-defined list does not define Gate 11. No implementation worker may invent it.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Explicit field names, constants, small parsing/validation helpers, readable exceptions and
conventional Odoo ORM patterns are mandatory.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain legal/effective-date boundaries, one-model Registry choice, historical hash
semantics and downstream payroll-engine ownership. Comments do not merely narrate syntax.

## HARD GATE 14 — CODEX RETRY LIMIT

Maximum two bounded attempts per task; the same root cause may not be repeated more than once.
A new failure must be classified before repair. Harness/environment failure does not authorize
source mutation.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

Every applicable row in `ENTERPRISE_COMPLETENESS_MATRIX.md` must PASS before move-forward.

Until runtime/Registry/regulatory evidence is complete:

`ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: NO`
