# OneHR Appraisal — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-APPRAISAL-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_appraisal
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
Verify project, addon, authoritative baseline, preserved scope, allowed write scope,
forbidden changes, dependency direction and current verified status before implementation.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex implements an already-approved contract or a proven bounded repair only.
It may not redesign canonical models, ownership, dependencies, security boundaries,
workflow architecture or functional scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve OKR/KPI cycles, target templates, weights/rating scales, self/manager/peer
multi-rater evidence, comments/attachments, consolidation, rating distribution,
acknowledgement, IDP/Learning hand-off, analytics, import/export and audit.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Syntax/static/source PASS does not prove Windows Odoo registry, access rules, QWeb,
cron, workflow, install/upgrade, data migration or cross-addon runtime behavior.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Approved Appraisal persistent business models are exactly:
- onehr.appraisal.cycle
- onehr.appraisal.form
- onehr.appraisal.score

No tutorial placeholder and no duplicate worker/competency/learning/talent business model.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
One business concern per readable Python/XML file. Small explicit authority helpers
and integration services. Avoid opaque metaprogramming and generated mega-files.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Lifecycle forms use statusbar, header actions, smart buttons, body actions, notebooks,
badges/ribbons, chatter/activity, KPI summaries and One2many row actions.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model has an explicit UI contract in UI_UX_MATRIX.md.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated search view exists for all three persistent models.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Each persistent model has an operational list view with useful fields, decorations,
badges, optional columns and row actions where useful.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL, record rules and model methods remain authoritative. UI visibility is not security.
No broad base.group_user CRUD. No business sudo bypass.

## HARD GATE 11
Intentionally undefined in the approved OneHR gate numbering. Do not invent it.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable constants/actions, Odoo 19 `<list>`, direct modifiers and models.Constraint.
No legacy _sql_constraints, attrs or states modifiers.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership/security/integration rationale, not obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded attempts for a proven source task; same root cause may repeat once.
Harness/environment failures do not authorize source mutation.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
ENTERPRISE_COMPLETENESS_MATRIX.md is mandatory. Source/runtime/registry/integration
status remain separate. Pending runtime evidence keeps MOVE_FORWARD_READY = NO.

Runtime root-cause classes:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default write scope is this addon only. Sibling source edits are forbidden without
explicit separate authorization.
