# OneHR Integrations API — UI/UX Matrix

| Model | List | Form | Search | Extra analysis | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.api.key` | YES | YES | YES | — | Statusbar; generate/rotate/activate/suspend/revoke; request/success/error smart buttons; chatter |
| `onehr.api.scope` | YES | YES | YES | — | key smart button; deactivate; risk badges; chatter |
| `onehr.webhook` | YES | YES | YES | Kanban | Statusbar; rotate/activate/pause/test/disable; queue/log smart buttons; One2many queue Process/Retry buttons; chatter |
| `onehr.api.log` | YES | read-only YES | YES | Pivot + Graph | immutable evidence, outcome badges, latency/error analysis |
| `onehr.api.queue` | YES | YES | YES | Kanban + Pivot + Graph | Statusbar; Process/Retry/Dead Letter/Cancel; log smart button; chatter |

Odoo 19 compatibility: `<list>`, direct modifiers, Search `<group>` without attributes,
`ir.actions.act_window.group_ids`, no legacy `tree/attrs/states`, no Enterprise-only Gantt.
