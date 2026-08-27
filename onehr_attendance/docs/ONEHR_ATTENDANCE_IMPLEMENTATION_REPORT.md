# OneHR Attendance — Direct Full Implementation Report

## What changed

The prior folder was a generic scaffold with placeholder controller/model/view code and `base`-only dependency. It has been replaced end-to-end by a Registry-aligned Odoo 19 enterprise attendance domain.

The implementation is native-first: Odoo `hr.attendance` remains canonical, and the Odoo 19 overtime engine remains authoritative. OneHR adds enterprise scheduling, effective policy, exceptions, import/reconciliation evidence, readiness workflow and professional UI around those native owners.

## Functional flow

1. Manager defines effective shifts and rotation patterns.
2. Manager optionally assigns a direct shift/pattern to an employee; absent an explicit schedule, the resolver chooses the most-specific valid shift using employee and soft enterprise-assignment context.
3. Canonical `hr.attendance` is entered through native UX or retry-safe OneHR ingestion.
4. OneHR calculates planned interval, lateness, early leave, rounded-hours evidence and geofence status without rewriting native worked-hours or overtime algorithms.
5. Officer confirms and materializes governed exception evidence.
6. Critical exceptions and pending native overtime approval block final Posted/payroll-readiness state.
7. Fingerprint/device files stage through Import Batch → validation → Reconciliation → canonical attendance.
8. Daily automation detects expected-shift missing punches while exposing a future Time Off/Learning exclusion hook.

## Security design

Attendance Officer is intentionally not granted Core HR Officer or `hr.group_hr_user`. The addon grants narrow read-only access to employee/position/work-calendar records needed for attendance operations, while business transactions remain protected by OneHR groups, ACLs, company rules and state authority checks.

## Runtime boundary

This build has source/static acceptance only until tested on the user's Windows Odoo 19 instance. No source PASS, ZIP integrity PASS or static test count is treated as functional completion.
