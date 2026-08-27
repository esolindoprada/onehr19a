# OneHR Discipline — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-DISCIPLINE-DIRECT-FULL  
STATUS: APPROVED_HARD_GATE  
PROJECT: OneHR NEW  
ADDON: onehr_discipline  
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
Verify OneHR NEW identity, Odoo 19 CE target, exact addon `onehr_discipline`,
latest supplied workspace, root OneHR Guardrail, authoritative 25-addon product
specification, current upstream contracts, exact write scope and runtime status.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker. It may implement the approved Discipline
contract and bounded compatibility repairs only after a proven source/runtime root
cause. It may not redesign model ownership, dependency topology, security authority,
approval ownership, payroll/contract ownership or suite architecture.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
The latest executable target is still the generic Odoo tutorial scaffold, so there is
no accepted business source to preserve line-by-line. The supplied scaffold description
does contain valuable product intent: violation classification, pipeline/SLA,
investigation, hearing, sanctions, appeal, letters, notifications, privacy and audit.

The authoritative 25-addon specification, however, declares exactly two persistent
Discipline business models: `onehr.discipline.case` and
`onehr.discipline.sanction`. Therefore the richer legacy intent is preserved inside
those two approved models rather than by inventing six extra persistent models.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Static/source/test inventory PASS does not mean the addon is enterprise-complete.
Fresh install, Workflow Approval routing, strict-access UAT, mail queue, QWeb,
cron idempotency, optional integration services, repeated upgrade, migration,
physical identifier inspection and Registry verification are separate gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Persistent Discipline business models are exactly:
- `onehr.discipline.case`
- `onehr.discipline.sanction`

`res.config.settings` is extended only as the approved transient configuration
surface. No persistent policy, violation, case-stage, investigation, hearing,
appeal or integration-shadow model is invented.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Separate files by concern: authority helpers, settings, case governance, sanction
approval/execution, integration services, security, data, views, reports, tests,
source acceptance and documentation. Avoid generated mega-files and obscure
metaprogramming.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Use enterprise statusbars, header actions, smart buttons, body actions, One2many
row actions, badges, ribbons, chatter/activity, Kanban, Calendar, Pivot/Graph,
QWeb and settings when useful. UI visibility never replaces server authorization.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model must have documented enterprise List/Form/Search coverage
plus appropriate analytical and navigation surfaces.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated Search views are mandatory for both persistent Discipline models.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists must expose business identity, employee-safe display, violation/sanction
classification, workflow state, SLA/effective dates, appeal/execution status and
governed row actions.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL, global company rules, assignment-scoped record rules and Python guards are
authoritative. No broad `base.group_user` CRUD, no public controller, no business
`.sudo()`, no spoofable lifecycle-context bypass and no direct lifecycle rewrite.
Investigators are assignment-scoped; HRBP is assignment-scoped; Manager/Legal
are company-scoped. Approval routing remains owned by Workflow Approval.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
Release-blocking checks:
- PostgreSQL identifier ceiling treated as 63 UTF-8 bytes.
- Canonical tables: `onehr_discipline_case`,
  `onehr_discipline_sanction`.
- lowercase dotted model names and lowercase snake_case fields.
- explicit Many2many relation/column names are unique and <=63 bytes.
- projected index and constraint identifiers are checked.
- local XML IDs are unique.
- no relation-table collision.
- no static ORM relation to soft modules.
- no `id` / `.id` dependency in `@api.depends`.
- no legacy `_sql_constraints`; use `models.Constraint`.

Any failure is `ADDON_SOURCE_FAILURE` and blocks runtime.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Use descriptive names, focused action methods, explicit authority helpers,
Odoo 19 `<list>`, direct modifiers, `Command` relational operations in tests/data,
small integration services and readable comments.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership boundaries, fair-process evidence, strict security,
approval execution, soft integrations, retention and why legacy concepts are
embedded rather than obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded source repair attempts for one proven defect. The same root
cause may repeat at most once. Classify the first complete traceback before
mutation. Harness/environment failures do not authorize business-source edits.
Attempt 2 failure requires STOP and reviewer/architecture decision.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory and separates source/static,
runtime, security, approval, reporting, scheduler, integration, upgrade and
Registry evidence. Move-forward remains NO until every applicable gate passes.

Runtime root-cause classes:
`HARNESS_FAILURE`, `ENVIRONMENT_FAILURE`,
`ODOO_VERSION_COMPATIBILITY_FAILURE`, `ADDON_SOURCE_FAILURE`,
`TEST_DEFECT`, `DATA/MIGRATION_FAILURE`, `ARCHITECTURE_CONFLICT`.

Default write scope is `onehr_discipline` only. Sibling OneHR source changes
require a separate approved change contract.
