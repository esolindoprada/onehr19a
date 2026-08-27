# OneHR PnP — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_pnp`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build  
WRITE_SCOPE: `onehr_pnp` only

## Latest supplied target baseline
The supplied target still contains the generic Odoo tutorial scaffold:
manifest `0.1`, `base`-only dependency, commented tutorial model, commented
public tutorial routes, generic views/templates/demo and a broad tutorial ACL.

Its `static/description/index.html` nevertheless supplies the intended PnP
product contract: Policies & Procedures repository, version/change log,
Draft→Approved→Published→Review→Archived, targeted audience, acknowledgement,
evidence, review scheduler, notifications, reports/analytics, Portal, multi-company,
three persistent core models plus `res.config.settings`, and exact hard/soft dependencies.

## Approved target structure
Persistent business models exactly:
- `onehr.policy`
- `onehr.policy.ack`
- `onehr.policy.evidence`

Transient extension:
- `res.config.settings`

Hard dependencies exactly:
- `onehr_security`
- `onehr_document`
- `onehr_workflow_approval`

Soft/downstream:
- `onehr_portal_self_service`
- `onehr_analytics`
- `onehr_sop`
- `onehr_multicompany_branch`
- `onehr_integrations_api`

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
