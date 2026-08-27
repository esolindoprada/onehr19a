# OneHR Attendance — Runtime Compatibility Repair 2026-08-20

TASK: dependency repair discovered while activating `onehr_mobile_kiosk`
TARGET ADDON: `onehr_attendance`
ROOT CAUSE CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE
BOUNDED REPAIR ATTEMPT: 1

## Proven defect

Odoo 19 rejected `onehr.shift.search` while loading `views/shift_views.xml`.
The uploaded source used legacy search-view group syntax:

    <group expand="0" string="Group By">

In Odoo 19, the search-view `group` element is a structural separator and takes
no attributes. The enterprise Group By filters themselves remain valid and are
preserved unchanged.

## Scope of correction

Removed only `expand="0" string="Group By"` from the 10 affected search-view
group elements across:

- `views/shift_views.xml` — 3
- `views/attendance_views.xml` — 1
- `views/exception_views.xml` — 1
- `views/reconciliation_views.xml` — 2
- `views/native_overtime_views.xml` — 3

No model, field, method, workflow, ACL, record rule, report, dependency, history,
or enterprise feature was removed or simplified.

The static source acceptance harness now fails if an attributed search-view
`<group>` returns.

RUNTIME_INSTALL_STATUS: PENDING_WINDOWS_RETEST
ONEHR_ATTENDANCE_MOVE_FORWARD_READY: NO
