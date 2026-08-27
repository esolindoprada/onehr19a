# OneHR Job Description — Integration Contract

## Hard owners
Job Description consumes canonical `onehr.position`, `onehr.job.family`, `onehr.grade`,
`hr.job` and `hr.department` from OneHR Base/Odoo. It does not duplicate them.

## Recruitment — soft
`onehr_jd_recruitment_payload(position=..., position_code=...)` exposes only the current
published JD information useful for requisition/candidate communication:
purpose, responsibilities, qualification/education/experience/skills and HSE risk level.
Recruitment remains owner of applicant/requisition/offer records.

## Appraisal — soft
`onehr_jd_appraisal_payload(...)` exposes current published KPI and competency snapshots.
Appraisal remains owner of KPI targets, ratings, rater evidence and development plans.

## Career & Succession — soft
Draft JD versions can call `action_refresh_competency_snapshot()`. The method dynamically
checks for `onehr.position.competency` and reads it under the caller's normal Career
authority. It never adds a hard dependency and never uses `sudo()`.

## Portal — downstream
`onehr_jd_portal_payload(...)` returns a safe subset of current published business content.
HTTP routes, authentication, public/session policy and employee self-service ownership
remain `onehr_portal_self_service`.

## Integrations API / BI — downstream
`onehr_jd_api_payload(jd_reference)` and `onehr_jd_export_payload()` are model-service
boundaries only. API tokens, signatures, route versioning, throttling, retry queues and
webhooks remain `onehr_integrations_api`.

## Analytics
`onehr_jd_kpi_snapshot(company=None)` exposes:
- active position count;
- position JD count;
- published position JD count;
- coverage %;
- average current version age;
- overdue review count.

Analytics remains owner of dashboards/snapshots.
