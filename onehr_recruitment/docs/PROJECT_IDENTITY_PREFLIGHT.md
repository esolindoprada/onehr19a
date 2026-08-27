# OneHR Recruitment — Project Identity Preflight

## HARD GATE 0 — PROJECT IDENTITY PREFLIGHT

- PROJECT: OneHR NEW
- ADDON: `onehr_recruitment`
- TARGET PLATFORM: Odoo 19 Community Edition
- DELIVERY METHOD: Direct Full Addon Build
- AUTHORITATIVE ARCHITECTURE: OneHR Enterprise Architecture v2
- AUTHORITATIVE REGISTRY: OneHR Master Model Registry v1
- PRODUCT BASELINE: OneHR 25 Addons Specification for Odoo 19 CE
- ROOT GUARDRAIL: `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`
- ROOT GUARDRAIL CHECKSUM DECLARED IN LATEST WORKSPACE EXPORT: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`
- INTEGRITY RULE: acceptance validates the actual `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md` against the colocated `.sha256` file in the target workspace; it does not rewrite the root Guardrail.
- AUTHORITATIVE CURRENT SOURCE CONTEXT: latest complete OneHR workspace dump supplied by the user on 14 Aug 2026.

## Preservation rule

The supplied `onehr_recruitment` folder was still a generic scaffold. The rebuild therefore preserves the approved product intent and Master Model Registry, not the placeholder scaffold model.

Canonical Odoo recruitment ownership is preserved:

- applicant: `hr.applicant`
- recruitment stage: `hr.recruitment.stage`
- job: `hr.job`
- talent pool: `hr.talent.pool`

OneHR owns only the approved enterprise recruitment facts: requisition, interview template/session/score, governed offer, preboarding orchestration, and immutable source/funnel snapshot.

## Required hard dependencies

Exactly:

1. `onehr_corehr`
2. `onehr_security`
3. `onehr_workflow_approval`
4. `hr_recruitment`

`onehr_document` and `onehr_integrations_api` remain soft integrations. `onehr_multicompany_branch` is not a hard dependency; recruitment continues to respect the standard allowed-company boundary and may be extended by the branch owner later without reverse dependency.

## Allowed change

- Registry-preserving Direct Full Build replacing the generic scaffold.
- Odoo 19 compatibility hardening.
- Odoo-native recruitment extension.
- Enterprise requisition, structured interview, offer, preboarding and analytics behavior.
- Professional views, search/list quality, server authority checks, tests and governance evidence.
- Narrow soft integration with OneHR Document and future downstream owner hooks.

## Forbidden change

- `onehr.applicant`, `onehr.recruit.stage`, `onehr.job.opening`, `onehr.onboard.template`, or `onehr.talent.pool` parallel canonical models.
- Duplicate employee master or direct replacement of Odoo native applicant-to-employee conversion.
- Cross-addon source edits.
- Hard dependency on OneHR Document, Integrations API, Attendance, Timeoff, Assignment or Employment Contract.
- Broad custom-model `base.group_user` ACL.
- `sudo()` as a business-security bypass.
- Executable routing/template expressions or stored `eval`/`safe_eval` logic.
- Rewriting finalized recruitment evidence.
- Codex architecture, simplification, deletion, ownership or dependency decisions.

## Current verified status

- Full coherent source build prepared.
- Static/source acceptance must pass before deployment.
- Windows/Odoo database runtime acceptance is not executed in this build environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD
