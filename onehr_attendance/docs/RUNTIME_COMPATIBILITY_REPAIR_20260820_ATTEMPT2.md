# OneHR Attendance — Runtime Compatibility Repair Attempt 2 — 2026-08-20

TASK:
Dependency repair discovered while activating `onehr_mobile_kiosk`.

TARGET ADDON:
`onehr_attendance`

ROOT CAUSE CLASSIFICATION:
`ODOO_VERSION_COMPATIBILITY_FAILURE`

BOUNDED REPAIR ATTEMPT:
2

## New runtime evidence

Odoo 19 rejected `hr.attendance.onehr.search` while loading:

`onehr_attendance/views/attendance_views.xml`

with:

`Invalid default period this_month for date filter`

The failing source was:

    <filter name="this_month" string="This Month" date="date" default_period="this_month"/>

Odoo 19 uses the internal period id `month` for the current month.  The filter
name and visible label are preserved; only the invalid internal default-period
identifier is corrected:

    <filter name="this_month" string="This Month" date="date" default_period="month"/>

## Scope and preservation evidence

- changed XML file: `views/attendance_views.xml`
- changed manifest version: `19.0.1.0.1` -> `19.0.1.0.2`
- hardened `tools/source_acceptance.py` to reject invalid date-filter
  `default_period` identifiers in future builds
- no model added/removed
- no field added/removed
- no method/workflow changed
- no ACL or record rule changed
- no hard dependency changed
- no attendance/overtime ownership changed
- no history/effective-dating behavior changed
- no enterprise UI feature removed

The latest uploaded `onehr_mobile_kiosk` source contains no `default_period`
attribute, therefore it is not modified for this defect.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST
ONEHR_ATTENDANCE_MOVE_FORWARD_READY: NO
ONEHR_MOBILE_KIOSK_MOVE_FORWARD_READY: NO
