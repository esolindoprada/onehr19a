
# OneHR Security — Security Control Matrix

| Control | Enforcement |
|---|---|
| Generic internal user custom-model CRUD | Not granted |
| Security User | Read role catalogue; self role assignment/SoD evidence |
| Security Manager | Company-scoped role provisioning and policy operations |
| Security Admin | Role-to-Odoo-group mapping authority; safe basic user provisioning; no raw Odoo group/multi-company entitlement bypass |
| Compliance Officer | Company-scoped evidence review and controlled SoD/audit decisions |
| Raw `res.users.group_ids` edits by OneHR Security Manager/Admin | Server-side denied; functional access must use effective OneHR roles |
| Business role → technical Access Rights/Admin groups | Server-side denied |
| Business role → Security governance groups | Server-side denied |
| Business role → portal/public/technical groups | Server-side denied |
| Sensitive/Restricted data access | Explicit groups, not implied by Security Admin |
| User-role start/end dates | Effective-dated; daily root reconciliation |
| Manual groups not managed by OneHR roles | Preserved by reconciliation |
| Cross-company/branch effective roles | Reconciliation unions all effective assignments before changing global Odoo group membership |
| Role / SoD policy deletion | Normal deletion prohibited; archive to preserve governed history |
| SoD warn | Evidence created; role may activate |
| SoD deny | Evidence created; activation blocked |
| Existing access after later SoD policy change | Scan/evidence; no silent retroactive privilege mutation |
| SoD resolution evidence | Finalized decision immutable |
| High-risk audit | Append-only structured record |
| Audit payload retention/anonymization | Admin/Compliance controlled; evidence retained |
| Privileged internal elevation | Only append-only evidence persistence + read-only global entitlement derivation; never business authorization |
| Company boundary | ACL/rules + user/role scope checks |
| Branch boundary | Deferred to branch owner; extension hooks exposed |
| UI visibility | Never treated as authorization |
| Module uninstall | `uninstall_hook` revokes OneHR-managed group memberships; deletion protections use `@api.ondelete(at_uninstall=False)` |

## Sensitive data policy

`group_onehr_sensitive_data_reader` and
`group_onehr_restricted_data_reader` are explicit reusable security gates.
They are intentionally **not implied** by Security Admin/Manager/Compliance.
Future data-owning addons may bind sensitive fields/models to these groups or
define narrower domain-specific groups. This prevents "security administrator"
from automatically becoming a reader of all future sensitive HR content.
