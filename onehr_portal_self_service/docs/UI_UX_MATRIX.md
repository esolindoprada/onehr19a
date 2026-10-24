
# OneHR Portal Self-Service — UI/UX Matrix

| Surface / Model | List | Form | Search | Extra | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.portal.request.type` | YES | YES | YES | — | Active/portal controls, SLA metrics, smart button, body action, request One2many row action, chatter |
| `onehr.portal.request.stage` | YES | YES | YES | — | Stage/state mapping, fold/visibility, smart button, body action, request One2many row action, chatter |
| `onehr.portal.request` | YES | YES | YES | Kanban + Calendar + Pivot + Graph | Statusbar, manager/HR lifecycle buttons, decision wizard, SLA/integration smart buttons/body actions, badges/ribbons, chatter |
| `hr.employee` extension | existing | inherited | existing | — | Portal enabled flag + self-service request smart button |
| `/my/hr` | — | — | Filters | Portal dashboard | employee profile summary, KPI tiles, soft-integration cards, request register, create/open actions |
| `/my/hr/new` | — | Portal form | — | — | service catalogue, service-specific detail panels, multi-file support, Save Draft / Submit |
| `/my/hr/<id>` | — | Portal detail | — | — | workflow/SLA/downstream evidence, attachments, comments, submit/cancel, manager decision |
| `/my/team` | — | — | — | Manager queue | direct-report approval queue and review drill-down |

Odoo 19 compatibility:
- `<list>` only; no legacy `<tree>`.
- direct `invisible` / `readonly`; no legacy `attrs` / `states`.
- search `<group>` containers have no attributes.
- native CE views only; Enterprise-only Gantt is not fabricated.

