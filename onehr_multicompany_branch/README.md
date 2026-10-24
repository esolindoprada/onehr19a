
# OneHR Multicompany & Branch

Enterprise operational branch foundation for **Odoo 19 Community Edition**.

## Architecture boundary

- `res.company` remains the legal and outer security partition.
- `onehr.branch` is an effective-dated operational subdivision inside one company.
- `res.users` stores explicit allowed/default branch preferences that can only narrow existing Odoo company access.
- `onehr.user.role` remains owned by `onehr_security`; this addon adds optional branch scope through the extension hooks already provided by that addon.
- `onehr.mixin.branch` is opt-in and must be inherited only by future business facts that genuinely belong to a branch.

## Enterprise controls

The addon includes hierarchical branch governance, temporal integrity, central-office reporting, least-privilege branch roles, branch-aware security-role overlap/SoD behavior, statusbar/actions/smart buttons/One2many actions, list/form/search coverage, audit integration and exactly 23 post-install runtime test methods, including five bounded cross-model branch read-closure regressions.

`onehr_branch_enabled` is a technical company policy. Disabling it does not weaken record rules or erase history; it prevents branch defaults/branch-scoped authority from becoming effective while the policy is disabled.

## Security authority

Branch Admin is not Security Admin. Branch Admin can maintain branch masters and narrowly maintain branch-scope fields on company-scoped users. Python guards reject unrelated user fields and reject branch IDs outside the administrator's own allowed legal companies. OneHR role activation/revocation remains owned by `onehr_security`.

## Current acceptance status

- Direct Full source build: **PASS**
- Source/static acceptance: **PASS**
- Windows Odoo 19 fresh install/tests/upgrades: **PENDING**
- Enterprise final completeness: **PENDING**
- `ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY`: **NO**

Version `19.0.1.0.1` is a bounded production repair that closes the relational-comodel read-authority gap for Odoo Technical Administrators and OneHR Security Manager/Admin users who consume branch fields from Users and Role Assignment surfaces. The new ACLs are read-only and existing branch/company record rules remain authoritative.

Run `tools/source_acceptance.py` after deployment before any runtime upgrade attempt.



## Bounded runtime closure — 19.0.1.0.2

Runtime evidence from the native Odoo Settings → Users action showed that branch-label closure alone was insufficient: the OneHR Security summary/search fields injected into `res.users` also traverse `onehr.user.role`, `onehr.role`, `onehr.sod.conflict.log`, and `onehr.audit.log`. Version `19.0.1.0.2` closes that complete current dependency graph for Odoo Technical Admin with read-only ACLs, retains the 19.0.1.0.1 `onehr.branch` read closure, and adds end-to-end Users list/search regression gates. No model code, view, record rule, dependency, ownership, workflow, effective dating or enterprise feature is changed.
