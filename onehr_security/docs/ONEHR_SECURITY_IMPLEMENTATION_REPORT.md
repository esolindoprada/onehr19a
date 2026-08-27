# OneHR Security — Direct Full Addon Build v1

## Delivery method

This package is a coherent Direct Full Addon Build. Codex was not used to build it.

Codex may only be introduced later if the exact target runtime proves a concrete
source defect, and then only under the bounded Guardrail.

## What replaces the generic scaffold

Removed conceptually/replaced:
- base-only manifest and version `0.1`;
- placeholder model;
- broad `base.group_user` full CRUD scaffold ACL;
- empty public-controller scaffold;
- demo placeholders;
- generic `views.xml` / `templates.xml`;
- Odoo 18 application-description wording.

Implemented:
- native `res.users` extension;
- OneHR business role catalogue;
- effective-dated user-role assignment;
- Odoo-group reconciliation;
- SoD warn/deny policy;
- immutable conflict evidence and human resolution evidence;
- append-only high-risk security audit;
- sensitive/restricted-access policy groups;
- company scope and branch extension contract;
- advanced security/compliance UI;
- 12 runtime test methods;
- source/runtime acceptance tooling.

## Odoo 19 design

Odoo `res.users` stays identity authority and `res.groups` stays low-level
entitlement authority. OneHR roles are a business abstraction over canonical
groups rather than a replacement.

Odoo 19 group privilege classification is used for OneHR security groups.
The module never hard-depends on the later branch addon.

## Provisioning model

No unregistered wizard model is invented.

Security Admin/Manager operate existing users and `onehr.user.role` through a
professional OneHR Security tab, role-assignment actions and reconciliation.
Role-to-group mapping is Security-Admin-only. Neither OneHR Security Manager nor
OneHR Security Admin may directly inject raw `res.users.group_ids`; functional
access must flow through effective OneHR roles. Security Admin can provision a
basic user identity in an already permitted company. Broader raw group and
multi-company entitlement administration remains with Odoo technical admin.

Because Odoo group membership is global, reconciliation calculates the union of all effective OneHR assignments for the user across companies before removing a managed group. This prevents a local expiry/revocation from accidentally removing access still required by another effective company/branch assignment. The elevated read is confined to this derived entitlement calculation; assignment authorization itself remains governed by normal ACL/rules.

Role definitions and SoD matrix policies are archive-only during normal operation. Their creation and policy-changing writes are captured in the structured security audit, so policy history is not reduced to chatter alone.

## SoD

- Warn: create evidence and continue activation.
- Deny: create evidence and block activation.
- Manual scans materialize conflicts for already-effective assignments.
- Retroactive policy changes do not silently revoke existing access; they create
  evidence for explicit governance.
- Human resolution comment is captured and frozen when finalized.

## Audit

`onehr.audit.log` is append-only for normal operations.

A narrow private `sudo().create()` is used only to persist mandatory audit
evidence after the triggering business operation has already passed its normal
authorization. It cannot authorize the triggering business action.

Controlled anonymization may remove payload content while retaining the event,
actor/time/correlation and an additional retention event.

## Uninstall security

The manifest declares `uninstall_hook`. Odoo 19 invokes this hook before removing
module data/schema. The hook removes every direct user membership belonging to an
Odoo group currently mapped by any OneHR business role, while preserving groups
that were never managed by OneHR. This prevents role-derived privileges from
surviving module removal.

## Branch integration

Company is the current top partition. The later branch addon may extend:
- `onehr.user.role._branch_scope_overlap_domain()`
- `onehr.user.role._branch_scope_label()`
- `res.users._onehr_branch_scope_assignment_domain()`

This preserves the approved dependency direction.

## Enterprise UI

Included where operationally meaningful:
- Statusbars: user-role assignment and SoD conflict lifecycle.
- Smart buttons: role counts, user security counts, conflict/audit targets.
- Header actions: Activate, Revoke, Accept Risk, Mitigate, Resolve, Anonymize.
- Body-form actions: Reconcile Access, Recheck SoD, Scan Effective Assignments.
- One2many/List row actions: Activate/Revoke/Open Role/User/Rule/Target.
- Search views for every custom user-facing persistent model.
- Operational lists with badges and decorations.

## Source/runtime status

DIRECT_FULL_SOURCE_BUILD: PASS
SOURCE_ACCEPTANCE: PASS
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_SECURITY_MOVE_FORWARD_READY: NO
