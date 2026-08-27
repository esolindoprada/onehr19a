# onehr_timeoff — Integration Contracts

## onehr_corehr

- `hr.employee` remains canonical employee identity.
- Time Off consumes employee company, department, manager, resource calendar, OneHR grade and native employment version start for eligibility.
- Time Off does not duplicate worker, department, job, grade or assignment masters.
- HR-only employee smart buttons are additive navigation and do not widen native ACLs.

## onehr_security

- Time Off User/Manager/HR roles imply the minimum OneHR security foundation needed for each role.
- No `base.group_user` custom-model CRUD.
- Self/team/company record rules are explicit.
- Model business methods enforce state/evidence immutability independently of button visibility.

## onehr_workflow_approval

- `onehr.leave.request` consumes `onehr.mixin.approvable`.
- The generic approval engine owns approval rule/path/decision evidence.
- Time Off owns leave state and performs entitlement reservation only after final approval.
- `_approval_payload()` freezes minimum-necessary request facts for approval evidence.
- `_approval_rule_context()` supplies manager, department, leave category/type, days and paid/unpaid facts for structured routing.
- `_on_approval_finalized()` remains the source-domain callback.

## onehr_attendance — soft integration only

Hard dependency is intentionally absent. Time Off provides:

- `_onehr_timeoff_validate_attendance_hook()` for a deployment-specific attendance/shift extension to validate or block scheduled work conflicts;
- team-calendar overlap control inside Time Off even when Attendance is absent.

This prevents reverse/circular dependency while preserving a clear extension point.

## payroll bridge / payroll localization — downstream only

`onehr_timeoff_payroll_payload()` returns request id/no, employee, dates, days, leave type code, paid/unpaid flag and state. Payroll adapters may consume it later. Time Off does not create payroll work entries, salary rules, payslips, GL entries or localization rules.

## onehr_multicompany_branch — future soft extension

Company is the current hard security partition. No `onehr.branch` field is invented here because the branch addon is not a hard dependency. A future branch owner may narrow Time Off using an approved extension contract without reversing dependency direction.

## onehr_integrations_api — downstream API adapter

The product baseline allows mobile/portal leave requests when the integrations addon is installed. This addon exposes conventional model create/actions and does not own API authentication or routes.

## onehr_analytics — downstream consumer

Request fields include requested days, state, department, leave type and approval lead time; allocation fields include allocated/used/available values. Analytics may consume them without a hard dependency back from Time Off.
