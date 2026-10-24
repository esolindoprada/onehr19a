
# OneHR SOP — UI/UX Matrix

| Model | List | Form | Search | Extra views | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.sop` | YES | YES | YES | Kanban + Pivot + Graph | current SOP, versions, acknowledgement smart buttons, archive, print, controlled revision, statusbar, KPI block, O2M version actions |
| `onehr.sop.version` | YES | YES | YES | Calendar | Draft→Review→Approved→Published→Obsolete, Read & Agree, audience preview, approve/publish, reminder/email actions, audit CSV, archive snapshot, compliance report |
| `onehr.sop.ack` | YES | YES | YES | Pivot + Graph | Read & Agree, Open SOP, employee drill-down for QA, statusbar, timestamp evidence |

Odoo 19 compatibility:
- `<list>`, never `<tree>`;
- direct `readonly`/`invisible`, never legacy `attrs`/`states`;
- Search `<group>` carries no attributes;
- no Enterprise-only Gantt renderer is fabricated.

