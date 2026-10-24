
# Security & Branch Scope Matrix

| Persona | Branch master | User branch scope | Role assignments | Consolidation | Server-side authority |
|---|---|---|---|---|---|
| Branch User | Read explicit allowed branches | No scope expansion; controlled own default only | None unless another OneHR security role grants it | No | record rules + quick-selector authorization |
| Branch Manager | Read explicit allowed branches | No scope administration | None by this addon | No | no structural write ACL |
| Branch Admin | Create/update branch masters in allowed companies | May change only branch fields on company-scoped users and only with branch IDs visible in the admin's legal-company scope | Read only for branch governance; security workflow still owned by Security Manager | Branch operational | `require_branch_admin`, res.users field-bound + actor-scope guard, company/branch constraints |
| Central Office | Read explicit allowed branches | Read-only | Read branch/company scoped role coverage | Yes, only explicit branches | no mutation ACL |
| OneHR Security Manager/Admin | Read branch masters in allowed legal companies solely to resolve branch relations and security-governance navigation | Read branch visibility; does not automatically become Branch Admin | Existing create/activate/revoke authority narrowed by branch rule | According to explicit branch scope | read-only branch ACL + unchanged branch global rule + security addon actions |
| Odoo Technical Admin | Read branch masters in allowed legal companies so Settings → Users can resolve OneHR branch fields | Native technical user administration; branch business mutation is not granted by this repair | Read-only access to current OneHR Users summary dependencies; no create/write/unlink authority | Technical | read-only closure ACLs + unchanged record rules; branch business actions still require Branch Admin |

## Non-negotiable boundaries

1. `res.company` remains the outer legal/security partition.
2. Branch scope never adds a company to `res.users.company_ids`.
3. Branch Admin ACL on `res.users` is constrained in Python to branch fields for other users, and branch IDs are validated through the caller's normal company/branch record rules.
4. Security Manager activation remains the only normal path for role assignment activation.
5. Global Odoo group membership is recalculated from effective role assignments and filters branch-specific rows to authorized/effective branches.
6. Central visibility requires explicit `onehr_allowed_branch_ids`; it is not an automatic company-wide bypass.


## Cross-model relational read closure — 19.0.1.0.1

The Users and Role Assignment views expose relational fields whose comodel is `onehr.branch`. Odoo's web client must read that comodel to render labels, even when the operator is only reading `res.users` or `onehr.user.role`. Version `19.0.1.0.1` therefore grants read-only branch ACLs to Odoo Technical Admin, OneHR Security Manager and OneHR Security Admin. No create/write/unlink permission is added, no group implication is added, and no record rule is changed.


## Native Users runtime dependency closure — 19.0.1.0.2

The native Users list/search does more than resolve branch relation labels. The current `onehr_security` summary/search implementation traverses `onehr.user.role`, `onehr.role`, `onehr.sod.conflict.log`, and `onehr.audit.log`. Version `19.0.1.0.2` grants Odoo Technical Admin read-only ACLs on those exact support models so the native technical Users action can complete. Existing record-rule XML is unchanged, and all four new ACLs have write/create/unlink set to zero.
