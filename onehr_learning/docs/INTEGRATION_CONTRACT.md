# OneHR Learning — Integration Contract

## Ownership
Learning owns course/session/enrollment/training-attendance/certificate/vendor/budget/cost facts.
It does not own worker, work attendance, generic leave, generic document, payroll, portal,
analytics transport, API authentication, branch master or external LMS transport.

## Hard integration
`onehr.mixin.approvable` from `onehr_workflow_approval` is used by Enrollment.
The Learning transaction remains the source business-state owner:
Draft → Requested → Approved → Enrolled/Waitlisted → Attended → Passed/Failed → Certified,
with Rejected/Cancelled/No Show as governed alternate states.

## Soft integrations
- Time Off: `action_generate_training_leave()` resolves accepted Time Off models only when
  installed and creates/submits under the participant's own Time Off authority; no sudo.
- Attendance: training attendance remains local evidence. Optional explicit synchronization
  uses accepted `hr.attendance.onehr_ingest_interval()` only when Attendance is installed
  and the actor also has Attendance Officer authority.
- Document: issued certificate may render its QWeb PDF and create accepted Document/version
  records only when Document is installed and the actor has Document Officer authority.
- Payroll Bridge: cost/budget methods expose controlled reimbursement payloads; transport
  and payroll execution remain downstream-owned.
- Portal: read-only participant payload service; no public controller is owned here.
- Analytics: KPI snapshot service exposes training hours, completion, certification and cost facts.
- Integrations API / LMS / SCORM / xAPI: authenticated transport owner may call stable Learning
  service methods. Learning defines no public token/webhook endpoint.
- Branch: company is the current security partition; branch stays a downstream extension.

No sibling source modifications are part of this build.
