
# OneHR Job Description — UI/UX Matrix

| Model | List | Form | Search | Extra analysis | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.jd` | YES | YES | YES | Kanban + Pivot + Graph | smart buttons, current JD, version workspace, position drill-down, template generation, template sync, print, archive, O2M version workflow buttons, chatter |
| `onehr.jd.version` | YES | YES | YES | Calendar + Pivot + Graph | Draft→Review→Approved→Published statusbar, submit/return/approve/publish, source import, competency refresh, previous version, PDF, compare, fingerprint, chatter |

Odoo 19 CE compatibility:
- `<list>`, never legacy `<tree>`;
- direct `invisible`/`readonly`, no `attrs`/`states`;
- Search-view `<group>` has no attributes;
- no Enterprise-only Gantt renderer is fabricated.

