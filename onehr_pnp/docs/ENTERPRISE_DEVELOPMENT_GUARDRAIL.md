
# OneHR PnP — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-PNP-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_pnp
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
Verify project OneHR NEW, exact target addon `onehr_pnp`, Odoo 19 CE,
latest supplied workspace, root OneHR Guardrail, approved PnP product contract,
hard dependency ownership, upstream service contracts, write scope and runtime
status before source work.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker only. It may implement the approved
PnP models/capabilities and make evidence-driven Odoo 19 compatibility repairs.
It may not redesign model ownership, dependency topology, security ownership,
workflow ownership, history semantics or product scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
The latest target source is still a tutorial scaffold, but its supplied Apps
description is a product contract and must be preserved: policy version/change
history, approval, targeted publication, acknowledgement, evidence, periodic
review, notifications, reports, multi-company, Portal and Analytics integration.
Because `onehr_sop` now owns operational SOP records, PnP must not duplicate SOP
models; soft SOP references preserve suite integration without ownership conflict.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Syntax/static/test inventory is not enterprise completion. Fresh install,
Workflow Approval routing, Document archive issuance, publication, employee
acknowledgement, employee/unit/policy evidence, schedulers, mail queues, QWeb,
security UAT, multi-company, downstream services and repeated upgrade/idempotency
remain separate runtime gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Persistent PnP business models are exactly:
- `onehr.policy`
- `onehr.policy.ack`
- `onehr.policy.evidence`

`res.config.settings` is extended only as the approved transient settings surface.
No fourth persistent policy-version/category/audience/evidence-line model is invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Separate files by concern: authority helpers, settings, policy governance,
acknowledgement evidence, compliance evidence, integration services, security,
data, views, reports, tests, acceptance tooling and documentation. Avoid opaque
metaprogramming and generated mega-files.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Use enterprise statusbars, governed header actions, smart buttons, body actions,
One2many row actions, badges/ribbons, KPI blocks, chatter/activity, Kanban,
Calendar, Pivot/Graph, reports and Settings surfaces where useful. UI visibility
never replaces server authorization.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model must have documented enterprise List/Form/Search coverage
plus role-appropriate analysis/navigation.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated Search views are mandatory for all three PnP persistent models.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists expose business identity, controlled version/state, audience/employee/unit,
compliance status, effective/review/due dates and governed row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACLs, global company rules, assignment/evidence record rules and Python method
guards are authoritative. No broad custom `base.group_user` CRUD, no business
`.sudo()`, no public controller, no direct lifecycle/evidence rewrite, and no
deletion of governed acknowledgement/submitted evidence.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
Release-blocking checks:
- PostgreSQL identifier ceiling treated as 63 UTF-8 bytes.
- Canonical tables: `onehr_policy`, `onehr_policy_ack`,
  `onehr_policy_evidence`.
- model names lowercase dotted; fields lowercase snake_case.
- explicit Many2many table/column names are unique and <=63 bytes.
- projected index/constraint identifiers are checked before runtime.
- local XML IDs are unique.
- no accidental relation-table collision.
- no static ORM relation to soft modules such as SOP/Portal/Analytics/Branch/API.
- no `id` or `.id` dependency in `@api.depends`.
- no legacy `_sql_constraints`; use Odoo 19 `models.Constraint`.

Any failure is `ADDON_SOURCE_FAILURE` and blocks runtime.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable methods, explicit action-context guards, Odoo 19 `<list>`, direct
`readonly`/`invisible` modifiers, `Command` relational writes, descriptive field
names and narrow integration hooks.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain model ownership, approval ownership, security boundaries,
evidence retention, soft integration and history decisions—not obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded source attempts for one proven runtime/source defect.
The same root cause may repeat at most once. Classify root cause first.
HARNESS/ENVIRONMENT failures do not authorize business-source mutation.
Attempt 2 failure requires STOP and reviewer/architecture decision.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory and keeps source/runtime/
security/integration/reporting/scheduler/upgrade/Registry gates separate.
Move-forward remains NO until every applicable gate passes.

Runtime root-cause classes:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default write scope is `onehr_pnp` only. Sibling OneHR source changes require a
separate approved architecture/change contract.

