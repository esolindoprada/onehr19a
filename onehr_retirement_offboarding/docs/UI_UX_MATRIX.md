# UI/UX Matrix

| Model | List | Form | Search | Extra Analysis | Enterprise actions |
|---|---|---|---|---|---|
| `onehr.offboarding` | Yes | Yes | Yes | Kanban, Pivot, Graph | Submit Approval, Generate Checklist, Exit Interview, Request Revoke, Request Final Benefit, Complete, Close, Cancel; Employee/Approval/Checklist/Interview/Contract smart buttons; readiness/refresh/print body actions; One2many row actions |
| `onehr.offboarding.checklist` | Yes | Yes | Yes | Kanban, Calendar | Assign to Me, Start, Complete, Block, Waive, Reopen; Case smart button |
| `onehr.clearance.item` | Yes | Yes | Yes | — | Archive/Restore; Generated Tasks smart button; List row Tasks button |
| `onehr.exit.interview` | Yes | Yes | Yes | Pivot, Graph | Schedule, Start, Submit, Waive, Reopen; Case smart button; printable report |

No Gantt, Cohort or Spreadsheet UI is fabricated for Community Edition. Search `<group>` nodes remain attribute-free and Odoo 19 `<list>` syntax is used.
