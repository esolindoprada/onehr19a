# OneHR Attendance — Integration Contracts

## onehr_assignment — soft, no hard dependency

When `onehr.assignment` exists, shift resolution may read the effective active/approved primary assignment to obtain position and work-location context. `onehr.shift.assignment.assignment_ref` is an optional `fields.Reference`. Attendance never creates, mutates or owns enterprise assignment records.

## onehr_timeoff and onehr_learning — future soft exclusion hook

`onehr.shift.assignment._onehr_exclusion_reason_for_date(day)` returns `False` in this addon. The Time Off / Learning owner may extend it later so approved leave or training suppresses false missing-punch exceptions. Attendance does not create parallel leave/training facts.

## onehr_mobile_kiosk — downstream hard dependency on Attendance

Kiosk/mobile owns device UX, token, QR/NFC and sync. It should call the governed attendance ingestion service rather than creating a parallel attendance table.

## onehr_integrations_api — adapter boundary

External API endpoints and credentials belong to the integrations addon. The stable domain service is `hr.attendance.onehr_ingest_interval(payload)`. No public controller is created here.

## onehr_payroll_bridge — downstream consumer

Payroll consumes Posted/approved attendance and native overtime metadata. This addon does not create payroll lines or accounting entries.

## onehr_analytics — downstream consumer

Analytics may read canonical attendance, exception state, lateness, early-leave, review state, rounded hours and native overtime. No analytics model is re-owned here.

## onehr_multicompany_branch — optional narrowing

Company remains the mandatory legal/security partition. `onehr.shift.branch_ref` provides an optional branch scope only when the branch model exists; this addon does not define `onehr.branch` or create a reverse dependency.
