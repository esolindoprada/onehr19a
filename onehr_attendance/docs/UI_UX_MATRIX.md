# onehr_attendance — UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart buttons | Body actions | One2many row actions | Analysis |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `onehr.shift` | YES | YES | YES | YES | Attendance, Schedules, Calendar | Preview planned interval | Schedule Employee/Preview; Attendance Employee/Exceptions | Calendar via schedule action |
| `onehr.shift.pattern` | YES | YES | YES | YES | Schedules | Validate cycle | Schedule Preview | — |
| `onehr.shift.assignment` | YES | YES | YES | YES | Employee, Today's Shift, Attendance, Exceptions | Preview; Check Yesterday Missing Punch | Exception Attendance/Review; Attendance Exceptions | — |
| `hr.attendance` | YES | YES | YES | YES | Employee, Shift, Reconciliation, Exceptions | Schedule Manager Review | Exception Review/Employee; Overtime Approve/Refuse | Calendar/Pivot/Graph |
| `onehr.attendance.exception` | YES | YES | YES | YES | Employee, Attendance | Resolution workflow | List row Review/Attendance/Employee | Pivot/Graph |
| `onehr.attendance.import.batch` | YES | YES | YES | YES | Reconciliations | Parse/Validate/Create Reconciliation | Reconciliation Open | — |
| `onehr.attendance.reconciliation` | YES | YES | YES | YES | Import, Attendances, Exceptions | Validate Candidates | Attendance Exceptions; Exception Attendance | — |
| `hr.attendance.overtime.line` | YES | YES | YES | Native status | Employee, Attendance | Native approve/refuse | Row approve/refuse/attendance | Pivot/Graph |
| `hr.attendance.overtime.rule` | YES | YES | YES | N/A | Ruleset | Policy metadata | Ruleset row open | — |
| `hr.attendance.overtime.ruleset` | YES | YES | YES | N/A | N/A | Regenerate Overtime | Rule row open | — |

Search views are not optional. Operational lists expose decision fields, source state, exception status and row actions rather than only names/IDs.
