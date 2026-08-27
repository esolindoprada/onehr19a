# OneHR SOP — Upstream Contract & Scope Isolation Audit

LATEST_WORKSPACE: `onehr19a(20260821-063315).md`  
LATEST_WORKSPACE_SHA256: `56050fa212f09c3a328f75bf0f712e168d72d339c15b5d5033ee5bbb3fc66fd9`  
TARGET_ADDON: `onehr_sop`  
WRITE_SCOPE: target addon only

## Supplied target baseline

The workspace contains 10 captured `onehr_sop` files:

- `onehr_sop/__init__.py`
- `onehr_sop/__manifest__.py`
- `onehr_sop/controllers/__init__.py`
- `onehr_sop/controllers/controllers.py`
- `onehr_sop/demo/demo.xml`
- `onehr_sop/models/__init__.py`
- `onehr_sop/models/models.py`
- `onehr_sop/security/ir.model.access.csv`
- `onehr_sop/views/templates.xml`
- `onehr_sop/views/views.xml`

The supplied target is still the generic tutorial scaffold: manifest `0.1`,
`base`-only dependency, commented tutorial model/routes, generic views/templates
and demo data. No accepted SOP business workflow is present to preserve.

## Verified upstream contracts

- PASS — OneHR Base audit mixin exists
- PASS — OneHR Document header model exists
- PASS — OneHR Document version model exists
- PASS — Document version supports action_issue
- PASS — Document archive supports rendered_content_html
- PASS — Document Officer group exists
- PASS — Document Manager group exists
- PASS — OneHR Security User group exists
- PASS — OneHR root menu exists
- PASS — CoreHR employee number field exists

Integration decisions:
- SOP uses `onehr.mixin.audit` instead of duplicating chatter/activity ownership.
- SOP hard-depends on `onehr_document` and archives Published SOP content through
  `onehr.document` + `onehr.document.version`; it does not create a parallel binary
  document master.
- SOP Reader/Editor/Approver group implications use existing OneHR Security,
  Odoo HR and OneHR Document authorities rather than inventing upstream roles.
- `onehr_portal_self_service`, `onehr_analytics`, branch and Integrations API remain
  downstream model-service consumers and are not hard dependencies.
- No sibling OneHR source file is emitted or patched by this package.

SCOPE_ISOLATION_RESULT: PASS_FOR_PACKAGE  
UPSTREAM_CONTRACT_AUDIT: PASS
