# OneHR Integrations API — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-INTEGRATIONS-API-V1
STATUS: APPROVED_HARD_GATE_FOR_THIS_BUILD
PROJECT: OneHR NEW
ADDON: onehr_integrations_api
TARGET_PLATFORM: Odoo 19 Community Edition
PRIMARY_DELIVERY_METHOD: DIRECT_FULL_ADDON_BUILD
ROOT_GUARDRAIL: ONEHR-EDG-V1
ROOT_GUARDRAIL_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55
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

The exact project/addon, supplied baseline, root guardrail, approved five persistent models,
hard dependency, soft integration direction, write scope and runtime status must be known before work.
`docs/PROJECT_IDENTITY_PREFLIGHT.md` is mandatory evidence.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is a bounded implementation worker only. It cannot redesign canonical business models,
move domain ownership into the API layer, alter dependency direction, weaken security, invent
Registry ED labels, or simplify away approved integration capability.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Preserve the product contract: versioned REST v1, API keys/scopes, rate limits, HMAC/replay
protection, inbound/outbound webhooks, retry/dead-letter queue, API audit/KPI, OpenAPI/Postman,
CORS/error schema and soft integration across OneHR. Tutorial placeholders are not accepted
business functionality and may be replaced by the approved full implementation.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Python/XML/source PASS is only permission to start runtime validation. Fresh install, endpoint
execution, least-privilege service-user UAT, security denial tests, scheduler, network-failure
behavior, upgrade/idempotency and cross-addon contract smoke remain separate gates.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Persistent models are exactly `onehr.api.key`, `onehr.api.scope`, `onehr.webhook`,
`onehr.api.log`, `onehr.api.queue`. `res.config.settings` is a native transient extension.
No employee/attendance/payroll/learning/document/etc. business master is duplicated here.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Code is split by responsibility: credential/scope/webhook/log/queue/settings models, explicit
REST controllers, request-runtime security, domain adapters, webhook delivery and OpenAPI.
No generated mega-file or arbitrary model/method dispatcher is allowed.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Operational forms use meaningful statusbars, lifecycle buttons, smart buttons, body actions,
notebooks, ribbons, chatter and One2many queue row actions where they improve administration.
Decorative UI never substitutes for model/server security.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every persistent model has an explicit UI contract in `UI_UX_MATRIX.md`, including whether
Kanban/Pivot/Graph is materially useful rather than fabricated.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every persistent custom model has a dedicated Search view.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Every persistent model has an operational `<list>` with decision-useful fields, badges,
decorations, optional columns and row actions where appropriate.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

ACLs, global company rules, service-user ACL/rules, key scopes, HMAC/replay controls and model
methods are authoritative. No broad `base.group_user` custom-model CRUD. Public HTTP routes must
authenticate before business execution. Domain adapters never use `sudo()`.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY

Odoo/PostgreSQL identifiers must remain safe and deterministic. Custom model names, relation
table names, constraint attributes, XML IDs, sequence codes and field names must be reviewed for
collisions and PostgreSQL's 63-byte identifier boundary. Many2many relations use explicit short
relation names. Odoo 19 ORM/view field names are validated (`group_ids`, not obsolete/invalid
`groups_id` on `ir.actions.act_window`). Legacy `_sql_constraints` is forbidden; use
`models.Constraint`.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Readable constants, small methods, direct Odoo ORM, explicit adapter methods, Odoo 19 `<list>`,
direct modifiers and `models.Constraint`. Avoid opaque reflection, metaprogramming and generic
user-controlled model/method invocation.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain security boundaries, technical-vs-business elevation, credential storage,
SSRF/replay/idempotency and ownership rationale. Comments do not narrate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT

Each implementation/repair task has at most two bounded source attempts; same root cause may
repeat once. Harness/environment failures do not authorize source mutation. After Attempt 2,
STOP with evidence instead of becoming an endless retry engine.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

`ENTERPRISE_COMPLETENESS_MATRIX.md` is mandatory and keeps source, runtime, security, upgrade,
network, registry and UAT states separate. Any pending required runtime evidence keeps
`ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO`.

Root-cause classes remain: HARNESS_FAILURE, ENVIRONMENT_FAILURE,
ODOO_VERSION_COMPATIBILITY_FAILURE, ADDON_SOURCE_FAILURE, TEST_DEFECT,
DATA/MIGRATION_FAILURE, ARCHITECTURE_CONFLICT.

Default write scope is `onehr_integrations_api` only. Sibling source edits are forbidden unless
separately approved.
