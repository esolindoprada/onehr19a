
# OneHR Portal Self-Service — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V1-PORTAL-SELF-SERVICE-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_portal_self_service
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
Verify OneHR NEW, exact target addon, latest supplied workspace, approved product contract,
root guardrail, Odoo 19 CE ownership, allowed write scope and preserved sibling contracts
before any source change. Default write scope is `onehr_portal_self_service` only.

## HARD GATE 1 — CODEX BUKAN ARCHITECT
Codex is a bounded implementation worker. Codex may implement an approved design or repair
a proven defect, but may not redesign canonical models, ownership, dependency topology,
security boundaries, workflow architecture or enterprise scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION
Preserve the supplied Portal product contract: My HR, My Team, employee self-service,
manager approval, HR processing, request status/SLA/history, notifications, attachments,
profile updates and the documented bridges to OneHR-owned HR domains. No capability may
be silently deleted merely to pass syntax, install or tests.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS
Static PASS, install PASS and test PASS are separate evidence. Portal rendering, CSRF,
record rules, manager/employee isolation, multi-company behavior, mail/activity, cron,
optional cross-addon contracts, upgrade/idempotency and UAT must be validated separately.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY
Approved persistent Portal business models are exactly:
- `onehr.portal.request.type`
- `onehr.portal.request.stage`
- `onehr.portal.request`

Native extensions are `res.users` and `hr.employee`. Decision/bulk wizards are transient.
No employee, leave, learning, appraisal, document, payroll, policy, SOP, career, discipline,
API-authentication or branch canonical master may be duplicated here.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE
One business concern per readable file. Lifecycle logic, integration services, authority
helpers, native extensions, controllers and wizards remain separated. Avoid generated
mega-files, opaque metaprogramming and hidden business behavior.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN
Operational forms use statusbar, contextual header actions, smart buttons, body actions,
notebooks, badges/ribbons, chatter/activity and meaningful One2many row actions where
business context benefits from drill-down.

## HARD GATE 7 — UI/UX MATRIX PER MODEL
Every persistent model has an explicit UI contract documented in `UI_UX_MATRIX.md`.
Portal pages are separately mapped for Employee and Manager journeys.

## HARD GATE 8 — SEARCH VIEW WAJIB
Dedicated search views are required for all three persistent Portal models, with useful
operational filters and groupings. Search domains may reference only searchable fields.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY
Every persistent model requires an operational Odoo 19 `<list>` view with meaningful
columns, badges/decorations, optional fields and row actions where useful. Legacy `<tree>`
is forbidden.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI
ACL, record rules and model methods are authoritative. UI visibility is convenience only.
No broad `base.group_user` CRUD, no business `sudo()`, no public HR endpoint and no
cross-addon ACL bypass. Optional integration execution remains subject to the owner addon's
normal security and authority.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY
Every model/table/relation/constraint identifier must remain PostgreSQL/Odoo safe. Explicit
Many2many relation names are kept below PostgreSQL's identifier limit. Odoo 19
`models.Constraint` is used instead of legacy `_sql_constraints`. Canonical model names are
not invented to solve naming collisions. Relation-table and generated-table names must be
audited before release.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY
Use readable constants, small helpers, explicit actions, Odoo 19 `<list>`, direct modifiers,
`models.Constraint`, standard controller methods and ordinary Python. No legacy `attrs`,
`states`, `_sql_constraints`, or intentionally clever indirection.

## HARD GATE 13 — COMMENTS YANG BERGUNA
Comments explain security boundaries, ownership, SLA behavior, portal trust boundaries and
soft-integration rationale. Comments must not narrate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT
Maximum two bounded attempts for one proven implementation/repair task. The same root cause
may repeat at most once. Harness/environment failures do not authorize business-source
mutation. On repeated or architectural failure, stop and report evidence.

Required root-cause classes:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Required stop markers include:
STOP_REASON: ARCHITECTURE_DECISION_REQUIRED
STOP_REASON: BASELINE_MISSING
STOP_REASON: OWNERSHIP_CONFLICT
STOP_REASON: REPEATED_ROOT_CAUSE
STOP_REASON: DESTRUCTIVE_CHANGE_NOT_APPROVED
STOP_REASON: OUT_OF_SCOPE_CHANGE_REQUIRED
STOP_REASON: MAX_ATTEMPTS_REACHED

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX
`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory. Source, registry, Windows runtime,
security/UAT and downstream-integration status remain separate. Pending runtime or exact
registry evidence keeps `ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY = NO`.

## Required Codex contract
ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MAX_ATTEMPTS = 2
TARGET_ADDON = onehr_portal_self_service
WRITE_SCOPE = onehr_portal_self_service/**
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

END_GUARDRAIL: ONEHR-EDG-V1-PORTAL-SELF-SERVICE-DIRECT-FULL

