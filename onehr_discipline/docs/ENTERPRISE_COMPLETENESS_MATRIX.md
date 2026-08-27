# OneHR Discipline — Enterprise Completeness Matrix

| Area | Source status | Runtime status |
|---|---|---|
| Root Guardrail / bounded-worker contract | PASS source | n/a |
| Tutorial scaffold removal | PASS source | Reached addon view loading |
| Exactly 2 persistent Discipline models | PASS source | PENDING registry |
| Exact 3 hard dependencies | PASS source | PENDING loader |
| Legacy product-intent preservation map | PASS source | PENDING UAT |
| Reported→Investigation→Hearing→Decision→Closed | PASS source | PENDING UAT |
| Investigation evidence & attachment handling | PASS source | PENDING UAT |
| Hearing schedule/minutes/statements | PASS source | PENDING UAT |
| Violation classification/weight | PASS source | PENDING UAT |
| SLA calculation/reminder cron | PASS source | PENDING cron |
| Appeal recording/review/outcome | PASS source | PENDING UAT |
| Sanction types incl. SP1/2/3/suspension/probation | PASS source | PENDING UAT |
| Payroll deduction request handoff | PASS source | PENDING downstream |
| Contract probation/termination handoff | PASS source | PENDING downstream |
| Workflow Approval source contract | PASS source | PENDING integration |
| Approval request Executed after sanction execution | PASS source | PENDING integration |
| Soft Appraisal evidence refresh | PASS source | PENDING optional integration |
| Soft PnP reference resolution | PASS source | PENDING optional integration |
| Soft Document handoff payload | PASS source | PENDING optional integration |
| Analytics/API discipline KPI service | PASS source | PENDING downstream |
| Repeat-offense rate | PASS source | PENDING runtime |
| Average resolution time | PASS source | PENDING runtime |
| Hearing Summons PDF | PASS source | PENDING QWeb |
| Hearing Minutes PDF | PASS source | PENDING QWeb |
| Case Outcome PDF | PASS source | PENDING QWeb |
| Outcome & Lead-Time Register PDF | PASS source | PENDING QWeb |
| Sanction/Warning/SP Letter PDF | PASS source | PENDING QWeb |
| Decision Record PDF | PASS source | PENDING QWeb |
| List/Form/Search both models | PASS source; Repeat Offense search repaired 19.0.1.0.1 | PENDING re-activation |
| Kanban/Calendar/Pivot/Graph | PASS source | PENDING UI |
| Statusbar/Smart/Body/O2M buttons | PASS source | PENDING UI |
| Global company isolation | PASS source | PENDING security UAT |
| Investigator assignment scope | PASS source | PENDING security UAT |
| HRBP assignment scope | PASS source | PENDING security UAT |
| Manager/Legal company scope | PASS source | PENDING security UAT |
| No broad base.group_user Discipline CRUD | PASS source | PENDING ACL registry |
| No public controller/business sudo | PASS source | PENDING runtime |
| No spoofable lifecycle context bypass | PASS source | PENDING security UAT |
| HARD GATE 11 identifier safety | PASS when scanner passes | PENDING physical DB |
| 50 post-install tests | PASS source inventory | PENDING execution |
| Exact Registry ED0–ED5 rows | PENDING authoritative rows | PENDING |
| Fresh install | n/a | FAILED Attempt 1 at Search View validation; repair 19.0.1.0.1 PENDING retest |
| Repeated upgrade/idempotency | n/a | PENDING |
| Post-upgrade smoke | n/a | PENDING |
| Enterprise functional completeness | PENDING runtime | PENDING |

SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME when source acceptance passes.  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_DISCIPLINE_MOVE_FORWARD_READY: NO

## Runtime Attempt 1 status

Activation failure classification: `ADDON_SOURCE_FAILURE`.

Proven defect:
`repeat_offense` was a computed/non-stored field without `search=`, while the
Search View used it in a filter domain.

Bounded repair `19.0.1.0.1` preserves the filter and dynamic business semantics
by adding `_search_repeat_offense`. Runtime acceptance remains pending until the
exact repaired package is activated again.
