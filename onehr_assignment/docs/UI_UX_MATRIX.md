
# onehr_assignment — UI/UX Matrix

| Model | List | Form | Search | Enterprise interaction |
|---|:---:|:---:|:---:|---|
| `onehr.assignment` | YES | YES | YES | Statusbar, ribbons, approval/activate/end actions, Employee/Position/Approval/Successor/Cost smart buttons, manager-review body button, costing/successor row actions, chatter, Calendar/Pivot/Graph |
| `onehr.assignment.change.request` | YES | YES | YES | Statusbar, submit/execute/reset/cancel, approvals/generated smart buttons, body review scheduling, movement-line row actions, chatter |
| `onehr.assignment.change.line` | YES | YES | YES | Source/generated assignment row & form actions, target-placement review, chatter |
| `onehr.assignment.cost.allocation` | YES | YES | YES | Effective costing columns, assignment navigation, chatter |
| `onehr.workforce.plan` | YES | YES | YES | Statusbar, submit/activate/new-version/close, approval/budget smart buttons, body budget review, plan-line row actions, Pivot/Graph, chatter |
| `onehr.workforce.plan.line` | YES | YES | YES | Position/Budget actions, capacity/cost columns, chatter |
| `onehr.position.budget` | YES | YES | YES | Statusbar, activate/close, assignment/source-plan smart buttons, body position review, Pivot/Graph, chatter |

Native `hr.employee` receives controlled assignment-history/current-primary smart buttons for Officer/Manager. Native `onehr.position` receives assignment/budget smart buttons and live occupancy metrics without rewriting the Base position status.

UI_UX_MATRIX_SOURCE_RESULT: PASS
RUNTIME_VIEW_VALIDATION: PENDING
