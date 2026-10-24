
# OneHR Multicompany & Branch — Bounded Production Repair 19.0.1.0.2

TASK_ID: `ONEHR-MULTICOMPANY-BRANCH-USERS-RUNTIME-CLOSURE-20260909`

ATTEMPT: `2 / 2`

TARGET_ADDON: `onehr_multicompany_branch`

WRITE_SCOPE: `onehr_multicompany_branch/**` only

ROOT_CAUSE_CLASSIFICATION: `ADDON_SOURCE_FAILURE — INCOMPLETE RUNTIME DEPENDENCY CLOSURE`

## Runtime evidence

The real Odoo 19 runtime log proves that native Settings → Users reaches
`res.users.web_search_read` and fails because uid 2 (Odoo Technical Admin) cannot read
`onehr.user.role` while the Users surface asks for `res.users.onehr_role_assignment_ids`.

The prior 19.0.1.0.1 repair correctly closed `onehr.branch` relational label reads, but its
generic gate was under-scoped: it modeled only relational comodel label resolution and did not
model the complete upstream compute/search dependency graph added by `onehr_security` to the
native Users list/search contract.

## Full-path source audit

The authoritative composite source shows that the native Users list/search can transitively
reach all of the following support models:

- `onehr.user.role` through role-assignment One2many and effective-role search/compute;
- `onehr.role` through role state/effective-date evaluation;
- `onehr.sod.conflict.log` through the SoD summary/search helper;
- `onehr.audit.log` through the monolithic OneHR security summary compute;
- `onehr.branch` through branch default/effective summary and relational labels.

Therefore fixing only the next failing comodel would be reactive and incomplete.

## Approved correction in 19.0.1.0.2

The addon adds four Odoo Technical Admin read-only ACLs for the security-owned support models
above that were still missing. The existing 19.0.1.0.1 read-only `onehr.branch` ACL is retained.
All five Technical Admin closure ACLs are exactly:

- read = 1;
- write = 0;
- create = 0;
- unlink = 0.

Existing OneHR Security Manager/Admin ACLs on the security-owned models remain authoritative;
existing branch read ACLs for those roles are retained.

## Explicit preservation

This Attempt 2 does NOT change:

- dependency topology (`onehr_security` remains the only hard dependency);
- model ownership or model registry;
- any Python business model code;
- any branch/security record-rule domain;
- any group implication;
- role assignment workflow, SoD workflow, effective dating, overlap rules or audit semantics;
- any Users/Role Assignment form/list/search/pivot/graph architecture;
- any sibling OneHR addon.

## Runtime regression additions

Five additional post-install regressions close the actual path, bringing the addon to 28 tests:

1. native Users list-style `search_read` as Odoo Technical Admin;
2. native Users OneHR search helpers as Odoo Technical Admin;
3. explicit read closure on all five current support models;
4. read-only permission verification for all Technical Admin closure ACLs;
5. Security Manager/Admin full Users + Role Assignment + Branch surface regression.

## Retry boundary

This is Attempt 2/2 for this bounded repair task. If the same Users runtime closure fails again,
source mutation must stop and the next evidence must be reviewed under a newly authorized task.

SOURCE_STATIC: `PASS — source acceptance V3`

WINDOWS_UPGRADE: `NOT_RUN`

RUNTIME_REGRESSION: `NOT_RUN`

REPEAT_UPGRADE_IDEMPOTENCY: `NOT_RUN`

POST_UPGRADE_UI_SMOKE: `NOT_RUN`

ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: `NO`
