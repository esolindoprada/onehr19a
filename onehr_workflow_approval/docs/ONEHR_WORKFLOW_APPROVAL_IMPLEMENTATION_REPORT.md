
# OneHR Workflow Approval — Direct Full Addon Build v1

## Delivery method
This is one coherent Direct Full Addon Build. Codex was not used to build it.
Codex is reserved only for a later bounded repair when runtime evidence proves a
specific addon-source defect.

## Architecture
Exactly eight Registry rows are implemented. Hard dependencies remain exactly
`onehr_security` and `mail`. There is no reverse dependency to recruitment,
contract, assignment, time off, learning, discipline, PnP or analytics.

## Enterprise workflow
Rules are ED2 versions using safe structured criteria. Steps at one level run in
parallel; levels advance sequentially. Approver resolution supports specific
users, effective OneHR roles, Odoo groups, source-supplied manager chains and
explicit source resolver keys.

Requests freeze source payload/context/rule version and preserve the approval path.
Delegation and manual reassignment preserve the represented authority identity, so
quorum/all and minimum-distinct-approver controls do not double-count a delegate.

## Security/history
No broad custom-model `base.group_user` ACL. Participant visibility is company
scoped. Workflow Admin is separated from Security Admin and restricted HR groups.
Source records are never sudo-written by the approval engine.

Narrow sudo is documented only for internal routing metadata, automatic system
decision creation and append-only evidence creation. This avoids granting requesters
broad access to other users' security assignments.

Decisions and SLA evidence are immutable. Corrections create superseding evidence.
The original source transaction is not silently rewritten by a decision correction.

## Enterprise UI
Statusbars, smart buttons, operational header/body actions, One2many/list row
actions, dedicated search views, SLA-aware lists, read-only evidence forms and
Pivot/Graph reporting are included where they represent real server behavior.

## Status
SOURCE_DIRECT_FULL_BUILD: subject to `tools/source_acceptance.py`
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_WORKFLOW_APPROVAL_MOVE_FORWARD_READY: NO


## Runtime compatibility repair — 2026-08-14

The first Windows install attempt reached Odoo registry field setup and proved an
Odoo 19 compatibility defect in `onehr.approval.rule.model_id`: a required
Many2one to `ir.model` was configured with `ondelete="restrict"`.

The corrected build uses `ondelete="cascade"`, which is the Odoo 19-compatible
required-field policy for this framework metadata relation. No architecture,
Registry, dependency, security, effective-dating, workflow, UI or history
responsibility changed.

The source acceptance gate now detects forbidden `restrict` usage for every
official Odoo 19 `IR_MODELS` metadata comodel. Runtime acceptance remains pending.
