# OneHR Retirement & Offboarding — Integration Contract

## Core HR — hard owner
`hr.employee` is canonical. Offboarding stores a case-time snapshot and exposes derived `onehr_*` navigation/exit indicators only. It does not create a parallel employee master.

## Workflow Approval — hard owner
`onehr.offboarding` inherits `onehr.mixin.approvable`. The source owns its case state and execution; Workflow Approval owns route/step/decision/delegation/SLA evidence. Approval transitions the case to In Progress and then marks the approved request executed only after checklist generation succeeds.

## Employment Contract — soft sibling owner
Legal employment-contract termination remains `onehr_employment_contract` ownership. Offboarding resolves `onehr.contract` at runtime, writes the contract owner's approved termination fields under ordinary ACLs, delegates to `action_request_termination_review()` / `action_execute_termination()`, and mirrors only a disposition/reference. No hard dependency and no duplicate contract model are introduced.

## Payroll Bridge / Finance — soft downstream
`onehr_offboarding_payroll_payload()` requests settlement inputs but explicitly returns `calculate_amount=False`. `onehr_record_final_benefit_result()` stores only downstream confirmation/reference/amount evidence. Payroll rules and calculation remain Payroll ownership.

## Document — soft downstream
`onehr_offboarding_document_payload()` exposes source context/reference. Document/template/e-sign generation remains Document ownership.

## Portal Self Service — soft downstream
`onehr_offboarding_portal_payload()` and exit-interview portal payloads are sanitized model-service contracts. HTTP routes, sessions, signup/authentication and public ACLs remain Portal ownership.

## Integrations API / SSO — soft downstream
`onehr_offboarding_api_payload()` and `onehr_offboarding_access_revoke_payload()` are transport-neutral. API keys, HTTP, webhooks, signatures, retry queues and external SSO calls remain Integrations API ownership.

## Analytics — soft downstream
`onehr_offboarding_kpi_snapshot()` returns current case/closure/retirement/resignation/overdue/time-to-close/reason metrics. KPI tile/snapshot persistence remains Analytics ownership.

## Branch — soft downstream
`branch_scope_key` is a routing/extension key only. No branch master or branch ACL model is duplicated here.
