# onehr_document — Integration Contracts

## onehr_corehr

- `hr.employee` is referenced by `employee_id`.
- Safe directory key `onehr_employee_number` may be displayed or used in bounded
  template variables.
- OneHR Document does not add `onehr.employee.document` and does not move employee
  master ownership.

## onehr_security

- Reuses `onehr.audit.log._log_event()` for high-risk append-only evidence.
- Reuses `Sensitive Data Reader` and `Restricted Data Reader` as explicit
  sensitivity gates.
- Business authorization happens before audit logging; the document addon itself
  contains no `sudo()` authorization bypass.

## onehr_workflow_approval

No hard dependency. Approval evidence stays canonical in
`onehr.approval.request/decision`. A source addon may link an approved business
record to `onehr.document` using source_model_id/source_res_id without copying
approval evidence.

## onehr_multicompany_branch

No hard dependency. Legal-company isolation is enforced now. A later branch-aware
bridge may further narrow records, but must not reverse dependency ownership or
expand Odoo allowed-company access.

## onehr_integrations_api

Soft integration only. `onehr.esign.transaction.dispatch_to_provider()` is the
stable provider-dispatch hook and `apply_provider_status()` is the controlled
status update API. This addon stores no external credential.

## onehr_portal_self_service / downstream domains

Downstream addons reference `onehr.document` / `onehr.document.version`.
They must not copy attachment binaries into domain-specific records and must not
publish a download route that bypasses model/attachment security.
