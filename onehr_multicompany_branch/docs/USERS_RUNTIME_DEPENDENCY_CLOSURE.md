
# Native Users Runtime Dependency Closure

Version: `19.0.1.0.2`

## Why the browser returned to Discuss

The failure is not a menu-definition or Discuss-routing defect. The Users action starts, then
its `res.users.web_search_read` cannot complete the requested OneHR fields. When the client
cannot materialize the Users view payload, the navigation does not remain on the failed action.
The server log records the actual actionable failure on `onehr.user.role`.

## Deterministic dependency graph

For the current authoritative source, the relevant native Users runtime graph is:

`Settings → Users`
→ `res.users.web_search_read`
→ OneHR Security/Branch fields injected into native Users list/search
→ `_compute_onehr_security_summary` / search helpers / branch summary
→ support-model reads:

1. `onehr.user.role`
2. `onehr.role`
3. `onehr.sod.conflict.log`
4. `onehr.audit.log`
5. `onehr.branch`

This graph is explicit and finite. The repair does not wait for those models to fail one at a
time in production.

## Surface matrix

| Surface | Runtime dependency | Odoo Technical Admin | Security Manager/Admin |
|---|---|---:|---:|
| Native Users list — OneHR role count | `onehr.user.role`, `onehr.role`, `onehr.audit.log`, `onehr.sod.conflict.log` via shared compute | read closure required | already authorized upstream |
| Native Users list — SoD count | `onehr.sod.conflict.log` plus shared compute dependencies | read closure required | already authorized upstream |
| Native Users search — OneHR Role | `onehr.user.role`, `onehr.role` | read closure required | already authorized upstream |
| Native Users search — SoD filter | `onehr.sod.conflict.log` | read closure required | already authorized upstream |
| Native Users branch columns/search | `onehr.branch` | retained from 19.0.1.0.1 | retained from 19.0.1.0.1 |
| User form OneHR Branch Visibility | `onehr.branch`, `onehr.user.role` | native page visibility unchanged | read closure retained |
| Role Assignment list/form/search/pivot/graph | `onehr.user.role`, `onehr.role`, `onehr.branch`, `res.users`, `res.company` | no menu redesign | read closure retained |

## Security invariants

- no `base.group_user` ACL is introduced;
- every new Technical Admin ACL is read-only;
- record rules are byte-for-byte unchanged from 19.0.1.0.1;
- branch legal-company global partition remains unchanged;
- `onehr.user.role` global branch narrowing remains unchanged;
- no write/create/unlink permission is added by this repair.

## Closure gate

Static acceptance now requires Technical Admin read authority on all five current support models,
not only relational branch comodels. Runtime acceptance separately executes the real Users
list/search dependencies and Security Manager/Admin governance surfaces.
