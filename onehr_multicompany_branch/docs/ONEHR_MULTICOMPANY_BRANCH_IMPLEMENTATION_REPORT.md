
# OneHR Multicompany & Branch — Direct Full Build Implementation Report

## Build decision

The historical generic scaffold is reconstructed as the Registry-approved Odoo 19 CE foundation addon. The implementation deliberately avoids a parallel company master and avoids modifying sibling source code.

## Enterprise design delivered

- Effective-dated hierarchical `onehr.branch` with controlled archive/history semantics.
- Odoo-native `res.company` extension for technical branch enablement/default/counts, with dedicated Settings list/search integration.
- Odoo-native `res.users` extension for explicit allowed branch scope and personal default.
- Registry-approved abstract `onehr.mixin.branch` for future source-domain opt-in.
- `onehr.user.role` branch scope through the extension contract frozen in `onehr_security`.
- Branch-specific role overlap and SoD peer resolution while company-wide roles continue to overlap all branches.
- Branch-aware OneHR managed-group reconciliation so a branch-specific role cannot keep global Odoo group entitlement merely because its branch is no longer authorized/effective.
- Least-privilege Branch User / Manager / Admin / Central Office groups using Odoo 19 privilege classification.
- Company-first and branch-aware record rules.
- Professional branch form/list/search with statusbar, smart buttons, controlled body actions and One2many row actions; native company/user/security views are extended rather than replaced.
- Central role-coverage pivot/graph without inventing an unregistered reporting model.
- Exactly 28 post-install tests and source acceptance tooling, including relational-comodel and full native Users runtime-dependency closure regression coverage.

## Important security decision

Branch Admin does not imply OneHR Security Admin and OneHR Security Admin does not imply Branch Admin. Branch Admin receives a narrow `res.users` write ACL solely to maintain branch fields; Python guards reject other-user edits outside those branch fields and reject branch IDs outside the administrator's own legal-company scope. Odoo company policy, allowed-company entitlements and raw group entitlements remain outside Branch Admin authority. The `res.company` OneHR Branch policy section is therefore restricted to Odoo Technical Administration.

## Bounded production repair — 19.0.1.0.1

The production traceback class was an `ADDON_SOURCE_FAILURE`: a user could have legitimate read authority on `res.users` or `onehr.user.role` while lacking ACL read authority on the relational comodel `onehr.branch`. That mismatch breaks Odoo web rendering when it resolves `onehr_allowed_branch_ids`, `onehr_default_branch_id`, `onehr_effective_branch_ids`, or `branch_id`.

The bounded repair adds only three read-only ACL rows for Odoo Technical Admin, OneHR Security Manager, and OneHR Security Admin. Existing company/branch record rules are untouched. Branch mutation remains owned by Branch Admin and enforced again in Python. A reusable source gate derives relational comodels from field declarations and verifies explicit read-ACL closure for all approved Users / Role Assignment branch consumers. Five runtime regression tests exercise the same contract.

## Bounded production repair — 19.0.1.0.2

The real runtime log proved that the native Users path still failed after branch-label closure because the OneHR Security summary/search fields injected into `res.users` traverse `onehr.user.role`, `onehr.role`, `onehr.sod.conflict.log`, and `onehr.audit.log`. The 19.0.1.0.1 gate was therefore incomplete, not wrong in its branch diagnosis.

Attempt 2 closes the complete current Users dependency graph for Odoo Technical Admin with four additional read-only ACLs. It does not alter any Python business model, view, record rule, group implication, dependency, model ownership, workflow, effective dating, SoD semantics, or audit behavior. Five additional runtime regressions now exercise native Users list/search plus the full support-model closure before another browser rerun.

## Status

DIRECT_FULL_SOURCE_BUILD: PASS
SOURCE_ACCEPTANCE: PASS
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: NO

Static/runtime/test PASS, when achieved, will still not be treated as final enterprise completeness until the final functional completeness matrix is reviewed with runtime evidence.

