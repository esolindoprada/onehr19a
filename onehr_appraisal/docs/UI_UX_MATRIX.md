# OneHR Appraisal — UI/UX Matrix

| Model | List | Form | Search | Extra analysis | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.appraisal.cycle` | YES | YES | YES | Kanban + Calendar | Statusbar; Open/Generate/Consolidate/Close; smart buttons; KPI import/result export; chatter |
| `onehr.appraisal.form` | YES | YES | YES | Kanban + Pivot + Graph | Statusbar; self/manager/peer actions; smart buttons; KPI score tiles; acknowledgement; PDF; One2many row buttons; chatter |
| `onehr.appraisal.score` | YES | YES | YES | Pivot + Graph | Submit Rating; target feedback workspace; development lifecycle; Learning hand-off; evidence; chatter |

Odoo 19 compatibility:
- operational lists use `<list>`, never legacy `<tree>`
- search-view `<group>` has no attributes
- direct `invisible`/`readonly` modifiers; no legacy `attrs`/`states`
- no Enterprise-only Gantt renderer is fabricated
