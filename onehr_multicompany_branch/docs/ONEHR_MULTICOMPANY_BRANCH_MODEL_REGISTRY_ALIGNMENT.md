
# OneHR Multicompany & Branch — Master Model Registry Alignment

| # | Model | Class | ED | Implementation contract |
|---:|---|---|---|---|
| 1 | `onehr.branch` | NEW persistent | ED1 | Operational subdivision inside `res.company`; code unique per company; active/effective range; hierarchy and governance |
| 2 | `res.company` | INHERIT_ODOO | ED0 | Branch enablement/default/fallback configuration; company remains top legal/security partition |
| 3 | `res.users` | INHERIT_ODOO | ED0 | Explicit allowed branches, personal default branch, effective helper fields, security integration |
| 4 | `onehr.mixin.branch` | NEW abstract | ED0 | Optional `branch_id`, default/domain/access helpers for genuinely branch-owned future OneHR facts |

## Approved cross-addon extension

`onehr.user.role` remains owned by `onehr_security` and is not re-owned here. This addon adds the Registry-approved branch scope to that existing ED1 assignment through the extension hooks deliberately exposed by security. Company-wide role scope remains represented by `branch_id=False`; branch-specific scope uses `onehr.branch`.

## Rejected legacy scaffold model

`onehr_multicompany_branch.onehr_multicompany_branch` is not an approved Registry row and is not created. This is a registry-preserving replacement, not feature deletion.

## Dependency direction

Hard dependency is exactly `onehr_security`. `onehr_security` does not depend on this addon. No circular dependency is introduced.

