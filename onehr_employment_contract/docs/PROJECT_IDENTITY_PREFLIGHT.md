# onehr_employment_contract — Project Identity Preflight

PROJECT: OneHR NEW
ADDON: onehr_employment_contract
TARGET: Odoo 19 Community Edition
DELIVERY: Direct Full Addon Build

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1 / approved model ownership decisions.
- OneHR 25 Addons Specification for `onehr_employment_contract`.
- Latest user-supplied OneHR workspace export dated 2026-08-14.
- Current accepted contracts of onehr_base, onehr_security, onehr_corehr,
  onehr_workflow_approval, onehr_document and onehr_recruitment.
- Odoo 19 native `hr.employee` / `hr.version` contract behavior.

PRESERVATION RULE:
- Core custom models remain `onehr.contract` and `onehr.contract.template`.
- Odoo `hr.version` is canonical for employment/contract dates, trial end and wage.
- OneHR contract is legal/workflow/document/evidence wrapper, never parallel employment facts.
- Hard dependencies exactly: onehr_corehr, onehr_security, onehr_workflow_approval.
- onehr_document and onehr_payroll_bridge remain soft integration boundaries.

ALLOWED CHANGE:
- Replace the generic scaffold with a coherent registry-preserving enterprise implementation.
- Add fields/methods/views/security/tests/docs on the approved two models.
- Use existing base lifecycle checklist and approval engine through approved contracts.
- Soft-detect onehr_document without hard dependency.

FORBIDDEN CHANGE:
- Create a parallel `hr.contract`/employee master or duplicate canonical employment truth.
- Change ownership in CoreHR, Assignment, Recruitment, Payroll, Document or Offboarding.
- Add/remove hard dependency without architecture approval.
- Edit sibling addons.
- Use UI visibility as security or business sudo to bypass access.

CURRENT VERIFIED STATUS:
- Incoming onehr_employment_contract is generic scaffold 0.1 with base-only dependency.
- Direct Full source package is being reconstructed under this preflight.
- Windows/Odoo runtime acceptance is not executed in this build environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD
