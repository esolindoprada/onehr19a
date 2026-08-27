# OneHR Career & Succession — Integration Contract

## Core ownership
Career/Succession owns competency dictionary, position competency requirements,
talent-pool facts and succession plans only.

## Base / CoreHR — hard
- `onehr.position` is the canonical position.
- `hr.employee` is the canonical employee.
- Department/job/company/grade facts are consumed, not duplicated.

## Appraisal — soft
When installed, Talent may refresh latest closed Appraisal performance/potential
evidence through the accepted Appraisal Career feedback service. No hard dependency,
no `sudo()`, and Appraisal access authority remains authoritative.

## Learning — soft
When installed, Talent may summarize completed/passed/certified Learning enrollment
evidence under normal Learning access. Career/Succession does not create courses,
sessions, attendance or certificates.

## Analytics — soft/downstream
`onehr_career_kpi_snapshot()` exposes:
- active talent count;
- high-potential count;
- succession plan count;
- succession coverage %;
- average bench strength;
- average readiness.

Analytics remains owner of dashboards/snapshots.

## Portal — downstream
`onehr_employee_career_payload(employee)` exposes only caller-owned career facts.
Portal route/session ownership remains downstream.

## Integrations API — downstream
`onehr_ingest_talent_assessment(payload)`, `onehr_talent_bi_payload()` and
`onehr_competency_bi_payload()` are model services only. Authentication, HTTP routes,
tokens, signatures, throttling, versioning and retry queues remain
`onehr_integrations_api` ownership.
