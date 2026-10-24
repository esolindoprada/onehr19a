# OneHR Integrations API — Latest Workspace Alignment

BASELINE_REFERENCE: `onehr19a.md`  
BASELINE_UPLOAD_TIMESTAMP: `2026-08-31T11:35:52Z`  
TARGET_ADDON: `onehr_integrations_api`  
TARGET_PLATFORM: Odoo 19 Community Edition  
WRITE_SCOPE: `onehr_integrations_api` only

## Target baseline confirmed

The latest supplied target is still a generic tutorial scaffold (`0.1`, `base` only, commented
sample controller/model/view/demo and placeholder broad ACL). It does not implement the advertised
Integrations API product contract.

The latest supplied product description continues to name the following owned integration models:

1. `onehr.api.key`
2. `onehr.api.scope`
3. `onehr.webhook`
4. `onehr.api.log`
5. `onehr.api.queue`

`res.config.settings` remains a native transient extension, not a sixth persistent model.

The advertised sample routes include Health, Employees, Attendance, Recruitment Applicant,
Time Off Request, Approval Events and Document e-Sign Status. The full build additionally exposes
accepted Learning, Appraisal, Career/Succession, Payroll, PnP, SOP, Job Description and Portal
service boundaries when those owner addons are installed.

## Revalidated sibling model-service boundaries

The latest workspace confirms, among others:

- Attendance: `hr.attendance.onehr_ingest_interval(payload)`.
- Appraisal: `onehr.appraisal.form.onehr_ingest_external_rating(payload)`.
- Learning: `onehr.learning.enrollment.onehr_external_enroll(payload)` and
  `onehr_ingest_external_result(payload)`.
- Career/Succession: `onehr.talent.pool.onehr_ingest_talent_assessment(payload)`.
- Document/e-Sign: `onehr.esign.transaction.apply_provider_status(...)` with provider dispatch
  retained as a soft integration extension point.

Other already-accepted Payroll/PnP/SOP/Job Description/Portal service tokens remain guarded by
source acceptance. Recruitment, Time Off and Workflow adapters use the owning models/actions under
the API key's least-privilege service user rather than fabricating new owner-side APIs.

## Architecture consequence

`onehr_integrations_api` owns transport, credential/scope enforcement, HMAC/replay/rate controls,
webhook delivery/retry and technical integration evidence. It does not become owner of HR domain
masters or workflows. Missing optional capabilities return a controlled capability-unavailable
response instead of creating duplicate business logic.

`LATEST_WORKSPACE_ALIGNMENT: PASS_FOR_SOURCE_BUILD`
`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`


## Runtime repair alignment — 2026-08-31

The latest supplied workspace contains the generated `onehr_integrations_api` Attempt-1
source and therefore matches the code that reached Odoo XML view validation. The first
complete runtime traceback proves a target-local defect in `view_onehr_webhook_search`:
`failed_count` was used in a domain while it was non-searchable. Attempt 2 preserves the
filter and makes the metric stored/searchable. No sibling contract change is required.
