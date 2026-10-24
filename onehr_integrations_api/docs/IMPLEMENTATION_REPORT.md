# OneHR Integrations API — Direct Full Addon Implementation Report

TASK: `ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831`  
ATTEMPT: 2/2  
VERSION: `19.0.1.0.1`  
WRITE_SCOPE: `onehr_integrations_api` only  
ROOT_CAUSE_CLASSIFICATION_FOR_REBUILD: `ADDON_SOURCE_FAILURE`

The latest user-supplied OneHR workspace (uploaded 2026-08-31 11:35:52Z) still contains the
`onehr_integrations_api` generic tutorial scaffold while its product description explicitly defines
API Keys, API Scopes, Webhooks, API Logs, Retry Queue, REST v1, throttling and cross-OneHR
integration. The scaffold is therefore replaced by the product-approved five-model integration
layer without modifying sibling addons.

Hard dependency remains exactly `onehr_security`; all HR business domains stay soft and
owner-controlled. The implementation includes REST v1, granular scopes, one-time PBKDF2 API
credentials, HMAC/replay/rate security, least-privilege service-user execution, inbound/outbound
webhooks, SSRF-aware outbound transport, retry/dead-letter, immutable audit/KPI evidence,
OpenAPI/Postman, global settings and professional Odoo 19 CE UI.

Latest workspace contract alignment was rechecked for the API product surface and accepted sibling
service boundaries. See `LATEST_WORKSPACE_ALIGNMENT.md`.

Hard Gate 11 is implemented explicitly with identifier-length/relation/XML-ID/Odoo ORM compatibility
checks in source acceptance. Hard Gates 0–15 remain mandatory and separately evidenced.

Runtime is not available in this build container, so Windows install/test/upgrade/UAT remain pending.

`ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO`


## Runtime Repair Attempt 2

The first Windows activation exposed a source/view contract defect: the Webhook search
filter `Has Dead Letters` used computed field `failed_count`, but that field was not
searchable. Repair `19.0.1.0.1` preserves the filter and makes `failed_count` stored.
A dedicated runtime regression test and source gate now prevent recurrence.

`ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE`  
`ATTEMPT: 2/2`
