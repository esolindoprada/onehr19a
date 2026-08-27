# OneHR Learning — UI/UX Matrix

| Model | List | Form | Search | Extra analysis | Enterprise interactions |
|---|---|---|---|---|---|
| Course | YES | YES | YES | Kanban | Publish/Unpublish, validate prerequisites, smart buttons to Sessions/Enrollments/Certificates, ribbons, chatter |
| Session | YES | YES | YES | Calendar, Pivot, Graph | Open/Start/Complete/Cancel, waitlist, import/export, smart buttons, One2many row actions, statusbar, chatter |
| Enrollment | YES | YES | YES | Kanban, Pivot, Graph | Approval, Enroll/Waitlist, assessment, certificate, leave soft hook, approval smart button, statusbar, chatter |
| Attendance | YES | YES | YES | Pivot, Graph | Present/Late/Partial/Absent/Excused, work-attendance soft sync, open Enrollment, evidence controls |
| Certificate | YES | YES | YES | Expiry Calendar, Pivot, Graph | Issue/Revoke/Print/Document soft hook, expiry status, smart navigation, chatter |
| Vendor | YES | YES | YES | — | Provider rating, partner link, Sessions smart button, operational history protection |
| Budget | YES | YES | YES | Pivot, Graph | Activate/Close/Cancel, Sessions/Costs smart buttons, budget-burn KPIs, payroll payload export |
| Cost Line | YES | YES | YES | Pivot, Graph | Commit/Actual/Cancel, related-record buttons, immutable actual evidence, payroll hand-off payload |

## CE Gantt boundary
The product specification mentions Session Gantt. Native Odoo Gantt is not part of the
standard Community Edition view set used by this project. This build therefore does not
inject an unverified Enterprise-only `<gantt>` view or a custom renderer merely to make a
checklist green. Session scheduling is delivered through enterprise List + Calendar +
Pivot + Graph + Form. A Gantt/timeline renderer can be added only as a separately
approved CE-compatible frontend capability and must pass its own runtime gate.
