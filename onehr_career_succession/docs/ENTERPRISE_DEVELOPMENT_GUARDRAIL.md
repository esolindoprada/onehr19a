
# OneHR Career & Succession — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-CAREER-SUCCESSION-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_career_succession
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

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0
Verify OneHR project identity, `onehr_career_succession`, latest workspace,
approved 25-addon contract, root Guardrail, Odoo 19 CE target, exact write scope,
ownership/dependency boundaries and current runtime status before any source change.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker. It may implement the approved four-model
Career/Succession contract and proven compatibility repairs only. It may not decide
new canonical models, ownership, dependency direction, workflow redesign, security
weakening or feature deletion.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve competency dictionary, position competency requirements, behavioural evidence,
talent/high-potential classification, readiness, gap analysis, succession planning for
critical positions, Appraisal/Learning scoring hooks, coverage/risk/bench KPIs,
competency import, BI service boundary, audit and company isolation.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Static/source/install/test PASS does not prove enterprise completion. Runtime workflow,
security, reports, scheduler, soft integrations, fresh install, upgrade/idempotency,
exact Registry rows and manual UI/UAT remain independent acceptance gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Approved persistent business models are exactly:
- `onehr.competency`
- `onehr.position.competency`
- `onehr.talent.pool`
- `onehr.succession.plan`

No extra persistent/transient competency-assessment, successor-line, career-path,
talent-score, configuration or API-authentication table is invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
One business concern per readable Python/XML file. Authority helpers and soft integration
services are explicit. No opaque generated mega-model or hidden metaprogramming.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Lifecycle records use statusbars, header actions, smart buttons, body actions,
notebooks, badges/ribbons, chatter/activity and useful One2many/Many2many row actions.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model has a documented List/Form/Search contract and appropriate
analysis view.

## HARD GATE 8 — SEARCH VIEW WAJIB
Every persistent model has a dedicated Search view.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Operational lists expose business identity, readiness/risk/status evidence, optional
columns, decorations/badges and useful row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL/record rules/model methods remain authoritative. No broad custom-model CRUD for
`base.group_user`; no business `sudo()` bypass; company isolation cannot be weakened
to make UI or tests pass.

## HARD GATE 11
Intentionally undefined in the approved OneHR numbering. Do not invent it.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable methods/constants, Odoo 19 `<list>`, direct modifiers and `models.Constraint`.
No legacy `_sql_constraints`, `attrs`, `states`, or `@api.depends(...".id")`.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain architecture/security/integration reasons rather than obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded attempts for a proven source/runtime-repair task. Same root cause
may repeat once. Environment/harness failures never authorize arbitrary source mutation.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory. Source/runtime/Registry/integration
status remain separate and `MOVE_FORWARD_READY` remains NO until all applicable gates pass.

Runtime root-cause classes:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default write scope is `onehr_career_succession` only. Sibling addon source edits are
forbidden unless explicitly authorized.

