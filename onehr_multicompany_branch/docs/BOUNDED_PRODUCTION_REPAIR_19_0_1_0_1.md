
# OneHR Multicompany & Branch — Bounded Production Repair 19.0.1.0.1

TASK_ID: `ONEHR-MULTICOMPANY-BRANCH-CROSS-MODEL-READ-CLOSURE-20260908`

ATTEMPT: `1 / 2`

TARGET_ADDON: `onehr_multicompany_branch`

WRITE_SCOPE: `onehr_multicompany_branch/**` only

ROOT_CAUSE_CLASSIFICATION: `ADDON_SOURCE_FAILURE`

## Proven failure class

A caller can legitimately read the owner model (`res.users` or `onehr.user.role`) while still lacking read ACL on the relational comodel `onehr.branch`. Odoo web rendering then fails when it resolves branch labels for fields such as:

- `res.users.onehr_allowed_branch_ids`;
- `res.users.onehr_default_branch_id`;
- `res.users.onehr_effective_branch_ids`;
- `onehr.user.role.branch_id`.

This is a cross-model read-authority contract defect, not a reason to broaden branch record rules or redesign OneHR security.

## Approved repair

Version `19.0.1.0.1` adds explicit **read-only** ACLs on `onehr.branch` for:

- `base.group_system` — Odoo Technical Administration;
- `onehr_security.group_onehr_security_manager`;
- `onehr_security.group_onehr_security_admin`.

Permissions are exactly read=1, write=0, create=0, unlink=0.

The repair does **not**:

- change the hard dependency (`onehr_security` remains exact);
- add or move a model;
- alter model ownership;
- change branch/company record-rule domains;
- imply Branch Admin from Security Manager/Admin;
- grant Security Manager/Admin branch create/write/unlink;
- change role-assignment workflow, overlap/SoD, effective dating or audit semantics;
- modify any sibling addon.

## Closure surfaces audited

### Settings / Users

- native Users list: `onehr_default_branch_id`, effective branch count;
- Users search: default/allowed branch search and grouping;
- OneHR Branch Visibility tab for Security Manager/Admin;
- branch smart actions from a user;
- security-owned Role Assignment One2many extended with `branch_id`.

### OneHR Security / Role Assignments

- list `branch_id`;
- form `branch_id`;
- search/filter/group-by `branch_id`;
- branch role coverage Pivot/Graph;
- user-to-role navigation that resolves branch display names.

## Runtime regression contract

Five post-install tests are added:

1. Users branch relational surfaces resolve for Odoo Technical Admin, Security Manager and Security Admin.
2. Role Assignment branch relational surface resolves for Security Manager/Admin.
3. Existing legal-company branch record-rule boundary remains intact.
4. New read ACLs do not add branch mutation authority.
5. Users/Role Assignment actions resolve branch records without comodel AccessError.

Runtime execution is still required on the user's real Odoo 19 CE database; source packaging does not claim that runtime gate.

## Acceptance status

SOURCE_STATIC: `PASS`

WINDOWS_UPGRADE: `NOT_RUN`

RUNTIME_REGRESSION: `NOT_RUN`

REPEAT_UPGRADE_IDEMPOTENCY: `NOT_RUN`

POST_UPGRADE_UI_SMOKE: `NOT_RUN`

ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: `NO`
