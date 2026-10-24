
# OneHR Career & Succession — UI/UX Matrix

| Model | List | Form | Search | Extra analysis | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.competency` | YES | YES | YES | requirement workspace | smart buttons, body workspace button, archive governance, O2M row action, chatter |
| `onehr.position.competency` | YES | YES | YES | Pivot + Graph | smart buttons, talent-gap action, position navigation, archive governance, chatter |
| `onehr.talent.pool` | YES | YES | YES | Kanban + Pivot + Graph | Statusbar, propose/approve/activate, source refresh, readiness cards, smart/body buttons, gap PDF, chatter |
| `onehr.succession.plan` | YES | YES | YES | Kanban + Pivot + Graph | Statusbar, proposal/approval/activation, candidate workspace, row gap action, coverage/risk dashboard, PDF, chatter |

Odoo 19 compatibility:
- `<list>`, never legacy `<tree>`;
- direct `invisible` / `readonly`, no legacy `attrs` / `states`;
- search `<group>` attributes are not used;
- no Enterprise-only Gantt renderer is fabricated.

