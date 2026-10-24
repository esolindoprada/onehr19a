

# OneHR Base — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart Button | Main Actions | Row/One2many Button | Chatter | Security |
|---|---|---|---|---|---|---|---|---|---|
| `hr.department` | inherited+extended | inherited+extended | OneHR action search | N/A | Positions | N/A | N/A | native behavior | native HR ACL/rules |
| `hr.job` | inherited+extended | inherited+extended | OneHR action search | N/A | Positions | N/A | N/A | native behavior | native HR ACL/rules |
| `hr.work.location` | inherited+extended | inherited+extended | OneHR action search | N/A | Positions | N/A | N/A | native behavior | native HR ACL/rules |
| `onehr.job.family` | yes | yes | yes | N/A | Positions | N/A | N/A | yes | Officer read; Manager admin |
| `onehr.position` | yes | yes | yes | Position Status | Hierarchy Nodes | status maintained as business field | N/A | yes | Officer read; Manager admin |
| `onehr.position.hierarchy` | yes | yes | yes | N/A | Versions | N/A | N/A | yes | Officer read; Manager admin |
| `onehr.position.hierarchy.version` | yes | yes | yes | Draft/Active/Retired | Nodes | Activate, Retire | Open Position in node rows | yes | Officer read; Manager actions |
| `onehr.position.hierarchy.node` | yes | yes | yes | N/A | Open Position | N/A | Open Position | yes | Officer read; Manager admin |
| `onehr.grade` | yes | yes | yes | N/A | Steps, Positions | N/A | editable steps | yes | Officer read; Manager admin |
| `onehr.grade.step` | yes | yes | yes | N/A | N/A | N/A | N/A | yes | Officer read; Manager admin |
| `onehr.sequence.rule` | yes | yes | yes | N/A | N/A | `next_value()` API | N/A | yes | Officer read; Manager admin |
| `onehr.eligibility.profile` | yes | yes | yes | N/A | N/A | `matches()` API | N/A | yes | Officer read; Manager admin |
| `onehr.lifecycle.event.type` | yes | yes | yes | N/A | Checklist Templates | N/A | N/A | yes | Officer read; Manager admin |
| `onehr.checklist.template` | yes | yes | yes | Draft/Active/Retired | Task Definitions, Allocated | Activate, Retire, Create New Version | Template link on tasks | yes | Officer read; Manager workflow |
| `onehr.checklist.task.template` | yes | yes | yes | N/A | Open Template | performer resolution hook | Template link | yes | Officer read; Manager admin |
| `onehr.checklist.instance` | yes | yes | yes | Draft/In Progress/Completed/Cancelled | Tasks, Pending, Done | Complete, Cancel, Schedule Outstanding Activities | Done/Schedule/Cancel on tasks | yes | Officer operational; Manager operational |
| `onehr.checklist.task` | yes | yes | yes | Pending/Done/Cancelled | Open Checklist | Done, Cancel, Schedule Activity | Done/Schedule/Checklist | yes | Officer operational; Manager operational |

## UI Security Principle

Visibility is a usability layer only. The Python methods use normal ORM operations
without `sudo()` and remain subject to ACLs and record rules.
