
# OneHR SOP — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-SOP-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_sop
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
Verify OneHR NEW, addon `onehr_sop`, Odoo 19 CE, latest workspace snapshot,
approved 25-addon product contract, root Guardrail, exact target write scope,
dependency direction, current upstream contracts and runtime status before source work.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker only. It may implement the approved
`onehr.sop`, `onehr.sop.version`, `onehr.sop.ack` contract or repair a proven
runtime defect. It may not redesign ownership, add/remove core models, promote
soft dependencies, weaken security, delete enterprise requirements or simplify
functionality merely to obtain a green test.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
The supplied `onehr_sop` is a generic Odoo tutorial scaffold, not an accepted
SOP business implementation. Direct Full replacement must preserve the approved
product contract: versioning, targeted unit/role publication, Read & Agree,
retention/review reminders, compliance reporting, acknowledgement export,
Document archive integration and Portal/Analytics/API hooks.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
AST/XML/static/tests are evidence, not completion. Fresh install, workflow UAT,
audience security, acknowledgement UAT, Document archive issuance, QWeb reports,
cron/reminders, CSV export, downstream services, upgrade/idempotency and exact
Registry ED rows remain separate runtime gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Persistent SOP business models are exactly:
- `onehr.sop`
- `onehr.sop.version`
- `onehr.sop.ack`

No extra persistent SOP template, audience, line, compliance snapshot, import,
API, portal or notification model may be invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Use concern-based files: authority helpers, SOP master, version/workflow,
acknowledgement evidence, integration services, security, views, reports, tests,
acceptance tooling and documentation. Avoid opaque metaprogramming and generated
mega-files so manual maintenance remains practical.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Where meaningful use statusbars, lifecycle actions, smart buttons, body buttons,
One2many row actions, badges/ribbons, KPI blocks, chatter/activity, review calendar,
Kanban, Pivot/Graph, audit export and report actions. UI never replaces server
authorization.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model must have documented List/Form/Search coverage and suitable
enterprise analysis/navigation according to its role.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated Search views are mandatory for all three persistent SOP models.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists expose meaningful business identity, lifecycle/compliance state, audience/
employee context, effective/review dates, acknowledgements and governed row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL, global company rules, publication-audience record rules and Python method guards
are authoritative. No broad custom `base.group_user` CRUD, no business `.sudo()`,
no public controller, no direct acknowledgement rewrite, and no published-history
deletion.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
Database/ORM naming is a release gate:
- PostgreSQL identifiers are treated as max 63 UTF-8 bytes.
- canonical tables must be `onehr_sop`, `onehr_sop_version`, `onehr_sop_ack`.
- model names use lowercase dotted Odoo naming.
- field names use lowercase snake_case and remain <=63 bytes.
- indexed-field predicted identifiers are checked for safe length.
- explicit Many2many relation tables/columns are unique, snake_case and <=63 bytes.
- constraint attribute/database-name projections must remain deterministic and safe.
- local XML IDs must be unique.
- no static ORM relation to soft OneHR modules.
- no forbidden `id` or `.id` dependency in `@api.depends`.
- no legacy `_sql_constraints`; use Odoo 19 `models.Constraint`.
- no accidental relation-table collision or identifier truncation ambiguity.

Any failure is `ADDON_SOURCE_FAILURE` and blocks runtime acceptance.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable method names, explicit constants, compact helpers, Odoo 19 `<list>`,
direct modifiers, `models.Constraint`, `Command` for relational operations and
clear model-service boundaries. No legacy `attrs`/`states`.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership, security, evidence retention, audience publication,
Document integration and soft dependency reasons; they do not narrate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded implementation/repair attempts for one proven runtime defect.
The same root cause may repeat once. Classify first; environment/harness failure
does not authorize random source mutation or endless retry.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory. Source, runtime, security,
integration, reporting, scheduler, upgrade and Registry status remain separate.
Move-forward remains NO until all applicable rows PASS.

Runtime root-cause classification:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default source write scope is `onehr_sop` only. Sibling OneHR source modifications
require separate architecture authorization.

