# onehr_timeoff — UI/UX Matrix

| Model / surface | List | Form | Search | Advanced enterprise interaction |
|---|:---:|:---:|:---:|---|
| `onehr.leave.type` | YES | YES | YES | Statusbar; activate/retire; Requests/Allocations/Employees-without-balance smart buttons; body Run Accrual and review actions; policy notebook; KPI snapshot; chatter. |
| `onehr.leave.request` | YES | YES | YES | Statusbar; submit/reset/done/cancel/print; Approval/Reserved Entitlement/Team/Employee smart buttons; body manager-review/team-calendar/reservation actions; attachment; balance + evidence tabs; chatter. |
| `onehr.leave.allocation` | YES | YES | YES | Statusbar; confirm/cancel/generate; Generated/Requests/Employee/Policy smart buttons; persistent mass-allocation modal; generated One2many with row buttons; balance/source tabs; chatter. |
| Leave Request analytics | — | — | uses request search | Calendar, Pivot and Graph; team calendar and annual usage action. |
| Leave Allocation analytics | — | — | uses allocation search | Pivot and Graph; employee balance, source and period grouping. |
| `hr.employee` extension | native | inherited | native | HR-only Leave Requests / Leave Allocations / Current Leave smart buttons. |

HARD_GATE_7_UI_UX_MATRIX_SOURCE_RESULT: PASS
HARD_GATE_8_SEARCH_VIEW_SOURCE_RESULT: PASS
HARD_GATE_9_LIST_VIEW_SOURCE_RESULT: PASS
RUNTIME_VIEW_VALIDATION: PENDING
