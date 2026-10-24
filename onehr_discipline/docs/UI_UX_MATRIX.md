
# OneHR Discipline — UI/UX Matrix

| Model | List | Form | Search | Extra views | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.discipline.case` | YES | YES | YES | Kanban + Hearing Calendar + Pivot + Graph | Pipeline statusbar; Start Investigation/Move Hearing/Move Decision/Close/Cancel; sanction/report smart buttons; Appraisal/Policy/Hearing/Sanction body actions; sanction One2many row actions; appeal controls; SLA ribbons; chatter |
| `onehr.discipline.sanction` | YES | YES | YES | Pivot + Graph | Approval statusbar; Submit/Return/Execute/Cancel; case/approval/report smart buttons; service/notice/report body actions; payroll/probation/contract sections; approval/execution evidence; chatter |

Additional actions:
- Active Investigations;
- Hearing Calendar;
- Case Analytics;
- Sanction Analytics.

Odoo 19 compatibility:
- operational `<list>`, not legacy `<tree>`;
- no `attrs=` / `states=`;
- Search `<group>` has no attributes;
- no Enterprise-only Gantt renderer is fabricated.

