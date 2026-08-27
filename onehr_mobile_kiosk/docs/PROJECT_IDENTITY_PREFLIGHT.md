# OneHR Mobile Kiosk — Project Identity Preflight

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

- **PROJECT:** OneHR NEW
- **ADDON:** `onehr_mobile_kiosk`
- **TARGET PLATFORM:** Odoo 19 Community Edition
- **DELIVERY METHOD:** Direct Full Addon Build
- **AUTHORITATIVE ARCHITECTURE:** OneHR Enterprise Architecture v2
- **AUTHORITATIVE REGISTRY:** OneHR Master Model Registry v1
- **PRODUCT BASELINE:** OneHR 25 Addons Specification for Odoo 19 CE
- **FUNCTIONAL BENCHMARK:** Oracle HRMS Enterprise / Workforce Management Guide where compatible with the frozen OneHR architecture
- **AUTHORITATIVE CURRENT SOURCE CONTEXT:** latest complete OneHR workspace dump supplied by the user on 18 Aug 2026
- **ROOT PROJECT GUARDRAIL:** `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`
- **ROOT GUARDRAIL SHA-256 DECLARED BY CURRENT WORKSPACE:** `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`

## Preservation rule

The supplied `onehr_mobile_kiosk` folder is a generic Odoo tutorial scaffold, not an accepted
business implementation. Preservation therefore applies to the approved OneHR product intent,
model ownership and current sibling integration contracts:

1. `onehr.kiosk.device` and `onehr.kiosk.log` are the two product-specified persistent kiosk models.
2. Odoo/OneHR Attendance `hr.attendance` remains the canonical attendance transaction.
3. `onehr_attendance` remains the hard dependency and its accepted
   `hr.attendance.onehr_ingest_interval(payload)` service is the attendance ingestion boundary.
4. `onehr_timeoff` remains a soft dependency; quick requests must use the employee's normal
   Time Off authority when available.
5. Device token, QR/NFC, geotag/geofence, face-ready capability, today schedule, leave balance,
   online/offline queue, synchronization, usage/error reporting and KPI intent are preserved.
6. `onehr_integrations_api` remains owner of external/public third-party API/webhook concerns.
7. Multi-company isolation is mandatory; branch is optional/downstream and is not reverse-owned here.

## Allowed change

- Full replacement of the generic scaffold by the approved enterprise implementation.
- Odoo 19 compatibility hardening.
- Professional backend UI, authenticated kiosk web UI, QR/NFC browser capabilities and geolocation.
- Hashed device-token governance, encrypted browser offline queue, durable retry/dead-letter evidence.
- Canonical Attendance bridge and soft Time Off bridge.
- Tests, reports, analytics, documentation and source-acceptance tooling.

## Forbidden change

- No duplicate attendance, employee, leave, branch, location, approval or API canonical model.
- No hard dependency drift beyond exactly `onehr_attendance`.
- No public unauthenticated attendance endpoint.
- No business `sudo()` bypass.
- No raw persistent device token, raw QR/NFC credential, PIN or biometric template/image evidence.
- No legacy `_sql_constraints`.
- No broad `base.group_user` CRUD on kiosk business models.
- No security weakening to make kiosk UX easier.
- No Codex architecture, simplification, feature deletion or endless retry.

## Current verified status

- Generic legacy scaffold: superseded by this Direct Full Build.
- Source/static acceptance: must be reported separately by `tools/source_acceptance.py`.
- Windows Odoo 19 install/upgrade/runtime/UAT: **PENDING** until executed on the user's target instance.
- Exact Master Model Registry ED labels for the two kiosk rows: **PENDING exact registry-row verification**.
- Enterprise completion / move-forward: **NO** until all runtime and registry gates pass.
