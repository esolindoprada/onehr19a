
# OneHR Portal Self-Service — Integration Contract

## Portal ownership
Portal Self-Service owns authenticated employee/manager presentation, HR service catalogue,
request orchestration, request approval evidence, SLA evidence and downstream references.
It does not own canonical transactions of other HR domains.

## CoreHR — hard
`hr.employee` is the canonical worker. Portal stores references and safe display snapshots.
Approved Profile Change requests write only explicitly whitelisted scalar fields to the
canonical employee under the current HR user's normal authority.

## Security — hard
OneHR Security is a hard dependency for the shared project security foundation. Portal's
role-specific ACL/rules and model authority remain additive and least-privilege.

## Time Off — soft
For service kind `timeoff`, Portal resolves exact active `onehr.leave.type.code`, creates
`onehr.leave.request`, then calls `action_submit_for_approval()`. Time Off remains owner of
leave policy, balance, validation and approval. No sudo and no direct database mutation.

## Learning — soft
Portal calls the accepted `onehr.learning.enrollment.onehr_external_enroll(payload)` service
with external reference, employee number and exact session reference. Learning remains owner
of enrollment state, seat capacity, approval, attendance and certification.

## Appraisal — soft/read-only
My HR may call `onehr.appraisal.form.onehr_employee_appraisal_payload(employee)` under the
current user's normal Appraisal access. Portal does not create or modify appraisal evidence.

## Document — soft
Portal may create `onehr.document` and its Draft `onehr.document.version` from the submitted
attachment only when the current HR operator also has Document authority. Document remains
owner of category, lifecycle, version, retention and compliance.

## Payroll Bridge — soft/read-only
My HR may display accepted employee-safe payroll payloads from `onehr.payroll.import` under
normal payroll access. Portal never owns payroll calculations or payment state.

## Job Description / PnP / SOP / Career — soft/read-only
Portal consumes their existing employee-safe model-service contracts when installed and
accessible. Missing access omits a dashboard card; it never broadens ACL.

## Discipline
No employee-facing Discipline payload is consumed because the supplied Discipline domain is
confidential and no separately approved employee-safe Portal contract is assumed.

## Integrations API / Analytics / Branch
Authentication/API transport, analytics snapshots and branch master remain downstream-owned.
Portal exposes no public API token/webhook table and does not invent branch ownership.

