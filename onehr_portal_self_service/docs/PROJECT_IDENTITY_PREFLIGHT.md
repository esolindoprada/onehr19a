
# OneHR Portal Self-Service — Project Identity Preflight

PROJECT: OneHR NEW
ADDON: onehr_portal_self_service
TARGET: Odoo 19 Community Edition
DELIVERY: Direct Full Addon Build
SOURCE_WRITE_SCOPE: `onehr_portal_self_service` only

## Authoritative inputs
- OneHR root Enterprise Development Guardrail.
- Latest user-supplied OneHR workspace snapshot `onehr19a(20260826-124033).md`.
- Existing accepted OneHR addon ownership and service contracts in that workspace.
- Odoo 19 CE native model ownership.
- Oracle HRMS R12.1 Enterprise and Workforce Management / SSHR concepts as a functional benchmark, not a schema to copy.

## Supplied Portal baseline
The supplied Portal addon is a tutorial scaffold, while its product description already
specifies the target contract: My HR, My Team, requests, approvals, SLA, portal pages,
three Portal business models, native user/employee extensions and soft bridges.

## Approved Portal contract
Persistent business models exactly:
- `onehr.portal.request.type`
- `onehr.portal.request.stage`
- `onehr.portal.request`

Hard dependencies exactly:
- `onehr_corehr`
- `onehr_security`
- `portal`
- `web`
- `mail`

Soft/downstream domains remain owner-controlled: Time Off, Learning, Appraisal, Document,
Payroll Bridge, Job Description, PnP, SOP, Career/Succession, Analytics, Multi-company/
Branch and Integrations API.

## Ownership boundaries
- `hr.employee` remains the canonical worker.
- Portal owns service-request orchestration and portal presentation, not downstream HR transactions.
- Target addons retain ACL, record-rule and business-method authority.
- Discipline evidence is intentionally not surfaced to employee self-service without a separately approved safe upstream contract.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD
ROOT_CAUSE_CLASSIFICATION_FOR_REBUILD: ADDON_SOURCE_FAILURE
WINDOWS_RUNTIME_ACCEPTANCE: PENDING

