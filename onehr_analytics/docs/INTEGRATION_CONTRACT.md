# OneHR Analytics — Integration Contract

## Ownership
Analytics owns KPI definitions, snapshot evidence, thresholds/trends, dashboard presentation,
favorites, scheduled KPI generation and drill-through metadata. It does not own source
transactions.

## Hard dependency
Exactly `onehr_security`. This gives the addon the approved OneHR security/base/mail foundation
without hard-coupling Analytics to transaction domains.

## Fixed model-aggregate allow-list
- `hr.employee`
- `hr.applicant`
- `onehr.recruitment.source.metric`
- `hr.attendance`
- `onehr.leave.request`
- `onehr.learning.session`
- `onehr.learning.enrollment`
- `onehr.appraisal.form`
- `onehr.payroll.export`
- `onehr.talent.pool`
- `onehr.succession.plan`
- `onehr.discipline.case`

A source model is usable only when installed and readable by the current user. Company scope is
always appended by Analytics. Branch scope fails closed unless `branch_id` exists and an exact
`onehr.branch` can be resolved.

## Explicit soft KPI services
### Appraisal
`onehr.appraisal.form.onehr_appraisal_kpi_snapshot(company)`
Supported numeric facts include appraisal count, closed count, completion rate and average final
score.

### Learning
`onehr.learning.session.onehr_learning_kpi_snapshot(company, date_from, date_to)`
Supported facts include sessions, learners, training hours, completion rate, certificates,
actual cost and cost per learner.

### Career / Succession
`onehr.talent.pool.onehr_career_kpi_snapshot(company)`
Supported facts include active/high-potential talent, succession plan count/coverage, bench
strength and readiness.

Source addons keep their own permission checks. Analytics does not `sudo()` those calls.

## Integrations API
`onehr_integrations_api` remains owner of HTTP routes, API keys, HMAC, CORS, throttling and
retry transport. Analytics exposes only a model-level `onehr_analytics_kpi_feed()` suitable for
a downstream adapter; it does not publish unauthenticated endpoints.

## Branch
`onehr_multicompany_branch` remains branch-master owner. Analytics stores only an optional
`branch_code` soft reference to avoid a hard reverse dependency.
