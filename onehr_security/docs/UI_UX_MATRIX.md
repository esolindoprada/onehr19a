
# OneHR Security — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart Buttons | Header / Body Actions | Row Buttons | Chatter | Main Security |
|---|---|---|---|---|---|---|---|---|---|
| `onehr.role` | Enterprise | Enterprise | Yes | N/A | Assignments, Effective Users, SoD Rules | Reconcile Assigned Users | Activate/Revoke on assignment O2M | Yes | Read for Security User; manage via Manager/Admin; group mapping Admin-only |
| `onehr.user.role` | Enterprise | Enterprise | Yes | Draft/Active/Blocked/Revoked | Open User, Open Role | Activate, Revoke, Recheck SoD | Activate, Revoke, User | Yes | Self read for Security User; company management for Manager/Admin |
| `onehr.sod.matrix` | Enterprise | Enterprise | Yes | N/A | Conflicts | Scan Effective Assignments | N/A | Yes | Policy read; Manager/Admin manage; company/global scope |
| `onehr.sod.conflict.log` | Read-oriented enterprise | Evidence form | Yes | Open/Accepted/Mitigated/Resolved | Open User, Open Rule | Accept Risk, Mitigate, Resolve | User, Rule | Yes | Append-only detection; controlled Compliance/Admin resolution |
| `onehr.audit.log` | Read-only enterprise | Evidence form | Yes | N/A | Open Target | Controlled Anonymize Payload | Target | Yes | Append-only; Security/Compliance read; retention controlled |
| `res.users` | Native list extended | Native enterprise form extended | Native search extended | Native | Role Assignments, SoD Conflicts, Audit | Reconcile OneHR Access | Role actions on O2M | Native | Company scope + server-side raw-group protection |

## Professional UI rule

Buttons exist only for real operations. Role assignment activation, SoD recheck,
access reconciliation, conflict resolution and audit retention call server-side
methods with authorization checks. `groups=` and `invisible=` are usability
layers and never replace the model security contract.
