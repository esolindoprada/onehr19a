# onehr_timeoff — Enterprise Completeness Matrix

| Area | Source status | Windows runtime status | Evidence / acceptance |
|---|---|---|---|
| Project identity / exact addon | PASS | PENDING | Manifest + preflight |
| Product-baseline three model names | PASS | PENDING | Source inventory |
| Exact Registry ED labels | PENDING_AUTHORITY_CHECK | PENDING | Authoritative Registry v1 not surfaced in supplied excerpts |
| Hard dependencies exact | PASS | PENDING | Manifest |
| Native employee/Core HR ownership preserved | PASS | PENDING | Integration contract |
| Leave types annual/sick/special/training/unpaid | PASS | PENDING | Leave Type category |
| Grade / tenure eligibility | PASS | PENDING | Policy engine |
| Automatic accrual | PASS | PENDING | Scheduler + idempotency key |
| Carry-over with cap/expiry | PASS | PENDING | Scheduler + policy |
| First-year proration / seniority bonus / balance cap | PASS | PENDING | Policy formula |
| Opening balance / HR adjustment | PASS | PENDING | Allocation source types + CSV import template |
| Durable mass allocation | PASS | PENDING | Allocation batch + generated children |
| Work-schedule leave duration | PASS | PENDING | Resource calendar calculation |
| Team calendar / conflict warning or block | PASS | PENDING | Request conflict engine + Calendar view |
| Workflow approval integration | PASS | PENDING | Approvable callbacks/context |
| Entitlement reservation / insufficient balance | PASS | PENDING | Frozen reservation evidence |
| Paid/unpaid downstream payroll hook | PASS | PENDING | Stable payload method |
| Attendance/shift soft hook | PASS | PENDING | No reverse hard dependency |
| Request lifecycle / historical immutability | PASS | PENDING | state/evidence guards + ondelete |
| Self / manager / HR security | PASS | PENDING | ACL + record rules + authority checks |
| Multi-company isolation | PASS | PENDING | company rules/check_company |
| List/Form/Search all three custom models | PASS | PENDING | explicit views |
| Advanced enterprise UI | PASS | PENDING | statusbar/smart/body/O2M/chatter/calendar/pivot/graph |
| Leave request PDF evidence | PASS | PENDING | QWeb report |
| KPI: balance/utilization/approval lead | PASS | PENDING | computed fields + analytics views |
| Source/static acceptance | PASS | PENDING | `docs/SOURCE_ACCEPTANCE_REPORT.txt`: 0 failures |
| Fresh install | NOT_RUN | PENDING | Windows Odoo 19 |
| Runtime tests (20 source methods) | SOURCE_READY | PENDING | `--test-tags /onehr_timeoff` |
| First upgrade | NOT_RUN | PENDING | Windows Odoo 19 |
| Repeat upgrade/idempotency | NOT_RUN | PENDING | Windows Odoo 19 |
| Cross-addon regression | NOT_RUN | PENDING | accepted OneHR suite |
| Functional UAT | NOT_RUN | PENDING | employee/manager/HR scenarios |

SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_TIMEOFF_MOVE_FORWARD_READY: NO
