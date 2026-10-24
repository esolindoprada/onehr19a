
# OneHR Workflow Approval — Master Model Registry Alignment

| # | Model | Classification | ED | Implementation responsibility |
|---:|---|---|---|---|
| 1 | `onehr.approval.rule` | NEW persistent | ED2 | Effective-dated structured approval matrix/rule version |
| 2 | `onehr.approval.step` | NEW persistent | ED2 | Ordered level/parallel step, resolver, quorum/SLA |
| 3 | `onehr.approval.request` | NEW persistent | ED3 | Generic source reference + frozen approval payload/path |
| 4 | `onehr.approval.decision` | NEW persistent | ED3 | Immutable per-step decision evidence/correction chain |
| 5 | `onehr.approval.delegate` | NEW persistent | ED1 | Effective delegation; cannot exceed delegator authority |
| 6 | `onehr.approval.escalation.log` | NEW persistent | ED3 | Append-only reminder/overdue/escalation/reassign evidence |
| 7 | `onehr.mixin.approvable` | NEW abstract | ED0 | Narrow source-side integration contract; no table |
| 8 | `onehr.approval.kpi.daily` | NEW persistent | ED4 | Daily immutable SLA/lead-time snapshot |

Hard dependencies: `onehr_security`, `mail`.

Soft consumer: `onehr_analytics`.

No dependency back to transaction owners such as recruitment, contract, assignment,
time off, learning, discipline or PnP.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
