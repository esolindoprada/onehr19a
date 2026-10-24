
# OneHR Workflow Approval — Full Structural Inventory

## `onehr.approval.rule`
- Classification: NEW persistent, ED2.
- Source: `models/approval_rule.py`.
- Main fields: code, name, version, company, source model/document/branch scope,
  requester role, amount/currency/risk criteria, structured extra criteria,
  priority, minimum distinct approvers, auto-approve, effective dates, state, steps.
- Main methods: deterministic matrix resolver, overlap/config constraints,
  Activate, Retire, Create New Version, Open Steps, Open Requests.

## `onehr.approval.step`
- Classification: NEW persistent, ED2.
- Source: `models/approval_rule.py`.
- Main fields: rule, level, sequence, approver policy, specific users/role/group/
  manager level/source resolver key, decision mode/quorum, self-approval guard,
  delegation flag, SLA/reminder, escalation users/role, instructions, validity.
- Main methods: base approver resolver, escalation resolver, constraints and smart actions.

## `onehr.approval.request`
- Classification: NEW persistent, ED3.
- Source: `models/approval_request.py`.
- Stores source reference, minimum source snapshot, normalized routing context,
  frozen rule code/version, requester/timestamps, state/current level/current steps,
  eligible approvers, routing snapshot, deadline, decision/escalation evidence,
  scratch decision comment, controlled reassignment fields and resubmission link.
- Main workflow: Submit, Approve, Reject, Cancel, Resubmit, Reminder, Reassign,
  SLA Cron, source finalization callback, source execution marker and smart actions.

## `onehr.approval.decision`
- Classification: NEW persistent, ED3.
- Source: `models/approval_decision.py`.
- Stores request/step, actor, represented authority identity, decision, rationale,
  timestamp/source, delegation chain and superseding correction chain.
- Normal write/delete forbidden; correction appends new evidence.

## `onehr.approval.delegate`
- Classification: NEW persistent, ED1.
- Source: `models/delegation.py`.
- Stores delegator/delegate/company, role-or-rule scope, effective dates, reason,
  state and activation/revocation evidence.
- Runtime map accepts only delegators already resolved as real base authorities.

## `onehr.approval.escalation.log`
- Classification: NEW persistent, ED3.
- Source: `models/escalation.py`.
- Append-only reminder, overdue, escalation and manual-reassignment evidence with
  correlation id and structured payload.

## `onehr.mixin.approvable`
- Classification: NEW abstract, ED0.
- Source: `models/approvable_mixin.py`.
- Hooks: `_approval_payload`, `_approval_rule_context`, `_approval_branch_scope_key`,
  `_on_approval_finalized`, `_approval_cancel_guard`, `action_submit_for_approval`,
  `action_open_approval_requests`, `onehr_mark_approval_executed`.

## `onehr.approval.kpi.daily`
- Classification: NEW persistent, ED4.
- Source: `models/kpi.py`.
- Immutable daily company/rule counts for submitted/pending/approved/rejected/
  executed/overdue and average cycle/pending age.

## Technical/support inventory
- Pure action helpers: `models/action_helpers.py`.
- Pure routing/security helpers: `models/routing_helpers.py`.
- Four approval application groups.
- 18 ACL rows; no custom-model `base.group_user` ACL.
- Global company boundaries + participant/manager visibility rules.
- Sequence `onehr.approval.request`.
- Hourly SLA cron + daily KPI cron.
- Dedicated list/form/search for all seven persistent models.
- Request and KPI Pivot/Graph reporting.
- Exactly 20 post-install runtime test methods.
