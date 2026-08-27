# OneHR Mobile Kiosk — Integration Contracts

## onehr_attendance — HARD dependency and canonical transaction owner

Hard dependency is exactly `onehr_attendance`. Current accepted Attendance documentation explicitly
states that Mobile Kiosk owns device UX/token/QR/NFC/sync and must use the governed attendance
ingestion service rather than create a parallel attendance table.

This addon implements that direction:

- check-in → `hr.attendance.onehr_ingest_interval(payload)`
- checkout → closes the employee's canonical open `hr.attendance`
- source channel/system/reference/device metadata are retained on canonical Attendance
- service-user ACL and record rules remain active
- no business `sudo()`.

## onehr_timeoff — SOFT dependency

There is no manifest dependency on Time Off.

When the Time Off models exist:

- balance summary uses `onehr.leave.allocation.balance_for_employee(...)`
- quick request looks up the active policy by company/code/effective date
- request is created as `employee.user_id`
- `action_submit_for_approval()` is called as the employee user
- Time Off's own ACL, record rules, validation, entitlement and approval remain authoritative.

If Time Off is absent or the employee has no self-service authority, the kiosk reports the
capability as unavailable or leaves the event in controlled failure/dead-letter evidence.

## onehr_multicompany_branch — optional

Company remains the mandatory legal/security partition. This addon does not define `onehr.branch`
or add a reverse hard dependency. A future branch-owner extension may narrow device scope.

## onehr_integrations_api — adapter owner

Public/external REST, third-party device webhook and API-key/throttling concerns remain owned by
`onehr_integrations_api`. This addon provides authenticated first-party kiosk routes and domain
services only.

## onehr_base / onehr_corehr / onehr_security

These are reached transitively through Attendance and remain owners of audit mixin, employee
number, work-location metadata and security foundation. Their source is not rewritten here.
