# OneHR Learning — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-LEARNING-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_learning
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
MOVE_FORWARD_REQUIRES_ALL_APPLICABLE_HARD_GATES: TRUE

## HARD GATE 0 — PROJECT IDENTITY PREFLIGHT
Before any edit, verify PROJECT, ADDON, AUTHORITATIVE BASELINE,
PRESERVATION RULE, ALLOWED CHANGE, FORBIDDEN CHANGE and CURRENT VERIFIED STATUS.
A failed preflight blocks implementation.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex may implement an already-approved contract or one proven runtime repair only.
It may not choose model ownership, dependencies, security boundaries, workflow
architecture, feature deletion, simplification, or replacement strategy.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve the approved L&D scope: catalog/curriculum/prerequisites; sessions;
capacity/waitlist; internal/external trainer; enrollment approval; reminders;
training attendance; pre/post assessment; reaction evaluation; pass/fail;
certificate lifecycle/expiry; vendor; budget/cost; import/export; analytics hooks;
and approved soft integrations.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Python/XML/static PASS is source evidence only. It never proves Windows Odoo runtime,
access rules, workflow behavior, PDF rendering, cron behavior or end-to-end integration.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
The addon owns exactly these eight product-baseline persistent business models:
onehr.learning.course, onehr.learning.session, onehr.learning.enrollment,
onehr.learning.attendance, onehr.learning.certificate, onehr.learning.vendor,
onehr.learning.budget, onehr.learning.cost.line.
No tutorial placeholder or unapproved business table is allowed.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
One business concern per readable Python/XML file. Reusable authority/action helpers
are small and explicit. Business actions use meaningful names and short methods.
No generated mega-file is accepted.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Operational forms use statusbars where lifecycle exists, smart buttons, notebooks,
body actions, chatter/activity, badges/ribbons, clear grouping and evidence fields.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every model has an explicit UI contract documented in UI_UX_MATRIX.md.

## HARD GATE 8 — SEARCH VIEW WAJIB
Every one of the eight persistent models must have a dedicated search view with
useful filters/group-by behavior.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Every persistent model must have an operational list view with useful columns,
optional columns, state badges/decorations and row actions where appropriate.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
Buttons never grant authority. ACL, record rules and model methods remain authoritative.
No broad custom-model CRUD for base.group_user. No business sudo bypass.

## HARD GATE 11
Intentionally undefined in the approved OneHR 15-gate numbering. Do not invent a gate.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable constants, business names, normal Python formatting, explicit validation,
Odoo 19 models.Constraint, and no legacy _sql_constraints.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership/security/integration rationale, not obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded attempts per proven source task; same root cause may repeat once.
A second failure requires new evidence or STOP/classification, not endless retries.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
The matrix in ENTERPRISE_COMPLETENESS_MATRIX.md is mandatory. Source/static/runtime/
integration/registry status are reported separately. Any pending applicable runtime
gate keeps MOVE_FORWARD_READY = NO.

## Runtime root-cause classes
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

## Write scope
Default write scope is this addon only. Sibling OneHR sources are read/integration
references and may not be modified without explicit separate authorization.
