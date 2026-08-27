# OneHR Enterprise Development Guardrail — Employment Contract Direct Full Build

GUARDRAIL_ID: ONEHR-EDG-V8-EMPLOYMENT-CONTRACT-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_employment_contract
TARGET_PLATFORM: Odoo 19 Community Edition
DELIVERY_METHOD: DIRECT_FULL_ADDON_BUILD
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
Before work: PROJECT, ADDON, AUTHORITATIVE BASELINE, PRESERVATION RULE, ALLOWED CHANGE,
FORBIDDEN CHANGE and CURRENT VERIFIED STATUS must be explicit. Any ambiguity stops work.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex may only implement/repair a bounded, already-approved design. It cannot redesign,
simplify, delete, move ownership, alter dependencies or retry indefinitely.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve approved contract lifecycle, template history, effective dates, probation,
expiry reminders, approval, renewal, termination, clearance, document hooks, security,
audit and native hr.version ownership. Unexplained loss is a hard fail.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Syntax/install/test PASS does not prove enterprise completeness. Functional workflow,
security, history, integrations, reports, runtime and upgrade evidence are separate gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Inventory models, fields, methods, views, actions, menus, groups, ACLs, rules, data,
cron, tests and integration hooks before move-forward.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Split code by business responsibility; use small explicit helpers and readable action
methods. Avoid registry magic, giant files and unnecessary indirection.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Forms must show business lifecycle and context with header actions/statusbar, smart
buttons, logical groups/notebooks, operational body actions and chatter where useful.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every user-facing model must have an explicit UI/UX decision matrix and security mapping.

## HARD GATE 8 — SEARCH VIEW WAJIB
Every user-facing persistent custom model requires a useful search view with relevant
filters/grouping.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists must expose decision-driving columns, state badges/decorations and useful row
navigation/actions rather than generic name/value scaffolds.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
UI invisibility is not authorization. High-impact actions require server-side group/ACL/
record-rule enforcement. Never solve access failures with broad base.group_user CRUD.

## HARD GATE 11 — INTENTIONALLY UNDEFINED
No Gate 11 is invented. It remains undefined unless explicitly defined by the user.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable names, bounded methods, ordinary ORM, explicit constants and simple domains.
No needless cleverness.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership, invariants, evidence/history and compatibility reasons; they
do not narrate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
MAX_CODEX_ATTEMPTS_PER_TASK=2; MAX_REPEAT_OF_SAME_ROOT_CAUSE=1. Classify failure first:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE or ARCHITECTURE_CONFLICT.
No source edit for harness/environment failure without separate proof of source defect.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
Move-forward requires no applicable PENDING/FAIL in architecture, preservation, source,
runtime, tests, security, temporal/history, upgrade/idempotency, uninstall/reinstall,
integration contract and functional completeness evidence.

## Employment Contract ownership hard rules
- `hr.version` is canonical for live contract/employment facts.
- `onehr.contract` is legal/workflow/evidence wrapper.
- `onehr.contract.template` is versioned/effective policy.
- Hard dependencies remain exactly onehr_corehr, onehr_security, onehr_workflow_approval.
- onehr_document and onehr_payroll_bridge stay soft.
- No sibling addon may be edited by a repair unless separately authorized.

END_GUARDRAIL: ONEHR-EDG-V8-EMPLOYMENT-CONTRACT-DIRECT-FULL
