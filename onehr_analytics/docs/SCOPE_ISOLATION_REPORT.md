# OneHR Analytics — Scope Isolation Report

## Allowed write scope
Only `onehr_analytics` source is created/replaced in this task.

## Sibling addons
No source file in `onehr_base`, `onehr_security`, Recruitment, Attendance, Time Off, Learning,
Payroll, Appraisal, Career/Succession, Discipline, Portal, Branch or Integrations API is
modified.

## Integration technique
Analytics discovers optional models through the registry, invokes only named existing KPI
service contracts, and uses normal current-user access. It never patches siblings to make an
Analytics test pass.

`SCOPE_ISOLATION: PASS`
