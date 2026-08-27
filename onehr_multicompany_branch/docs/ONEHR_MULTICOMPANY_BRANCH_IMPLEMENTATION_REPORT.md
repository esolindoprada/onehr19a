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
- Exactly 18 post-install tests and source acceptance tooling.

## Important security decision

Branch Admin does not imply OneHR Security Admin and OneHR Security Admin does not imply Branch Admin. Branch Admin receives a narrow `res.users` write ACL solely to maintain branch fields; Python guards reject other-user edits outside those branch fields and reject branch IDs outside the administrator's own legal-company scope. Odoo company policy, allowed-company entitlements and raw group entitlements remain outside Branch Admin authority. The `res.company` OneHR Branch policy section is therefore restricted to Odoo Technical Administration.

## Status

DIRECT_FULL_SOURCE_BUILD: PASS
SOURCE_ACCEPTANCE: PASS
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: NO

Static/runtime/test PASS, when achieved, will still not be treated as final enterprise completeness until the final functional completeness matrix is reviewed with runtime evidence.
