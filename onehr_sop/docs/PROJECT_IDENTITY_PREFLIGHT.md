
# OneHR SOP — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_sop`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build

## Supplied target baseline
Latest supplied workspace still contains a generic tutorial scaffold:
- manifest version `0.1`;
- dependency only `base`;
- generic author/description;
- commented tutorial model;
- commented `auth='public'` tutorial routes;
- generic `views.xml` / `templates.xml`;
- demo scaffold;
- no accepted SOP workflow or business model.

Direct Full replacement therefore does not delete accepted SOP functionality.

## Approved product contract
Persistent business models exactly:
- `onehr.sop`
- `onehr.sop.version`
- `onehr.sop.ack`

Hard dependencies exactly:
- `onehr_security`
- `onehr_document`

Soft:
- `onehr_portal_self_service`
- `onehr_analytics`
- downstream `onehr_integrations_api` model-service consumer

Workflow:
Draft → Review → Approved → Published → Obsolete

Core capability:
versioning, targeted publication by unit/role, employee Read & Agree timestamp,
review/retention, compliance rate per unit, overdue SOPs, acknowledgement rate,
days from publish to 90% acknowledgement, audit CSV export and archived documentation.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING

