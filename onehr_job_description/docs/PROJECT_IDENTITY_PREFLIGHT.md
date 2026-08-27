# OneHR Job Description — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_job_description`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build

## Latest supplied target baseline
The latest OneHR workspace still contains the generic tutorial scaffold:
- manifest version `0.1`;
- dependency only `base`;
- placeholder author/description;
- commented tutorial model;
- commented public HTTP routes;
- generic `views.xml` / `templates.xml`;
- demo scaffold;
- no accepted Job Description business workflow.

No business feature is lost by replacing that scaffold.

## Product contract
Core models exactly:
- `onehr.jd`
- `onehr.jd.version`

Hard dependencies exactly:
- `onehr_base`
- `onehr_security`

Soft integrations:
- `onehr_recruitment`
- `onehr_appraisal`
- `onehr_career_succession`
- `onehr_portal_self_service`
- downstream `onehr_integrations_api` / `onehr_analytics` service consumers where enabled

Core scope:
- JD per position;
- purpose and responsibilities;
- KPI and competency linkage/snapshots;
- K3/HSE risks and controls;
- job-family templates;
- version/history;
- portal publication boundary;
- export to Recruitment/Appraisal;
- Draft → Review → Approved → Published;
- JD register and version comparison;
- coverage per position and average version age;
- external JD source import/capture.

## Canonical ownership
- `onehr.position` remains OneHR Base position master.
- `hr.job`, `hr.department`, `hr.work.location` remain Odoo-native masters.
- `onehr.job.family` and `onehr.grade` remain OneHR Base.
- Career/Succession owns competency master/position competency requirements.
- Recruitment owns requisitions/applicants/interviews/offers.
- Appraisal owns cycles/forms/scores.
- Portal owns public/self-service routes/session policy.
- Integrations API owns HTTP authentication/tokens/webhooks.
- JD does not duplicate any of these owners.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
