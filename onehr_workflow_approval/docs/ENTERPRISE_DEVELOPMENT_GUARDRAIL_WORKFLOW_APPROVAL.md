# OneHR Enterprise Development Guardrail — Workflow Approval Direct Full Build

GUARDRAIL_ID: ONEHR-EDG-V4-WORKFLOW-APPROVAL-DIRECT-FULL
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR NEW
ADDON: onehr_workflow_approval
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

Every task must state PROJECT, ADDON, AUTHORITATIVE BASELINE, PRESERVATION RULE,
ALLOWED CHANGE, FORBIDDEN CHANGE and CURRENT VERIFIED STATUS before implementation.

Authorities are OneHR Enterprise Architecture v2, OneHR Master Model Registry v1,
the approved 25-addon topology, latest user-supplied source/export, approved
preservation decisions and Odoo 19 CE native technical ownership.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex may diagnose and implement only a bounded approved change. Codex is not an
architect, product owner, simplifier, deletion authority, model-ownership authority,
dependency authority, security-policy authority or endless retry engine.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

Preserve matrix approval, role/threshold routing, sequential levels, parallel
steps, dynamic approver resolution, delegation, reassignment, SLA reminders and
escalation, self-approval guard, quorum/multi-eyes, auto approval, resubmit/cancel,
mail/activity/chatter, immutable decision/audit evidence, SLA/KPI reporting and
source integration hooks. Unexplained loss is a hard failure.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Syntax, install, upgrade or automated-test PASS is not enterprise completeness.
Architecture, registry, source ownership, workflow behavior, temporal semantics,
security, audit/history, reporting, upgrade/uninstall safety and realistic business
smoke must separately pass.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Exactly eight Master Model Registry rows are owned here:
1. onehr.approval.rule — NEW ED2
2. onehr.approval.step — NEW ED2
3. onehr.approval.request — NEW ED3
4. onehr.approval.decision — NEW ED3
5. onehr.approval.delegate — NEW ED1
6. onehr.approval.escalation.log — NEW ED3
7. onehr.mixin.approvable — NEW abstract ED0
8. onehr.approval.kpi.daily — NEW ED4

Hard dependencies remain exactly: onehr_security, mail.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Domain code is split into rule/step, request orchestration, decision evidence,
delegation, escalation evidence, source integration contract, KPI and small pure
helpers. Monolithic scaffold-style business code is forbidden.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Use meaningful statusbars, notebooks, smart buttons, body/header actions and
read-only evidence forms when backed by real server behavior.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

Every persistent model must have an explicit UI/UX contract in docs/UI_UX_MATRIX.md.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every persistent user-facing model must have a dedicated search view.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Lists must expose operational columns, states/badges, SLA/decision context and
relevant row actions, not basic name-only tables.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

Button visibility is not authorization. ACLs, record rules and Python authority
checks remain authoritative. Do not grant custom-model CRUD to base.group_user.
Workflow Administrator must not imply OneHR Security Admin or restricted HR data.
Approval engine must not sudo source business records.

Narrow sudo is allowed only for documented internal authority-resolution metadata
that ordinary requesters must not enumerate directly, and for append-only evidence
creation after the business action is already authorized. It may never authorize
or mutate the source business transaction.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Use readable domain names, short helpers, explicit state transitions, structured
JSON rather than executable expressions and Odoo-native model inheritance.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain architecture, authorization, temporal/history or compatibility
reasons. Do not clutter code with comments that merely restate syntax.

## HARD GATE 14 — CODEX RETRY LIMIT

Classify failures before source modification as HARNESS_FAILURE,
ENVIRONMENT_FAILURE, ODOO_VERSION_COMPATIBILITY_FAILURE, ADDON_SOURCE_FAILURE,
TEST_DEFECT, DATA/MIGRATION_FAILURE or ARCHITECTURE_CONFLICT.

Maximum two approved Codex attempts for one task and maximum one repeat of the same
root cause. No automatic retry loop. Architecture ambiguity, ownership conflict,
destructive change, out-of-scope work or repeated root cause must STOP.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

docs/ENTERPRISE_COMPLETENESS_MATRIX.md is mandatory. MOVE_FORWARD_READY may not be
YES while any applicable runtime, upgrade, security/history, post-upgrade or
functional-completeness item is PENDING or FAIL.

## Approval ownership contract

A generic approval request never owns the source business transaction. It references
the source, freezes minimum-necessary approval payload/routing context, records the
approval path/evidence and invokes narrow source hooks. The source addon owns the
business state and actual execution.

Approval decisions and SLA/escalation evidence are immutable during normal
operations. Corrections create superseding evidence. Completed ED3 history is never
rewritten to pretend that the original event did not occur.

END_GUARDRAIL: ONEHR-EDG-V4-WORKFLOW-APPROVAL-DIRECT-FULL
