# OneHR Attendance — Project Identity Preflight

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

- **PROJECT:** OneHR NEW
- **ADDON:** `onehr_attendance`
- **TARGET PLATFORM:** Odoo 19 Community Edition
- **DELIVERY METHOD:** Direct Full Addon Build
- **AUTHORITATIVE ARCHITECTURE:** OneHR Enterprise Architecture v2
- **AUTHORITATIVE REGISTRY:** OneHR Master Model Registry v1
- **PRODUCT BASELINE:** OneHR 25 Addons Specification for Odoo 19 CE
- **FUNCTIONAL BENCHMARK:** Oracle HRMS Enterprise / Workforce Management Guide where compatible with the frozen OneHR architecture
- **AUTHORITATIVE CURRENT SOURCE CONTEXT:** latest complete OneHR workspace dump supplied by the user on 18 Aug 2026
- **ROOT PROJECT GUARDRAIL:** `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`, expected SHA-256 `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`

## Preservation rule

1. Odoo `hr.attendance` remains the canonical attendance transaction. No `onehr.attendance` duplicate is created.
2. Odoo 19 native overtime calculation remains authoritative. The Registry concept `hr.attendance.overtime` maps to the actual Odoo 19 model `hr.attendance.overtime.line`.
3. Preserve enterprise requirements for shifts, rotation patterns, employee schedules, late/early detection, overtime integration, device/fingerprint staging, reconciliation, missing-punch evidence, reports, KPIs and multi-company isolation.
4. `onehr_assignment`, `onehr_timeoff`, `onehr_learning`, `onehr_mobile_kiosk`, `onehr_payroll_bridge`, `onehr_analytics` and `onehr_integrations_api` remain soft/downstream integration owners; this addon must not reverse dependency direction.
5. `onehr_assignment` may be referenced through a soft `fields.Reference` contract only when present. It is not a hard dependency.
6. Security is enforced by ACL/record rules/business methods, not by hiding buttons.
7. ED3 evidence is not made deletable merely to make uninstall or tests pass; uninstall-safe `@api.ondelete(at_uninstall=False)` is used.

## Allowed change

- Full replacement of the generic attendance scaffold by the approved enterprise implementation.
- Odoo 19 compatibility hardening.
- Professional forms, lists, search views, calendar/pivot/graph and QWeb reports.
- Shift policy, import/reconciliation, exception evidence, and native overtime metadata.
- Tests, documentation, acceptance tooling and bounded soft-integration hooks.

## Forbidden change

- No duplicate employee, attendance, overtime, job, position, department, work-location, branch, payroll, time-off or learning owner.
- No hard dependency drift beyond `onehr_corehr`, `onehr_security`, `hr_attendance`.
- No broad `base.group_user` CRUD for OneHR attendance business models.
- No `sudo()` business bypass.
- No legacy `_sql_constraints`.
- No business-history `unlink()` override used as an uninstall trap.
- No Codex architecture, simplification, feature deletion or endless retry.

## Current verified status

- Source/static acceptance: must be reported separately by `tools/source_acceptance.py`.
- Windows Odoo runtime acceptance: PENDING until executed on the user's Odoo 19 environment.
- Move-forward/frozen status: NO until all applicable runtime and enterprise-completeness gates pass.
