# onehr_payroll_bridge — Enterprise Completeness Matrix

| Area | Source status | Windows runtime status | Evidence / acceptance |
|---|---|---|---|
| Project identity / exact addon | PASS | PENDING | Preflight + manifest |
| Exactly 3 product-approved custom models | PASS | PENDING | Registry alignment + source acceptance |
| Exact Registry ED labels | PENDING | PENDING | Exact Registry row not surfaced; not invented |
| Hard dependencies exactly Core HR + Security | PASS | PENDING | Manifest |
| Payroll calculation ownership excluded | PASS | PENDING | Integration contracts |
| Tax/localization ownership excluded | PASS | PENDING | Integration contracts |
| API credential/public-route ownership excluded | PASS | PENDING | Integration contracts |
| CSV variable export | PASS_SOURCE | PENDING | Export model/tests |
| Native Odoo work-entry soft consumption | PASS_SOURCE | PENDING | Runtime with hr_work_entry required |
| Frozen source/config evidence + SHA-256 | PASS_SOURCE | PENDING | Export model/tests |
| Attendance/overtime soft consumption | PASS_SOURCE | PENDING | Runtime cross-addon UAT required |
| Time Off soft consumption | PASS_SOURCE | PENDING | Runtime cross-addon UAT required |
| Assignment costing soft consumption | PASS_SOURCE | PENDING | Runtime cross-addon UAT required |
| Vendor payroll CSV import | PASS_SOURCE | PENDING | Import workflow/tests |
| Employee/vendor reconciliation | PASS_SOURCE | PENDING | Reconciliation workflow/tests |
| Immutable correction revision history | PASS_SOURCE | PENDING | Import revision workflow/tests |
| Department costing payload/report | PASS_SOURCE | PENDING | Export/report/tests |
| Monthly Draft preparation scheduler | PASS_SOURCE | PENDING | Cron + runtime |
| Least-privilege security | PASS_SOURCE | PENDING | ACL/rules/tests |
| List/Form/Search all 3 models | PASS_SOURCE | PENDING | Source acceptance |
| Advanced enterprise UI | PASS_SOURCE | PENDING | Statusbar/smart/body/O2M/calendar/pivot/graph/chatter |
| Fresh install | NOT_RUN | PENDING | Windows Odoo 19 |
| Runtime tests | SOURCE_READY | PENDING | `--test-tags /onehr_payroll_bridge` |
| First upgrade | NOT_RUN | PENDING | Windows Odoo 19 |
| Repeat upgrade / idempotency | NOT_RUN | PENDING | Windows Odoo 19 |
| Uninstall/reinstall disposable DB | NOT_RUN | PENDING | Windows Odoo 19 |
| Cross-addon regression | NOT_RUN | PENDING | Installed OneHR suite |
| Final functional completeness review | NOT_RUN | PENDING | All applicable rows PASS |

`SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME_WITH_REGISTRY_ED_PENDING`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: NO`
