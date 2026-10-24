
# OneHR PnP — Upstream Contract & Scope Isolation Audit

LATEST_WORKSPACE: `onehr19a(20260821-075108).md`  
LATEST_WORKSPACE_SHA256: `cbade2fc9120f9eedd61ae0b335143d14a9201110d51c1c69a89be31c85e1227`  
TARGET_ADDON: `onehr_pnp`  
WRITE_SCOPE: target addon only

## Supplied target baseline
The latest workspace contains 11 PnP scaffold file paths:
- `__init__.py`
- `__manifest__.py`
- `controllers/__init__.py`
- `controllers/controllers.py`
- `demo/demo.xml`
- `models/__init__.py`
- `models/models.py`
- `security/ir.model.access.csv`
- `static/description/index.html`
- `views/templates.xml`
- `views/views.xml`

The runtime source is still the generic tutorial scaffold. Its Apps description
is treated as the approved PnP product intent and is preserved by this Direct Full build.

## Verified upstream contracts
- PASS — Root Guardrail ONEHR-EDG-V1 present
- PASS — PnP product contract names onehr.policy
- PASS — PnP product contract names onehr.policy.ack
- PASS — PnP product contract names onehr.policy.evidence
- PASS — PnP hard dependency contract contains Security
- PASS — Workflow approvable mixin present
- PASS — Workflow executed-source hook present
- PASS — Document header model present
- PASS — Document version model present
- PASS — Document version issue action present
- PASS — OneHR SOP current implementation present
- PASS — OneHR root menu present

Integration decisions:
- PnP uses `onehr.mixin.audit` rather than duplicating chatter/activity ownership.
- PnP uses `onehr.mixin.approvable` and leaves approval routing/decision evidence
  to OneHR Workflow Approval.
- Published policy snapshots use OneHR Document header/version ownership.
- PnP does not duplicate `onehr_sop`; only optional SOP code references are kept.
- Portal, Analytics, Branch and Integrations API remain soft/downstream.
- No sibling OneHR source file is emitted or modified by this package.

SCOPE_ISOLATION_RESULT: PASS_FOR_PACKAGE  
UPSTREAM_CONTRACT_AUDIT: PASS

