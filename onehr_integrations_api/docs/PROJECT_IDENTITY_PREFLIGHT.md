# OneHR Integrations API — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_integrations_api`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build  
TASK: `ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831`  
ATTEMPT: 2/2  
WRITE_SCOPE: `onehr_integrations_api` only

## Authoritative baseline

- OneHR Enterprise Architecture v2 and Master Model Registry v1 ownership rules.
- Approved 25-addon topology and latest user-supplied OneHR workspace latest workspace dump uploaded 2026-08-31 plus the first complete Windows activation traceback.
- Root `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md` (ONEHR-EDG-V1).
- Supplied Integrations API product description naming REST/Webhooks/API Keys/Scopes/Throttling/Retry/Audit/OpenAPI.
- Accepted sibling model-service contracts; sibling source is read-only for this build.
- Odoo 19 CE native security/HTTP/ORM ownership.

## Supplied target baseline

The target addon is a generic tutorial scaffold: manifest `0.1`, dependency only `base`,
commented tutorial model/routes, generic views/demo and broad placeholder `base.group_user` ACL.
No accepted Integrations API business implementation exists in that scaffold.

ROOT_CAUSE_CLASSIFICATION_FOR_REBUILD: `ADDON_SOURCE_FAILURE`

## Approved product-owned persistent models — exactly five

1. `onehr.api.key`
2. `onehr.api.scope`
3. `onehr.webhook`
4. `onehr.api.log`
5. `onehr.api.queue`

Native transient extension: `res.config.settings` only.

## Hard dependency

Exactly `onehr_security`. It provides OneHR Base/mail/security transitively. Business-domain
addons remain soft so the API adapter does not reverse dependency ownership.

## Forbidden architecture drift

No duplicate employee/attendance/leave/payroll/document/learning/appraisal/talent/policy/SOP/JD
masters; no generic arbitrary model/method API; no business `sudo()`; no broad base-user CRUD;
no hard dependency on optional domain addons; no sibling source edit; no plaintext API secret
storage; no security weakening to make endpoints pass.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING


## Attempt-2 runtime repair preflight

Windows activation of Attempt 1 failed while validating `view_onehr_webhook_search`.
The `dead_letters` filter used domain `[("failed_count", ">", 0)]`, while
`onehr.webhook.failed_count` was a non-stored computed field with no search method.

ROOT_CAUSE_CLASSIFICATION_FOR_RUNTIME_REPAIR: `ADDON_SOURCE_FAILURE`

The bounded correction is limited to making that approved metric searchable while
preserving the filter, model ownership, dependencies, security, and UI contract.
