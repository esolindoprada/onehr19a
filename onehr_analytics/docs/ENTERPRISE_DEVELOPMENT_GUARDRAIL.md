# OneHR Analytics — Enterprise Development Guardrail

GUARDRAIL_ID: `ONEHR-EDG-ANALYTICS-V1`  
PROJECT: `OneHR NEW`  
ADDON: `onehr_analytics`  
TARGET: `Odoo 19 Community Edition`  
DELIVERY: `Direct Full Addon Build`  
TASK: `ONEHR-ANALYTICS-DIRECT-FULL-20260831`  
ATTEMPT: `1 / 2`

This document is a **hard gate**, not advisory guidance. It specializes the root OneHR
Enterprise Development Guardrail for Analytics without weakening it.

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0
Before implementation or runtime repair, confirm OneHR NEW, `onehr_analytics`, Odoo 19 CE,
latest user-supplied workspace, root guardrail, and the approved Analytics product contract.
Write scope is `onehr_analytics` only. Runtime success, source success, and enterprise
completeness are separate states.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a `BOUNDED_IMPLEMENTATION_WORKER`. Architecture authority, simplification authority,
deletion authority, model-ownership authority, and dependency-change authority are `NONE`.
Codex may implement an already-approved design or a proven target-local repair only.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve the approved Analytics product intent: configurable KPI tiles, periodic snapshots,
thresholds and alerts, trend comparison, drill-through, multi-company/branch awareness,
BI-friendly evidence, executive favorites, and cross-addon KPI bridges. Do not remove a feature
to make an install or test pass. The supplied tutorial scaffold itself carries no accepted
business implementation that must be preserved.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Compilation/static acceptance is necessary but insufficient. Runtime install/upgrade,
security, workflow, multi-company behavior, provider authorization, scheduled generation,
immutable evidence, usability, and failure handling must all be accepted separately.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Approved model footprint is exact:
- persistent `onehr.analytics.tile`;
- persistent `onehr.kpi.snapshot`;
- abstract `onehr.mixin.analytics`.

No generic tutorial model is permitted. Optional transaction addons remain source owners.
Analytics owns KPI definitions and snapshot evidence only.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Separate concerns into `analytics_mixin.py`, `provider_engine.py`, `analytics_tile.py`, and
`kpi_snapshot.py`. Security, data, views, tests, docs and source-acceptance tooling remain in
separate conventional folders. Business methods are named by intent rather than compressed
helpers or generated opaque code.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Forms must use business sections, statusbar workflow, meaningful action buttons, smart
buttons, KPI summary blocks, threshold/schedule sections, evidence tabs, ribbons where useful,
and chatter only where operational collaboration is appropriate. High-volume snapshots remain
immutable evidence and do not receive unnecessary chatter.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model must have an explicit UI coverage decision. Tile has List/Form/Search
and Kanban dashboard. Snapshot has List/Form/Search plus Pivot/Graph analysis. Button placement
must match lifecycle and authority. No view is added merely to satisfy a count.

## HARD GATE 8 — SEARCH VIEW WAJIB
Every persistent model has a dedicated search view with useful filters and group-by dimensions.
Search domains may reference only stored/searchable fields.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists expose business identifiers, scope, category/state/status, key metrics, dates and owner
context with restrained decorations. Row actions are present only where they reduce navigation
burden and remain server-authorized.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
UI hiding is never authorization. Analyst/Manager/Admin groups, ACLs, global company rules,
provider source ACLs and model action guards remain authoritative. No custom `base.group_user`
CRUD. No business `sudo()`. No public Analytics controller. Branch-scoped providers fail closed
if a verifiable branch boundary is unavailable.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
All model table identifiers and explicit relation tables must remain PostgreSQL-safe and below
the 63-byte identifier limit. Many2many relations are explicitly named. No legacy
`_sql_constraints`; Odoo 19 `models.Constraint` is used. XML IDs must be unique. Action field
naming follows Odoo 19 (`group_ids`, not invalid `groups_id`). Details are in
`DATABASE_IDENTIFIER_ORM_SAFETY.md`.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Use readable names, bounded methods, conventional Odoo structure, clear guard clauses, and
small provider helpers. Do not hide business policy in clever metaprogramming, encoded blobs,
or arbitrary runtime dispatch.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain security boundaries, source ownership, fail-closed behavior, intentional
immutability, retention, and why potentially surprising choices exist. Comments must not restate
obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
`MAX_CODEX_ATTEMPTS_PER_TASK = 2` and `MAX_REPEAT_OF_SAME_ROOT_CAUSE = 1`.
The present direct-full task is Attempt 1/2. A runtime traceback must be classified before any
mutation. Harness/environment failures do not authorize source mutation. A distinct proven
source defect may authorize Attempt 2/2. If that attempt fails, stop with
`STOP_REASON: MAX_ATTEMPTS_REACHED`.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
The addon may move forward only when the completeness matrix records architecture, ownership,
security, UI/UX, workflow, analytics evidence, cross-addon contracts, Odoo 19 compatibility,
source acceptance and Windows runtime acceptance. Source PASS alone sets only
`PASS_FOR_RUNTIME`, never production acceptance.

## Non-negotiable ownership boundaries
- Analytics does not become Recruitment, Attendance, Time Off, Learning, Payroll, Appraisal,
  Career/Succession, Discipline, Branch or Integration API owner.
- No arbitrary Python formula execution, `eval`, `safe_eval`, or arbitrary model/method dispatch.
- No canonical employee, branch, payroll, applicant, leave, learning or appraisal duplication.
- No fabricated Enterprise-only Spreadsheet, Cohort or Gantt capability in Odoo 19 CE.

END_GUARDRAIL: `ONEHR-EDG-ANALYTICS-V1`
