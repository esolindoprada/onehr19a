
# OneHR Workflow Approval — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart buttons | Main/body actions | Row / One2many actions |
|---|---|---|---|---|---|---|---|
| `onehr.approval.rule` | enterprise | enterprise | yes | Draft/Active/Retired | Steps, Requests | Activate, Retire, New Version | Step → Rule |
| `onehr.approval.step` | enterprise | enterprise | yes | N/A | Rule, Requests | configuration workflow | Rule / Requests |
| `onehr.approval.request` | SLA-aware | workflow form | yes | Draft→Pending→Approved/Rejected→Executed/Cancelled | Source, Decisions, SLA Events, Resubmissions | Submit, Approve, Reject, Cancel, Resubmit, Send Reminder, Reassign | decision/log → Request |
| `onehr.approval.decision` | immutable evidence | read-only | yes | N/A | Request, Source | correction via admin API | Request, Source |
| `onehr.approval.delegate` | enterprise | enterprise | yes | Draft/Active/Revoked | Delegator, Delegate | Activate, Revoke | N/A |
| `onehr.approval.escalation.log` | immutable evidence | read-only | yes | N/A | Request, Source | none | Request, Source |
| `onehr.approval.kpi.daily` | KPI table | read-only snapshot | yes | N/A | Source Requests | none | N/A |

Additional reporting: Approval Request Pivot/Graph and KPI Pivot/Graph.

UI SECURITY PRINCIPLE: visibility is only usability. ACL, record rules and Python
authority/source guards remain authoritative.
