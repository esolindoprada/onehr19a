
# OneHR Discipline — Upstream Contract & Scope Isolation Audit

LATEST_WORKSPACE: `onehr19a(20260821-090735).md`  
LATEST_WORKSPACE_SHA256: `937ad21d8008301f436ec93641e95178a740d45473ec81834cc27daba6e14ab2`  
TARGET_ADDON: `onehr_discipline`  
WRITE_SCOPE: target addon only

## Supplied target baseline
The latest workspace contains exactly 11 target scaffold files:
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

Executable target source is generic tutorial scaffolding. The Apps description
contains older Discipline product intent but is not an accepted implementation.

## Verified current upstream contracts
- PASS — root `ONEHR-EDG-V1` exists in the supplied workspace.
- PASS — canonical CoreHR employee facade is `hr.employee`.
- PASS — `onehr.mixin.approvable` source contract exists.
- PASS — Workflow source marks approval Executed only through
  `onehr_mark_approval_executed(...)`.
- PASS — accepted Appraisal service
  `onehr_discipline_feedback_payload()` exists and is evidence-only.
- PASS — OneHR root menu `onehr_base.menu_onehr_root` exists.
- PASS — hard dependencies required by the authoritative Discipline product spec
  are already present in the suite workspace.

## Architecture reconciliation
The legacy Apps description named 8 Discipline models. The authoritative 25-addon
specification later identifies exactly 2 core Discipline models. Root architecture
authority therefore requires the later approved suite contract to control model
ownership. Legacy features are preserved inside Case/Sanction rather than by
inventing persistent models not present in the authoritative spec.

## Soft ownership
No static ORM dependency is introduced to Document, Payroll Bridge, Employment
Contract, Appraisal, PnP, Branch, Analytics or Integrations API.

## Scope isolation
No sibling OneHR source file is emitted or modified by this package.

UPSTREAM_CONTRACT_AUDIT: PASS  
SCOPE_ISOLATION_RESULT: PASS_FOR_PACKAGE

