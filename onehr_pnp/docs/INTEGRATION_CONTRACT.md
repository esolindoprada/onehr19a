
# OneHR PnP — Integration Contract

## OneHR Workflow Approval — hard owner
`onehr.policy` inherits `onehr.mixin.approvable`.

PnP supplies:
- `_approval_payload()`
- `_approval_rule_context()`
- `_approval_branch_scope_key()`
- `_approval_cancel_guard()`
- `_on_approval_finalized(decision, request)`

PnP remains owner of Policy business state and actual publication execution.
Workflow Approval owns routing, levels, approver eligibility, delegation,
decision evidence and request state. PnP calls `onehr_mark_approval_executed()`
only after Document snapshot, audience assignments and Published state succeed.

## OneHR Document — hard owner
Published policy content is archived through `onehr.document` plus issued
`onehr.document.version`. Successor policy versions reuse the logical Document
header and archive the previous version snapshot. PnP does not create a parallel
document/template/e-sign master.

## OneHR SOP — soft sibling owner
Operational SOP content/version/acknowledgement remains owned by `onehr_sop`.
`related_sop_references` stores optional SOP codes only. `action_open_related_sops`
uses a runtime model check; there is no hard dependency or static ORM relation.

## Portal — soft/downstream
`onehr_policy_portal_payload(policy_code)` and
`onehr_pnp_submit_evidence(payload)` expose model-service contracts under normal
PnP ACL/record rules. HTTP routes, sessions and authentication remain owned by
`onehr_portal_self_service`.

## Analytics — soft/downstream
`onehr_pnp_compliance_snapshot(company=None)` exposes current policy count,
review-overdue count, audience/acknowledgement/evidence totals and rates.
Dashboard/snapshot persistence remains owned by `onehr_analytics`.

## Integrations API — downstream
`onehr_pnp_ack_status(...)` is API-ready but does not create public controllers,
token models, retry/webhook ownership or transport policy.

## Branch — soft/downstream
`branch_scope_key` participates in Workflow routing and provides a stable
extension key. `onehr_multicompany_branch` may extend audience resolution later
without reverse dependency or PnP branch-master duplication.

