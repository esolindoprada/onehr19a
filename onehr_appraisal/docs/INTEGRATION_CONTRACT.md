# OneHR Appraisal — Integration Contract

## Hard ownership
Appraisal owns:
- appraisal cycle
- employee appraisal form
- appraisal score/objective/feedback/development line

Hard dependencies are exactly `onehr_corehr` and `onehr_security`.

## CoreHR
`hr.employee` is canonical worker and manager. Appraisal stores employee references
and performance facts only. It does not duplicate person, contract or restricted CoreHR data.

## Learning — soft
Development lines may carry an exact `learning_session_reference`.
`action_push_to_learning()` calls
`onehr.learning.enrollment.onehr_external_enroll(payload)` only when Learning is installed.
The current user must also satisfy Learning's own authority. No sudo and no hard dependency.

## Analytics — soft
`onehr_appraisal_kpi_snapshot()` exposes completion rate, average final score and rating distribution.
Analytics remains owner of dashboards/snapshots.

## Career / Succession — soft
`onehr_career_feedback_payload()` exposes closed-appraisal performance/potential evidence.
Career/Succession remains owner of competency, talent-pool and succession models.

## Discipline — soft
`onehr_discipline_feedback_payload()` is HR-restricted evidence only.
Appraisal does not create discipline cases or sanctions.

## Portal — soft
`onehr_employee_appraisal_payload(employee)` is read-only under normal caller access.
Portal routing/session ownership remains downstream.

## Integrations API — soft
`onehr_ingest_external_rating(payload)` is a model service only.
Authentication, public HTTP, tokens, signatures, rate limiting, queue/retry and API
versioning remain `onehr_integrations_api` ownership.

## Multicompany / branch
Company is the hard security partition in this build. Branch remains a downstream extension.


## Privacy-safe downstream fields
Operational Participant/Manager UI uses stored safe-display employee/manager/reviewer names.
Employee number and raw private `hr.employee` references are retained for governed HR/integration
operations and are not exposed through the participant portal payload.
