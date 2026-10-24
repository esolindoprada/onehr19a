
# OneHR Security — Master Model Registry Alignment

| # | Model | Classification | ED | Ownership / Implementation |
|---:|---|---|---|---|
| 1 | `res.users` | INHERIT_ODOO | ED0 | Canonical Odoo user; OneHR role/security summary and extension hooks only |
| 2 | `onehr.role` | NEW persistent | ED1 | Business role catalogue mapped to canonical `res.groups` |
| 3 | `onehr.user.role` | NEW persistent | ED1 | Effective user-role assignment, company scope and future branch hook |
| 4 | `onehr.sod.matrix` | NEW persistent | ED1 | Effective SoD conflict policy |
| 5 | `onehr.sod.conflict.log` | NEW persistent | ED3 | Immutable conflict and resolution evidence |
| 6 | `onehr.audit.log` | NEW persistent | ED3 | Append-only structured high-risk security audit |

## Canonical Odoo ownership preserved

- User identity: `res.users`.
- Low-level group/access entitlement: `res.groups`.
- Legal-company partition: `res.company`.
- OneHR does not create a parallel user or group model.

## Branch ownership preserved

`onehr.branch` is intentionally absent. `onehr_multicompany_branch` depends on
`onehr_security`, not the reverse. Security therefore enforces company scope now
and exposes narrowly named branch-extension hooks for later narrowing.

## Registry-preserving interpretation of historical scaffold features

The historical description mentioned a User Provisioning Wizard and Record Rule
Templates. Neither has an approved Registry row. Their required capability is
preserved without inventing ownership:

- provisioning = `res.users` + `onehr.user.role` enterprise form/actions;
- low-level permissions = canonical `res.groups`, ACLs and `ir.rule`;
- branch-specific narrowing = later branch addon extension;
- sensitive access = explicit reusable Odoo security groups, not a parallel PII model;
- high-risk audit = approved `onehr.audit.log`.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
