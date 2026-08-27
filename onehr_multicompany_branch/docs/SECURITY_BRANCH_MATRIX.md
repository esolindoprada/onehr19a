# Security & Branch Scope Matrix

| Persona | Branch master | User branch scope | Role assignments | Consolidation | Server-side authority |
|---|---|---|---|---|---|
| Branch User | Read explicit allowed branches | No scope expansion; controlled own default only | None unless another OneHR security role grants it | No | record rules + quick-selector authorization |
| Branch Manager | Read explicit allowed branches | No scope administration | None by this addon | No | no structural write ACL |
| Branch Admin | Create/update branch masters in allowed companies | May change only branch fields on company-scoped users and only with branch IDs visible in the admin's legal-company scope | Read only for branch governance; security workflow still owned by Security Manager | Branch operational | `require_branch_admin`, res.users field-bound + actor-scope guard, company/branch constraints |
| Central Office | Read explicit allowed branches | Read-only | Read branch/company scoped role coverage | Yes, only explicit branches | no mutation ACL |
| OneHR Security Manager/Admin | Existing security authority retained | Read branch visibility; does not automatically become Branch Admin | Existing create/activate/revoke authority narrowed by branch rule | According to explicit branch scope | security addon actions + branch global rule |
| Odoo Technical Admin | Native Odoo authority | Native technical authority | Native technical authority | Technical | super/system authority; still subject to business constraints where applicable |

## Non-negotiable boundaries

1. `res.company` remains the outer legal/security partition.
2. Branch scope never adds a company to `res.users.company_ids`.
3. Branch Admin ACL on `res.users` is constrained in Python to branch fields for other users, and branch IDs are validated through the caller's normal company/branch record rules.
4. Security Manager activation remains the only normal path for role assignment activation.
5. Global Odoo group membership is recalculated from effective role assignments and filters branch-specific rows to authorized/effective branches.
6. Central visibility requires explicit `onehr_allowed_branch_ids`; it is not an automatic company-wide bypass.
