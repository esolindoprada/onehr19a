# OneHR Career & Succession — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_career_succession`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build

## Authoritative baseline
- OneHR Enterprise Architecture v2 and Master Model Registry v1.
- OneHR 25 Addons Specification for Odoo 19 CE.
- Root OneHR Enterprise Development Guardrail v1.
- Latest user-supplied OneHR workspace.
- Odoo 19 CE native/model ownership.
- Current accepted CoreHR, Base, Appraisal and Learning contracts.

## Current supplied baseline
The supplied addon is still a generic tutorial scaffold:
- manifest version `0.1`;
- hard dependency only `base`;
- commented tutorial model/controller;
- public-route example;
- broad placeholder ACL;
- generic `views.xml` / `templates.xml`;
- no accepted Career/Succession business implementation to preserve.

## Product contract
Exactly four core models:
- `onehr.competency`
- `onehr.position.competency`
- `onehr.talent.pool`
- `onehr.succession.plan`

Hard dependencies exactly:
- `onehr_base`
- `onehr_corehr`

Soft integrations:
- `onehr_appraisal`
- `onehr_learning`
- `onehr_analytics`

Workflow:
`Draft → Proposed → Approved → Active`

Primary product outcomes:
competency dictionary, position competency matrix, high-potential talent pool,
readiness/gap analysis, succession plan for critical positions, succession coverage,
risk index, bench strength and average readiness.

## Ownership boundaries
- `hr.employee` remains the canonical employee.
- `onehr.position` remains OneHR Base ownership.
- Appraisal remains owner of appraisal score/evidence.
- Learning remains owner of courses/sessions/enrollments/certification.
- Analytics remains owner of dashboards/snapshots.
- `onehr_integrations_api` remains owner of public REST/auth/token/webhook concerns.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
