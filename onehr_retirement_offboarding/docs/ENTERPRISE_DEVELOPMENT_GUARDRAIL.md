# OneHR Retirement & Offboarding — Enterprise Development Guardrail

GUARDRAIL_ID: `ONEHR-EDG-RETIREMENT-OFFBOARDING-V1`  
ROOT_GUARDRAIL: `ONEHR-EDG-V1`  
ROOT_GUARDRAIL_SHA256: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`  
STATUS: `APPROVED_HARD_GATE_FOR_THIS_BUILD`  
TASK: `ONEHR-RETIREMENT-OFFBOARDING-DIRECT-FULL-20260901`  
TARGET: Odoo 19 Community Edition  
CODEX_ROLE: `BOUNDED_IMPLEMENTATION_WORKER`  
MAX_CODEX_ATTEMPTS_PER_TASK: `2`  
MAX_REPEAT_OF_SAME_ROOT_CAUSE: `1`

This file is a hard gate, not implementation advice. The addon must not be called FINAL, FROZEN or MOVE_FORWARD_READY merely because source checks, installation, or tests pass.

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

The assigned write scope is exactly `onehr_retirement_offboarding`. The incoming target is a generic tutorial scaffold and the approved task explicitly authorizes a registry-preserving Direct Full Addon Build. Target platform is Odoo 19 CE. Architecture authority remains outside Codex.

## HARD GATE 1 — CODEX BUKAN ARCHITECT

Codex may implement only the approved design and later repair a proven target-local defect. Codex has no authority to redesign model ownership, dependencies, approval semantics, security, history, or sibling addons.

## HARD GATE 2 — EXISTING FUNCTION PRESERVATION

The product contract is preserved: resignation/retirement/other exit cases, cross-functional checklist, asset/access clearance, exit interview, access revoke evidence, final-benefit bridge, SLA reminders, audit, reporting, multi-company readiness and soft downstream integration. The generic tutorial model/controller/demo has no accepted business function and is removed.

## HARD GATE 3 — ENTERPRISE COMPLETENESS BUKAN SEKADAR TEST PASS

Static/source PASS, install PASS and test PASS are separate evidence. Functional completeness additionally requires workflow, security/privacy, cross-addon ownership, audit/history, reporting, configuration and Windows runtime acceptance.

## HARD GATE 4 — FULL STRUCTURAL INVENTORY

Persistent owners are exactly:

- `onehr.offboarding`
- `onehr.offboarding.checklist`
- `onehr.clearance.item`
- `onehr.exit.interview`

Native extensions are `hr.employee` and `res.users`. No parallel employee, contract, payroll, document, branch, portal, API or analytics master is created.

## HARD GATE 5 — HUMAN-FRIENDLY CODING STRUCTURE

Business concerns are separated into model files, action helpers, security helpers, views, reports, tests and documentation. Helper methods use explicit names. Bounded soft integrations are grouped in the offboarding model rather than hidden in generic dispatch code.

## HARD GATE 6 — PROFESSIONAL FORM DESIGN

Forms contain clear business sections, meaningful statusbars, role-gated actions, smart buttons, ribbons, evidence tabs and inline operational summaries. High-risk controls are not reduced to editable status fields.

## HARD GATE 7 — UI/UX MATRIX PER MODEL

The mandatory matrix is documented in `UI_UX_MATRIX.md`. The design uses only meaningful Odoo 19 CE surfaces and does not fabricate Enterprise-only views.

## HARD GATE 8 — SEARCH VIEW WAJIB

Every persistent model has a dedicated Search View with useful fields, filters and group-by dimensions.

## HARD GATE 9 — LIST VIEW ENTERPRISE QUALITY

Every persistent model has an enterprise List View with operational columns, badges/decorations and row actions where the row action is safe and useful.

## HARD GATE 10 — SECURITY TIDAK BOLEH DIKALAHKAN UI

UI invisibility is never relied on as authorization. Server methods enforce role checks, company rules are global, evidence/state writes are guarded, task owners are scoped to assigned work, and Odoo user revocation requires both Offboarding Administrator and System Administrator authority.

## HARD GATE 11 — DATABASE IDENTIFIER & ORM NAMING SAFETY

PostgreSQL identifiers and explicit relation names are checked against the 63-byte limit. The addon uses Odoo 19 `models.Constraint`, not legacy `_sql_constraints`. Details are in `DATABASE_IDENTIFIER_ORM_SAFETY.md`.

## HARD GATE 12 — CODE STYLE HUMAN FRIENDLY

Code favors clear business vocabulary, small helpers, explicit state actions, predictable action dictionaries and readable security checks over clever metaprogramming.

## HARD GATE 13 — COMMENTS YANG BERGUNA

Comments explain ownership boundaries, immutable evidence, security intent and why soft integrations are bounded. Comments do not narrate obvious syntax.

## HARD GATE 14 — CODEX RETRY LIMIT

Current build is Attempt `1 / 2`. A later runtime repair may use at most one additional target-local source attempt after the FIRST concrete failure is classified. Environment/harness failures do not authorize source mutation. Attempt 2 failure stops with `STOP_REASON: MAX_ATTEMPTS_REACHED`.

## HARD GATE 15 — ENTERPRISE COMPLETENESS MATRIX

`ENTERPRISE_COMPLETENESS_MATRIX.md` is the move-forward checklist. Current source build may be PASS_FOR_RUNTIME while Windows runtime, registry ED classification and upgrade evidence remain pending.
