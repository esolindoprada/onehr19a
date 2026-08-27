# OneHR PnP — UI/UX Matrix

| Model | List | Form | Search | Extra views | Enterprise interactions |
|---|---|---|---|---|---|
| `onehr.policy` | YES | YES | YES | Kanban + Calendar + Pivot + Graph | Approval statusbar; submit/publish/review/revision/archive; approvals/versions/ack/evidence/archive smart buttons; audience preview; reminders; reports; O2M row actions; chatter |
| `onehr.policy.ack` | YES | YES | YES | Pivot + Graph | Read & Acknowledge; policy/evidence smart buttons; reminder evidence; O2M evidence actions; statusbar |
| `onehr.policy.evidence` | YES | YES | YES | Pivot + Graph | Employee/unit/policy scope; Submit/Verify/Reject; policy/assignment/document navigation; attachment/link/document/note payload; statusbar; chatter |

Odoo 19:
- `<list>`, never legacy `<tree>`;
- no legacy `attrs=` or `states=`;
- Search `<group>` has no attributes;
- no Enterprise-only Gantt renderer is fabricated.
