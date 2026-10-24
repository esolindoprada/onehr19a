
# UI / UX Matrix

| Model / extension | List | Form | Search | Enterprise controls |
|---|---|---|---|---|
| `onehr.branch` | Dedicated enterprise list with lifecycle decoration | Dedicated form | Dedicated search | statusbar, activate/archive, quick default selector, 4 smart buttons, body actions, hierarchy One2many row buttons, chatter |
| `res.company` | Native list inherited with branch policy/default/count columns | Native form inherited | Dedicated branch-policy search attached to native company action | technical-admin branch smart button, policy/default branch section, operational counts |
| `res.users` | Native user list inherited | Native user form inherited | Native search inherited | allowed/default branch page for Branch Admin, read-only visibility for central/security, branch stat buttons, branch role action |
| `onehr.user.role` | Security enterprise list inherited + branch column | Security enterprise form inherited + branch scope | Security enterprise search inherited + branch filters/group | existing statusbar/actions remain; branch scope frozen after activation; pivot/graph coverage added |
| `onehr.mixin.branch` | N/A | N/A | N/A | abstract helper only; no standalone menu/view by design |

## UI principle

Advanced controls are present only where they represent real business actions. No button can bypass ACL, record rules, company intersection, branch authorization, effective dates or server-side group checks.

