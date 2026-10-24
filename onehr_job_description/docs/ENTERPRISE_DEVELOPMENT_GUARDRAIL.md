
# OneHR Job Description — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-JD-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_job_description
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
Verify OneHR NEW identity, addon `onehr_job_description`, Odoo 19 CE target, latest
workspace, approved 25-addon product contract, OneHR Base native-first ownership,
root Guardrail, exact write scope, dependency direction and runtime status before
changing source.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker only. It may implement the approved
`onehr.jd` / `onehr.jd.version` contract or repair a proven runtime defect. It may
not redesign canonical ownership, add/remove core models, change dependency topology,
weaken security, delete functionality, or simplify enterprise requirements.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
The supplied target is a generic Odoo tutorial scaffold rather than accepted JD
business functionality. The Direct Full replacement must preserve the approved product
contract: position JD dictionary, purpose, responsibilities, KPI, competency, K3/HSE,
templates, versions/history, portal publication boundary, Recruitment/Appraisal export,
reports, coverage analytics, import capability and Draft → Review → Approved → Published.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Python/XML/static/test PASS does not equal enterprise completion. Fresh install,
workflow UAT, ACL/record rules, QWeb rendering, cron, import, integration contracts,
upgrade/idempotency, exact Registry ED rows and manual UI acceptance remain separate.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Approved persistent business models are exactly:
- `onehr.jd`
- `onehr.jd.version`

No persistent/transient responsibility/KPI/competency/risk/approval/import/API master
is invented. Detailed JD content belongs to the approved Version model.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
Readable concern-based files:
- authority helpers;
- JD master/template governance;
- JD version/workflow/content;
- integration services;
- security;
- views;
- reports;
- tests;
- evidence documentation.

No opaque metaprogramming or generated mega-file is required for normal maintenance.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Use relevant statusbars, lifecycle actions, smart buttons, body actions, badges/ribbons,
chatter/activity, tabs and version-history row actions. UI enhancement must never
replace server-side authorization.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model has documented List/Form/Search coverage and suitable analysis
views. UI ownership remains Odoo 19 CE compatible.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated Search views are mandatory for `onehr.jd` and `onehr.jd.version`.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Lists expose meaningful identity, position/job family, lifecycle/coverage, version,
review, effective dates and contextual row actions with useful decoration/badges.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL, global company rules, role rules and Python method guards are authoritative.
No broad custom CRUD for `base.group_user`, no business `sudo()`, no public controller
for JD content, and no direct rewrite of approved/published evidence.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
Database and ORM identifiers are a release gate:
- PostgreSQL identifier ceiling is treated as 63 bytes.
- Model names use lowercase dotted Odoo names.
- Canonical auto tables must remain `onehr_jd` and `onehr_jd_version`.
- Field names are lowercase snake_case, valid Python/Odoo identifiers and <=63 bytes.
- Explicit Many2many relation tables are unique and <=63 bytes.
- Constraint attribute names and expected table/field/index identifiers are checked
  for safe deterministic length and collision risk.
- No duplicate local XML external IDs.
- No accidental duplicate relation table/column pair.
- No field may statically depend on a soft-module model.
- SQL constraints use Odoo 19 `models.Constraint`; legacy `_sql_constraints` is forbidden.
- Model/table/field identifiers may not use whitespace, hyphens or uppercase.
- `@api.depends` may not use forbidden pseudo-field paths such as `id`/`.id`.

Any identifier collision/truncation ambiguity is an ADDON_SOURCE_FAILURE and blocks
runtime acceptance.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Readable method names, small helpers, explicit constants, Odoo 19 `<list>`, direct view
modifiers, `models.Constraint`, `Command` where relational commands improve clarity,
and no legacy `attrs`/`states`.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain ownership, security, historical evidence and soft-integration reasons,
not obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded attempts for one proven repair task. The same root cause may repeat
once. Environment/harness failures do not authorize random source mutation.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory. Source, runtime, Registry, security,
integration, reporting and upgrade status remain separate. Move-forward remains NO
until all applicable rows pass.

Runtime root-cause classification:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default write scope is `onehr_job_description` only. Sibling addon source changes
require separate architecture authorization.

