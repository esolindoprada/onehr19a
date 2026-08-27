# onehr_employment_contract — Integration Contracts

## Core HR / Odoo native
`hr.version` owns live employment contract dates, trial end and wage. OneHR stores
legal process/evidence and references the exact native version. Renewal uses Odoo's
native `hr.employee.create_contract(date)` path.

## Workflow Approval (hard dependency)
`onehr.contract` extends `onehr.mixin.approvable`. Contract approval and termination
approval use structured source snapshots and routing context. Source state/execution
remains owned here; the approval engine owns routing/decision evidence.

## Base lifecycle checklist (transitive through CoreHR)
Executing approved termination requires an active/effective `TERMINATION` checklist
template and allocates `onehr.checklist.instance` as clearance evidence.

## Document (soft)
No hard relation. `document_template_code` resolves an installed `onehr.document.template`
at runtime and opens `wizard.document.generate` with employee/company/source/date
context. After a governed contract document exists, **Request E-Signature** delegates to
OneHR Document's own current document-version e-sign action. Document Manager authority
remains authoritative; this addon never bypasses it. If `onehr_document` is not installed,
both document actions fail clearly without changing contract state.

## Payroll/work entries (soft, future owner)
`_onehr_after_contract_activation()` and `_onehr_after_contract_termination()` are
narrow extension hooks. This addon does not invent payroll/work-entry ownership.

## Recruitment (no reverse dependency)
Recruitment owns applicant/preboarding. Employment Contract does not inherit or edit
Recruitment models, avoiding a reverse dependency. A later approved orchestration
addon/hook may create a contract after hire without changing this ownership boundary.

## Assignment / Offboarding
Assignment remains owner of placement/movement. This addon does not archive employees
on termination; retirement/offboarding remains the owner of broader exit orchestration.


## Line-manager privacy boundary
Contract Line Manager is deliberately not granted private `hr.employee`, `hr.version`,
OneHR position/grade/engagement-type ACLs. Contract views expose controlled display-only
labels, and the Employee smart button routes line managers to native `hr.employee.public`.
Contract Officers/Managers retain the governed private HR navigation needed for operations.
