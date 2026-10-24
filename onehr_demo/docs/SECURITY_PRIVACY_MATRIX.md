
# OneHR Demo — Security & Privacy Matrix

## Control plane

- Viewer: read controlled evidence only.
- Operator/Admin privileges remain defined by existing `onehr_demo` groups.
- High-impact compatibility, enablement, generation, validation, reset and rebuild
  actions require the existing System + Demo Admin server-side authority.
- Company-scoped record rules remain authoritative for scenario/run/checkpoint/reference/log.
- Generator metadata remains code-owned.

## MP05 production authority

MP05 does not use business `sudo()` and does not alter production ACLs or record rules.

Before generation, readiness verifies the current operator can:

- read the selected `res.company`;
- read/create `onehr.branch`;
- read/create `hr.department`;
- administer branches through either Odoo System Administrator or OneHR Branch Admin authority.

The selected company must already have OneHR Branch Scope enabled. The generator
does not silently broaden that legal-company security configuration.

## Privacy

MP05 contains no employee/customer PII. Generated branch/organization names are
fictional demo masters. Existing log sanitization continues to remove passwords,
tokens, API keys and authorization headers from persisted evidence.

