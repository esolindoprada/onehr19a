# OneHR Discipline — Integration Contract

## OneHR CoreHR — hard owner
Discipline references canonical `hr.employee`, employee number, department/job
and line manager. It does not create a parallel employee model.

## OneHR Security — hard owner
Discipline adds domain-specific roles/rules but does not replace OneHR security
role/audit ownership.

## OneHR Workflow Approval — hard owner
`onehr.discipline.sanction` inherits `onehr.mixin.approvable`.

Discipline supplies:
- `_approval_payload()`
- `_approval_branch_scope_key()`
- `_approval_rule_context()`
- `_approval_cancel_guard()`
- `_on_approval_finalized(decision, request)`
- `action_submit_for_sanction_approval()`
- `action_execute()`

Workflow Approval owns routing, approver eligibility, levels, delegation,
escalation and decision evidence. Discipline owns sanction business state.
The approval request becomes Executed only after Discipline successfully executes
the approved sanction.

## OneHR Appraisal — soft
`action_refresh_appraisal_feedback()` dynamically calls the accepted
`onehr_discipline_feedback_payload()` service when Appraisal is installed.
No sudo is used. Appraisal HR authority remains mandatory and Appraisal never
creates Discipline records.

## OneHR PnP — soft
`policy_reference` remains a text reference. `action_open_policy_reference()`
uses a runtime model check and normal PnP access. Discipline does not own policy
versions or policy acknowledgement.

## OneHR Document — soft
`onehr_discipline_document_payload(reference)` supplies a restricted,
minimum-necessary archive handoff. Discipline does not statically relate to or
create Document records because Document is not a hard dependency.

## Payroll Bridge — soft
Discipline may own an approved deduction request as part of the sanction.
`onehr_discipline_payroll_payload(period_start, period_end, company)` exposes
executed requests. `onehr_record_payroll_execution(...)` records adapter result
only. Discipline never calculates payroll, posts payslips or mutates accounting.

## Employment Contract — soft
`onehr_discipline_contract_payload(employee, company)` exposes executed
probation/termination-review outcomes. Contract lifecycle changes remain with
Employment Contract.

## Analytics / Integrations API — downstream
`onehr_discipline_kpi_snapshot(...)` exposes case count, open/closed count,
SLA overdue count, repeat-offense rate, average resolution days, violation trend,
case-state distribution and sanction distribution. HTTP/API transport and
dashboard persistence remain downstream ownership.

## Branch — downstream extension
`branch_scope_key` participates in sanction approval context and remains a stable
extension key without reverse dependency on `onehr_multicompany_branch`.
