# OneHR Workflow Approval — Source Integration Contract

A source addon that needs OneHR generic approval inherits:

`onehr.mixin.approvable`

The source remains owner of its business state and execution.

Source hooks:
- `_approval_payload()` — minimum-necessary snapshot shown/stored for approval.
- `_approval_rule_context()` — structured route inputs: company, document type,
  normalized amount/currency, risk, manager chain, source resolver IDs and extra keys.
- `_approval_branch_scope_key()` — future branch extension point.
- `_on_approval_finalized(decision, request)` — source-domain final decision hook.
- `_approval_cancel_guard(request)` — source-domain cancellation veto.
- `onehr_mark_approval_executed(request)` — source calls only after approved work succeeds.

The approval engine never changes arbitrary source state, never invents a source
approval payload, never executes source business work and never bypasses source ACL/rules.
