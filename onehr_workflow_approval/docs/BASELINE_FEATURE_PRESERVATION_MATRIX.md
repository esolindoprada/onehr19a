
# OneHR Workflow Approval — Baseline Feature Preservation Matrix

| Baseline / approved intent | Direct Full Build implementation | Source status |
|---|---|---|
| Approval matrix by role/threshold | ED2 rules with OneHR role, normalized amount/currency, risk, document/branch and structured extra criteria | PASS |
| Multi-level sequential | Ordered `level` progression | PASS |
| Parallel approval | Multiple steps sharing the same level | PASS |
| Dynamic approver picker | Specific users, OneHR role, Odoo group, requester manager chain, source resolver key | PASS |
| Delegation | ED1 delegation mapped only from a resolved base authority | PASS |
| Reassignment | Workflow Manager reassign preserving original authority identity + evidence | PASS |
| SLA | Per-step deadlines, due/overdue state and hourly processing | PASS |
| Reminder | Mail activities + append-only reminder event | PASS |
| Escalation | Configured users/roles added after SLA breach + append-only evidence | PASS |
| Self-approval block | Per-step requester exclusion | PASS |
| Quorum / 2-eyes / 4-eyes | any/quorum/all + rule minimum distinct authority identities | PASS |
| Mail / activities / chatter | `onehr.mixin.audit`, followers and automated activities | PASS |
| Auto approve | Explicit rule, zero minimum human approvers, system decision evidence | PASS |
| Resubmit | New request supersedes rejected/cancelled request; old ED3 history retained | PASS |
| Cancel guard | requester/manager action + source `_approval_cancel_guard()` | PASS |
| Immutable decision trail | no normal rewrite/delete; correction creates superseding evidence | PASS |
| SLA audit trail | immutable reminder/overdue/escalation/reassign rows | PASS |
| Dashboard / SLA KPI | ED4 daily snapshot + list/pivot/graph | PASS |
| Source integration hooks | Registry-approved `onehr.mixin.approvable` contract | PASS |
| Source business ownership | source addon remains owner and executor | PASS |
| Safe rule criteria | scalar/list structured JSON; no eval/safe_eval | PASS |
