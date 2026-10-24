
# Scope Isolation — Bounded Repair 19.0.1.0.2

TARGET: `onehr_multicompany_branch`

ATTEMPT: `2 / 2`

## Allowed changes

- manifest version bump to `19.0.1.0.2`;
- four read-only ACL rows for `base.group_system` on security-owned support models required by
  the native Users runtime path;
- runtime regression tests;
- source-acceptance closure gate;
- repair evidence/documentation.

## Explicitly unchanged

- all `models/*.py` files;
- all `views/*.xml` files;
- `security/onehr_branch_groups.xml`;
- `security/onehr_branch_rules.xml`;
- hard dependency list;
- model ownership;
- business workflow/effective dating/audit implementation;
- every sibling OneHR addon.

The package must fail preservation review if any of those frozen areas differ from the deployed
19.0.1.0.1 baseline without separate approval.
