# OneHR Attendance — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V10-ATTENDANCE-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_attendance
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

This Guardrail governs design, implementation, remediation, upgrade and acceptance of `onehr_attendance`. It is mandatory, not advisory.

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

Before any source change verify PROJECT, ADDON, AUTHORITATIVE BASELINE, PRESERVATION RULE, ALLOWED CHANGE, FORBIDDEN CHANGE and CURRENT VERIFIED STATUS. Any ambiguity blocks implementation.

For this addon the frozen identity is documented in `PROJECT_IDENTITY_PREFLIGHT.md`. Hard dependencies are exactly `onehr_corehr`, `onehr_security`, `hr_attendance`.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is a bounded implementation worker only. It may inspect the exact failing artifact, implement an already-approved contract or repair one proven source defect. It may not redesign model ownership, dependencies, security, workflow, effective dating, UI scope or enterprise completeness.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Preserve canonical Odoo attendance/overtime ownership and all approved enterprise capabilities: shifts, schedules, rotation, late/early/missing-punch detection, import, reconciliation, device/API contract, reports, security, audit and downstream soft integrations. A failing test is never permission to delete or reduce capability.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax PASS, XML PASS, install PASS, upgrade PASS and unit-test PASS are necessary but not sufficient. Enterprise completeness also requires the functional matrix, security, UI, history/evidence, reporting, integration boundaries and runtime UAT.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

`FULL_STRUCTURAL_INVENTORY.md` must match the delivered source tree. Unreviewed hidden models, controllers, duplicate owners or backup artifacts are not allowed.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Domain code is split by responsibility (`shift.py`, `attendance.py`, `exception.py`, `import_reconciliation.py`, `native_overtime.py`). Business methods have meaningful names; helper code is small and predictable; manual editing must remain practical.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Primary transactional/master forms must use enterprise layout where meaningful: statusbar, action buttons, smart buttons, body actions, notebooks, ribbons, chatter and clear evidence sections. UI decoration must never replace server-side authority.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every user-facing model/native extension must be evaluated against `UI_UX_MATRIX.md`. Buttons are added only when they perform a real business action or drill-down.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every persistent custom user-facing model must have an explicit search view. Canonical Attendance and native overtime operational surfaces also receive dedicated OneHR search views.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Operational lists must show decision-relevant columns, badges/decorations and useful row actions. A list containing only name/value placeholder fields fails this gate.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

ACL, record rules, company integrity and business-method authority are mandatory. Invisible/read-only expressions are UX controls only. No `sudo()` business bypass or broad `base.group_user` custom CRUD is allowed.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

The user did not define Hard Gate 11. It is intentionally left undefined and must not be invented by ChatGPT, Codex or any implementation worker.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use descriptive field/method names, bounded methods, explicit state/evidence context keys, short helper functions, consistent sectioning and no unnecessary metaprogramming.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments/docstrings explain ownership boundaries, safety decisions, Odoo-native contracts and non-obvious business logic. Comments must not narrate trivial syntax or preserve dead scaffold code.

## HARD GATE 14 — CODEX RETRY LIMIT

Maximum Codex attempts per task: **2**. Maximum repetition of the same root cause: **1**. Before any second attempt classify the first failure as one of:

- HARNESS_FAILURE
- ENVIRONMENT_FAILURE
- ODOO_VERSION_COMPATIBILITY_FAILURE
- ADDON_SOURCE_FAILURE
- TEST_DEFECT
- DATA/MIGRATION_FAILURE
- ARCHITECTURE_CONFLICT

Harness/environment failures do not authorize addon-source modification. Architecture conflicts stop implementation. Codex is never an endless retry engine.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory. `ONEHR_ATTENDANCE_MOVE_FORWARD_READY` can become YES only when every applicable source/runtime/completeness item has objective PASS evidence.

## Explicit prohibitions

- No `onehr.attendance` duplicate.
- No replacement of Odoo 19 overtime line/rule/ruleset calculation ownership.
- No reverse hard dependency on Assignment, Time Off, Learning, Mobile Kiosk, Payroll, Analytics, Branch or Integrations API.
- No security weakening to make a view/test work.
- No legacy `_sql_constraints`; use Odoo 19 constraint mechanisms.
- No deletion of runtime tests to obtain PASS.
- No claim of FINAL/FROZEN from static evidence alone.
