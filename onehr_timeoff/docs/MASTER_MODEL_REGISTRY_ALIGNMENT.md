# OneHR Time Off — Master Model Registry / Product Baseline Alignment

The supplied product baseline explicitly identifies the following three Time Off core business models. This build creates exactly those three custom persistent model names and no additional leave-policy/balance/wizard model.

| # | Model | Implementation responsibility |
|---:|---|---|
| 1 | `onehr.leave.type` | Effective leave policy/type; annual/sick/special/training/unpaid categories; allocation/approval rules; grade/tenure eligibility; accrual, seniority, carry-over and team-conflict policy. |
| 2 | `onehr.leave.request` | Employee leave/absence transaction; work-schedule duration; team-calendar conflict; approval workflow; frozen entitlement reservation; lifecycle Draft → Approval → Approved/Rejected → Done plus governed cancellation. |
| 3 | `onehr.leave.allocation` | Entitlement ledger, opening balance, automatic accrual, carry-over, adjustment and durable mass-allocation batch/child evidence. |

## Odoo / sibling ownership preserved

- `hr.employee`: Odoo/Core HR canonical worker identity; inherited only for Time Off smart navigation/counts.
- `hr.department`: Odoo-native organization reference through employee placement.
- `onehr.grade`: OneHR Base-owned grade reference used for eligibility.
- `onehr.approval.*` + `onehr.mixin.approvable`: owned by `onehr_workflow_approval`; Time Off only consumes the source-side contract.
- `onehr.audit.log` / role authority: owned by `onehr_security`.
- Attendance/shift facts: remain `onehr_attendance` owned.
- Payroll work entries, payroll calculations and posting: remain payroll-owned.

## Deliberate non-invention

No custom model is created for:

- `onehr.leave.balance`;
- `onehr.leave.accrual.rule`;
- `onehr.leave.carryover`;
- `onehr.leave.mass.wizard`.

Balance is derived from confirmed allocation evidence minus approved/done request reservations. Accrual/carry-over policy lives on `onehr.leave.type`. Mass allocation uses `onehr.leave.allocation` with `allocation_scope='mass'` and durable generated child allocations, providing modal/wizard-like UX without an unapproved transient model.

## Effective-dating classification note

The accessible supplied sources identify the three model names and functional obligations but do not expose their exact Master Model Registry ED-number labels. This build therefore refuses to fabricate ED0–ED5 labels. Runtime/final architecture acceptance must compare these three models against the authoritative Registry v1 before `MOVE_FORWARD_READY` is set to YES.

REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE_RESULT: PASS
REGISTRY_ED_LABEL_VERIFICATION: PENDING_AUTHORITATIVE_REGISTRY_CHECK
RUNTIME_REGISTRY_RESULT: PENDING
