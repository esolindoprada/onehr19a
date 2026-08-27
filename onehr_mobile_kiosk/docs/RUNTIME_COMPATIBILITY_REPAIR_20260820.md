# OneHR Mobile Kiosk — Odoo 19 Search View Compatibility Repair 2026-08-20

TASK: bounded activation hardening
TARGET ADDON: `onehr_mobile_kiosk`
ROOT CAUSE CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE
BOUNDED REPAIR ATTEMPT: 1

## Proven source defect

The exact Odoo 19 search-view compatibility defect proven in the Attendance
dependency also existed in two Mobile Kiosk search views:

- `views/device_views.xml`
- `views/log_views.xml`

Both used legacy:

    <group expand="0" string="Group By">

The legacy attributes were removed while every Group By filter and its context
were preserved unchanged.

No dependency, model ownership, security boundary, device lifecycle, queue,
attendance bridge, controller, report, action, or enterprise UI feature was
removed or weakened.

The source acceptance harness now rejects attributed search-view `<group>`
elements.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_MOBILE_KIOSK_MOVE_FORWARD_READY: NO
