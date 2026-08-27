# OneHR Recruitment — Master Model Registry Alignment

| # | Model | Classification | ED | Ownership / implementation contract |
|---:|---|---|---|---|
| 1 | `hr.applicant` | INHERIT_ODOO | ED3 | Canonical applicant/pipeline record; OneHR adds requisition, interview, offer and preboarding links only |
| 2 | `hr.recruitment.stage` | INHERIT_ODOO | ED1 | Canonical recruitment stage; OneHR adds enterprise phase/SLA/governance flags |
| 3 | `hr.job` | INHERIT_ODOO | ED1 | Canonical job; OneHR adds requisition demand drill-down and snapshot action |
| 4 | `hr.talent.pool` | INHERIT_ODOO | ED1 | Canonical talent pool; OneHR adds target job/review governance |
| 5 | `onehr.recruitment.requisition` | NEW persistent | ED3 | Governed recruitment demand and approval-source state |
| 6 | `onehr.interview.template` | NEW persistent | ED2 | Versioned/effective structured interview definition |
| 7 | `onehr.interview.session` | NEW persistent | ED3 | Scheduled interview and frozen template identity/evidence |
| 8 | `onehr.interview.score` | NEW persistent | ED3 | Per-rater finalized score evidence with superseding correction |
| 9 | `onehr.offer` | NEW persistent | ED3 | Governed compensation/offer decision and approval source |
| 10 | `onehr.preboarding` | NEW persistent | ED3 | Hire/preboarding orchestration linked to native employee conversion and generic HIRE checklist |
| 11 | `onehr.recruitment.source.metric` | NEW persistent | ED4 | Immutable period/source funnel snapshot |

## Rejected legacy/scaffold ownership

The following are intentionally not created because they conflict with the approved Registry/native-first architecture:

- `onehr.job.opening`
- `onehr.applicant`
- `onehr.recruit.stage`
- `onehr.onboard.template`
- `onehr.talent.pool`
- `onehr_recruitment.onehr_recruitment`

## Dependency contract

Hard dependencies are exactly `onehr_corehr`, `onehr_security`, `onehr_workflow_approval`, `hr_recruitment`.

Soft integration contracts:

- `onehr_document`: offer-letter generation through `wizard.document.generate` when installed; no hard reverse dependency.
- `onehr_integrations_api`: future job-board/webhook/e-sign/API adapter owner; no endpoint or credential ownership in recruitment.
- downstream hire owners (employment contract, assignment, attendance/access provisioning): extend `_onehr_post_hire_orchestration()` when their architecture is implemented; recruitment does not create their records prematurely.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
