# OneHR Enterprise Development Guardrail — Multicompany & Branch Direct Full Build

GUARDRAIL_ID: ONEHR-EDG-V5-MULTICOMPANY-BRANCH-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_multicompany_branch
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

Every implementation/repair must name PROJECT, ADDON, AUTHORITATIVE BASELINE, PRESERVATION RULE, ALLOWED CHANGE, FORBIDDEN CHANGE and CURRENT VERIFIED STATUS. Missing or ambiguous identity means STOP.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex, if explicitly used later, is a bounded implementation worker only. It may implement or repair an already approved contract, never invent architecture, model ownership, dependencies, simplification, deletion, migration policy or product scope.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Historical branch intent and accepted OneHR security extension hooks must be preserved. No feature may disappear merely to make install/tests pass. The obsolete scaffold model is excluded only because the approved Registry explicitly replaces it with `onehr.branch`.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax/static/install/test PASS does not prove enterprise completion. Functional completeness is reviewed separately after runtime, security, upgrade/idempotency and integration evidence exists.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Inventory models, extensions, fields, methods, actions, views, menus, ACLs, record rules, tests, docs and integration hooks before declaring source acceptance.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Separate branch master, reusable branch mixin, company extension, user extension and role integration into focused files. Keep server authorization helpers and action helpers small and named by business purpose.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Branch forms must use a meaningful header/statusbar, operational identity, legal company, effective period, hierarchy, governance notes, smart buttons and controlled actions. Decorative complexity without business purpose is rejected.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every user-facing model/extension must have an explicit UI decision: editable master, read-only summary, inherited native form, inherited security form, consolidated pivot/graph, or intentionally no standalone UI.

## HARD GATE 8 — SEARCH VIEW WAJIB

`onehr.branch` must have a dedicated search view. User and role search extensions must expose branch filtering/grouping where operationally useful.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Branch list must expose code/name/type/company/hierarchy/effective dates/status and safe operational actions. Role list must show branch scope. Decorations must represent lifecycle meaning, not cosmetic color.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

Buttons/groups/read-only modifiers are usability controls only. Server-side group checks, ACLs, record rules, company intersection, branch constraints and effective-date validation remain authoritative. Branch scope may narrow but never expand Odoo allowed-company security.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use Odoo 19 native model classes, `models.Constraint`, named constraints/actions, section comments, explicit domains and no plain-Python mixin in an Odoo model inheritance list. Avoid compressed one-line business logic.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain architecture/security intent, especially narrow system-user derivation, company-vs-branch boundary and why branch scope cannot silently be rewritten. Comments must not restate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT

MAX_ATTEMPTS=2; MAX_REPEAT_SAME_ROOT_CAUSE=1. A new source modification requires root-cause classification first. Same root cause repeated, architecture ambiguity, ownership conflict, destructive migration or out-of-scope need => STOP with evidence.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

The final matrix must report PASS / FAIL / PENDING / NOT_APPLICABLE for architecture, registry, preservation, source/static, fresh install, tests, branch/company security, effective dating, first upgrade, repeat upgrade/idempotency, post-upgrade smoke, uninstall/reinstall, integration contracts and final functional review. PENDING is never rewritten as PASS.

## Codex mandatory contract if explicitly invoked later

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MAX_ATTEMPTS = 2
TARGET_ADDON = onehr_multicompany_branch
WRITE_SCOPE = exact onehr_multicompany_branch path only
APPROVED_ARCHITECTURE = OneHR Enterprise Architecture v2
APPROVED_REGISTRY = OneHR Master Model Registry v1
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

No Codex run is authorized by this package automatically.
