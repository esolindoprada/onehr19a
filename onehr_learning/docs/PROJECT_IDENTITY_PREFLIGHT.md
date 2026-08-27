# OneHR Learning — Project Identity Preflight

PROJECT: OneHR NEW
ADDON: onehr_learning
TARGET: Odoo 19 Community Edition
DELIVERY: Direct Full Addon Build

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1 (exact ED labels still require authoritative-row comparison).
- OneHR 25 Addons Specification for Odoo 19 CE.
- Root OneHR Enterprise Development Guardrail.
- Latest user-supplied OneHR workspace source.
- Oracle HRMS / Oracle Learning Management concepts only as a compatible functional benchmark.
- Odoo 19 CE native technical ownership.

PRESERVATION RULE:
- Preserve the eight approved Learning business model names.
- hr.employee remains the worker owner; res.partner remains contact/legal counterparty owner.
- onehr_workflow_approval remains generic approval-engine owner.
- Learning owns training attendance, not work attendance.
- Learning owns training certificates, not generic employee education/document ownership.
- Optional downstream modules stay soft integrations.

ALLOWED CHANGE:
- Replace the generic tutorial scaffold completely with the approved enterprise implementation.
- Add Odoo 19 compatibility, professional UI, restrictive security, reports, tests, docs,
  import/export, crons and narrow service contracts.

FORBIDDEN CHANGE:
- Tutorial model onehr_learning.onehr_learning.
- Extra unapproved Learning business model.
- Hard dependency beyond onehr_base, onehr_corehr, onehr_security,
  onehr_workflow_approval.
- Sibling source edit, ownership transfer, broad base.group_user CRUD, business sudo,
  legacy _sql_constraints, public unauthenticated API, or fake CE-only Gantt renderer.

CURRENT VERIFIED STATUS:
- Supplied onehr_learning baseline is a generic Odoo scaffold (version 0.1, depends base).
- This Direct Full Build replaces that scaffold.
- Source/static acceptance is executed locally.
- Windows Odoo 19 install/upgrade/runtime acceptance remains pending.
- Exact Master Model Registry ED labels are not fabricated.

ROOT_CAUSE_CLASSIFICATION_FOR_REBUILD: ADDON_SOURCE_FAILURE
PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD
