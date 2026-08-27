# OneHR Enterprise Development Guardrail — Document Direct Full Build

GUARDRAIL_ID: ONEHR-EDG-V6-DOCUMENT-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_document
TARGET_PLATFORM: Odoo 19 Community Edition
DELIVERY_METHOD: DIRECT_FULL_ADDON_BUILD
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

Before implementation or repair, identify PROJECT, ADDON, AUTHORITATIVE BASELINE,
PRESERVATION RULE, ALLOWED CHANGE, FORBIDDEN CHANGE and CURRENT VERIFIED STATUS.
Any ambiguity means STOP.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex is not used to invent the document architecture. If explicitly invoked
later, it may only implement a bounded correction against the approved Registry,
dependency and security contracts.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Document library, categories, template-driven output, validity, reminder,
issue/sign/archive lifecycle, secure employee/source linkage, report and audit
intent must not disappear merely to obtain PASS. Historical scaffold ideas not
owned by the Registry are preserved through approved contracts rather than
inventing unauthorized models.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Static syntax, install, upgrade and test PASS are only technical evidence.
Enterprise completeness additionally requires feature, security/privacy,
history, attachment, integration, runtime and final functional review.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Inventory all eight Registry models, fields, methods, actions, states, views,
menus, ACLs, record rules, report, cron, sequence, tests, docs and downstream
extension contracts before source acceptance.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Separate categories, logical documents/versions, templates/versions, e-sign
transactions and wizards into focused files. Helpers must be small, named and
business-readable.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Forms must expose document identity, ownership, category/sensitivity, effective
dates, version evidence, expiry, source, attachments, signature evidence and
controlled actions. Decorative controls without a business purpose are rejected.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every Registry model has an explicit UI decision. All six persistent business
models have enterprise list/form/search coverage; transient models have focused
modal forms.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every persistent `onehr_document` model requires a dedicated search view with
operational filters/grouping appropriate to document, category, expiry, template
and e-sign work.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Lists expose actionable business columns, state/sensitivity badges, expiry
signals, ownership, company scope and safe row actions. Lists are not generic
name/value scaffolds.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

Button visibility is usability only. ACLs, global company rules, sensitivity
rules, ownership, source `check_access`, history immutability and attachment
ownership remain authoritative. No public download route is created.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use Odoo 19 model classes, descriptive methods, explicit state transitions,
bounded helper functions, readable domains and no arbitrary executable stored
template code. Do not compress business logic into opaque one-liners.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain architecture/security intent: why documents are versioned, why
template variables are bounded, why provider secrets are absent, why source
records are re-authorized and why binary files remain attachment-backed.

## HARD GATE 14 — CODEX RETRY LIMIT

MAX_ATTEMPTS = 2
MAX_REPEAT_SAME_ROOT_CAUSE = 1

Every failed runtime gate must first be classified:
HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE,
ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE or
ARCHITECTURE_CONFLICT.

Same root cause repeated, architecture ambiguity, ownership conflict, destructive
migration or out-of-scope sibling change => STOP.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

The final matrix must explicitly report architecture, Registry, preservation,
source/static, fresh install, tests, security/privacy, attachment access,
effective dating/version history, expiry/reminder, e-sign evidence, first
upgrade, repeated upgrade/idempotency, post-upgrade smoke,
uninstall/reinstall, integration contracts and final functional review.
PENDING is never rewritten as PASS.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

Gate 11 is intentionally undefined because the user-defined 15 Hard Gate list does
not assign a Gate 11. This package records the gap but does not invent a substantive gate.

## Mandatory Codex contract if the user explicitly invokes Codex later

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
DEPENDENCY_CHANGE_AUTHORITY = NONE
MODEL_OWNERSHIP_CHANGE_AUTHORITY = NONE
MAX_ATTEMPTS = 2
MAX_REPEAT_SAME_ROOT_CAUSE = 1
TARGET_ADDON = onehr_document
WRITE_SCOPE = exact onehr_document path only
APPROVED_ARCHITECTURE = OneHR Enterprise Architecture v2
APPROVED_REGISTRY = OneHR Master Model Registry v1
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

This package does not run Codex automatically.
