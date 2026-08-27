# OneHR Recruitment — Enterprise Development Guardrail

GUARDRAIL_ID: ONEHR-EDG-V7-RECRUITMENT-DIRECT-FULL
STATUS: APPROVED_HARD_GATE_FOR_THIS_BUILD
PROJECT: OneHR NEW
ADDON: onehr_recruitment
TARGET_PLATFORM: Odoo 19 Community Edition
PRIMARY_DELIVERY_METHOD: DIRECT_FULL_ADDON_BUILD
ROOT_GUARDRAIL: ONEHR-EDG-V1
ROOT_GUARDRAIL_DECLARED_SHA256_FROM_WORKSPACE_EXPORT: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55
ROOT_GUARDRAIL_INTEGRITY_RULE: VALIDATE_LOCAL_MD_AGAINST_COLOCATED_SHA256_WITHOUT_REWRITING_ROOT_GUARDRAIL
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

Before work: project, addon, authoritative baseline, preservation rule, allowed change, forbidden change and current verified status must all be explicit. `docs/PROJECT_IDENTITY_PREFLIGHT.md` is mandatory evidence.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex may implement or diagnose a bounded approved task only. It may not choose architecture, scope, canonical models, model ownership, dependencies, deletion/merge strategy or product simplification.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Approved Recruitment specification, Architecture v2, Master Model Registry and accepted sibling integration contracts must be preserved. Generic scaffold placeholders are not allowed to override approved registry/native ownership.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax PASS, install PASS, runtime PASS or tests PASS are not proof of enterprise completeness. Business flow, history, security, integration, UI, reporting, upgrade and preservation are separate acceptance dimensions.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Exact models, inherited native models, fields, business methods, views/actions/menus, ACLs/rules, data, tests and integration contracts must be inventoried before freeze. Unexplained loss is a hard failure.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Code is decomposed by business responsibility. Helper functions are small and explicit; business models do not become monolithic utility files. A human maintainer must be able to locate and edit behavior safely.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Forms use business lifecycle statusbars, meaningful header actions, smart buttons, sections/notebooks, ribbons, chatter and body operations when those interactions materially help users. Decorative complexity alone is not accepted.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every user-facing model has a documented UI contract in `docs/UI_UX_MATRIX.md`. Native models are extended instead of shadowed.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every custom persistent model has a dedicated search view with useful operational filters/grouping. Search is part of enterprise usability, not optional polish.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Lists expose decision-relevant fields, state/status, optional secondary columns and safe row actions where appropriate. Large operational lists must be scannable without opening every form.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

Button visibility is not authorization. ACL, global company boundaries, group rules, field groups and Python guards remain authoritative. No source business `sudo()` is allowed merely to make a workflow work.

## HARD GATE 11 — INTENTIONALLY UNDEFINED

The user did not define Hard Gate 11. This build does not invent or renumber one.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use descriptive names, business constants, small methods, explicit conditions, limited nesting and consistent source layout. Avoid clever compact code that obscures policy.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain business invariants, ownership boundaries, historical/effective-dating intent, security rationale and non-obvious compatibility choices. Comments that only restate the next line are avoided.

## HARD GATE 14 — CODEX RETRY LIMIT

MAX_CODEX_ATTEMPTS_PER_TASK = 2. MAX_REPEAT_OF_SAME_ROOT_CAUSE = 1. A failed gate must first be classified: HARNESS_FAILURE, ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE, ADDON_SOURCE_FAILURE, TEST_DEFECT, DATA/MIGRATION_FAILURE, or ARCHITECTURE_CONFLICT. Harness/environment failures do not justify business-source edits unless a separate source defect is proven.

Required stop markers include:

- STOP_REASON: ARCHITECTURE_DECISION_REQUIRED
- STOP_REASON: BASELINE_MISSING
- STOP_REASON: OWNERSHIP_CONFLICT
- STOP_REASON: REPEATED_ROOT_CAUSE
- STOP_REASON: DESTRUCTIVE_CHANGE_NOT_APPROVED
- STOP_REASON: OUT_OF_SCOPE_CHANGE_REQUIRED
- STOP_REASON: MAX_ATTEMPTS_REACHED

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

`docs/ENTERPRISE_COMPLETENESS_MATRIX.md` must have no applicable FAIL/PENDING before FINAL/FROZEN/MOVE_FORWARD_READY. Source acceptance alone always leaves runtime rows pending.

## Codex prompt minimum contract

Every Codex prompt, if the user explicitly chooses to use Codex later, must contain:

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MODEL_OWNERSHIP_CHANGE_AUTHORITY = NONE
DEPENDENCY_CHANGE_AUTHORITY = NONE
MAX_ATTEMPTS = 2
MAX_REPEAT_OF_SAME_ROOT_CAUSE = 1
TARGET_ADDON = onehr_recruitment
WRITE_SCOPE = onehr_recruitment only, unless separately approved
APPROVED_ARCHITECTURE = OneHR Enterprise Architecture v2
APPROVED_REGISTRY = OneHR Master Model Registry v1
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

## Move-forward rule

`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: YES` is forbidden until source/static, exact registry/dependency validation, fresh install, all required tests, security behavior, upgrade/repeat upgrade, post-upgrade smoke, history/temporal behavior, integration contracts, sibling preservation and the enterprise completeness matrix all pass with evidence.

END_GUARDRAIL: ONEHR-EDG-V7-RECRUITMENT-DIRECT-FULL
