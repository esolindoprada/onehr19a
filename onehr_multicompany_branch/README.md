# OneHR Multicompany & Branch

Enterprise operational branch foundation for **Odoo 19 Community Edition**.

## Architecture boundary

- `res.company` remains the legal and outer security partition.
- `onehr.branch` is an effective-dated operational subdivision inside one company.
- `res.users` stores explicit allowed/default branch preferences that can only narrow existing Odoo company access.
- `onehr.user.role` remains owned by `onehr_security`; this addon adds optional branch scope through the extension hooks already provided by that addon.
- `onehr.mixin.branch` is opt-in and must be inherited only by future business facts that genuinely belong to a branch.

## Enterprise controls

The addon includes hierarchical branch governance, temporal integrity, central-office reporting, least-privilege branch roles, branch-aware security-role overlap/SoD behavior, statusbar/actions/smart buttons/One2many actions, list/form/search coverage, audit integration and exactly 18 post-install runtime test methods.

`onehr_branch_enabled` is a technical company policy. Disabling it does not weaken record rules or erase history; it prevents branch defaults/branch-scoped authority from becoming effective while the policy is disabled.

## Security authority

Branch Admin is not Security Admin. Branch Admin can maintain branch masters and narrowly maintain branch-scope fields on company-scoped users. Python guards reject unrelated user fields and reject branch IDs outside the administrator's own allowed legal companies. OneHR role activation/revocation remains owned by `onehr_security`.

## Current acceptance status

- Direct Full source build: **PASS**
- Source/static acceptance: **PASS**
- Windows Odoo 19 fresh install/tests/upgrades: **PENDING**
- Enterprise final completeness: **PENDING**
- `ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY`: **NO**

Run `tools/source_acceptance.py` after deployment before any runtime install attempt.
