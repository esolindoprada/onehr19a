# onehr_corehr — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart / Body / Row Actions | Chatter | Security |
|---|---|---|---|---|---|---|---|
| `hr.employee` | Native extended | Native extended | Native extended | Native version timeline | 9 smart buttons; lifecycle/OH body actions; inline One2many row actions | Native | Odoo HR + Core HR field/action groups |
| `hr.employee.public` | Native | Native | Native | N/A | N/A | Native | directory-safe field only |
| `hr.version` | Native | Native via employee | Native | Native version timeline | Native | Native | Odoo HR |
| `onehr.employee.dependent` | Yes | Yes | Yes | N/A | Employee, End Relationship | Yes | Core HR Officer |
| `onehr.employee.emergency.contact` | Yes | Yes | Yes | N/A | Set Primary, Expire, Employee | Yes | Core HR Officer |
| `onehr.employee.identifier` | Yes | Yes | Yes | N/A | Verify, Expire, Employee | Yes | Identifier Steward only |
| `onehr.employee.education` | Yes | Yes | Yes | N/A | Complete, Expire, Employee | Yes | Core HR Officer |
| `onehr.employee.employment.history` | Yes | Yes | Yes | N/A | Verify, Close, Employee | Yes | Core HR Officer |
| `onehr.engagement.type` | Yes | Yes | Yes | N/A | Versions smart button, Archive | Yes | Officer read / Manager maintain |
| `onehr.work.incident` | Yes | Yes | Yes | Draft→Reported→Review→Closed/Cancelled | Report, Review, Close, Create Assessment, smart buttons, row actions | Yes | Occupational Health only |
| `onehr.medical.assessment` | Yes | Yes | Yes | Draft→Finalized→Superseded | Finalize, Superseding Correction, Employee/Incident | Yes | Occupational Health only |
| `onehr.disability.record` | Yes | Yes | Yes | Draft→Active→Closed | Activate, Close, Employee | Yes | Occupational Health only |
| `res.config.settings` | Native | Native extended | Native | N/A | Save via native Settings | N/A | Existing Settings access + view groups |

All custom persistent user-facing models have dedicated search views and enterprise lists.
