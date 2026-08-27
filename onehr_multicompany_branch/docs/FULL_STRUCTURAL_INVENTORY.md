# Full Structural Inventory

## Manifest

- version `19.0.1.0.0`
- hard dependency exactly `onehr_security`
- no controllers, demo data or placeholder scaffold
- application false; OneHR remains the application shell

## Models

### `onehr.branch`

Persistent ED1 branch master. Key fields: code, name, company, type, parent/children/parent_path, manager user, active, valid_from/to, lifecycle status, notes and controlled counts/flags.

Business methods include normalization, display, lifecycle compute, hierarchy/date/company constraints, reference protection, controlled activate/archive, self-service default selection, smart-button actions and append-only security audit emission.

### `onehr.mixin.branch`

Abstract ED0 helper with optional `branch_id`, default-branch resolution, allowed-branch domain and explicit access validation.

### `res.company`

Adds branch enablement, One2many branch registry, default branch, counts and smart action. The Settings company list/search are extended for branch policy review; policy editing remains technical-admin authority.

### `res.users`

Adds allowed/default/effective branch fields, counts, company intersection/default integrity, controlled branch-scope write policy, Branch Admin actor-company validation, active-role removal guard, security branch-domain hook, branch-aware effective group derivation and smart actions.

### `onehr.user.role`

Security-owned model extension: `branch_id`, effective/company/user integrity, branch identity freeze, overlap semantics, branch scope label, branch-aware activation and audit.

## Security

- four branch groups under an Odoo 19 privilege: Branch User, Branch Manager, Branch Admin, Central Office;
- 7 ACL rows, none granted directly to `base.group_user`;
- branch company global rule;
- explicit branch-scope rule;
- branch admin company administration rule;
- Branch Admin res.users company rule with authoritative Python field restriction and actor legal-company validation;
- global `onehr.user.role` company + self-history + branch narrowing rule.

## Views and actions

- `onehr.branch`: enterprise list, form, search, actions;
- res.company: inherited branch configuration + smart button + enterprise list/search integration;
- res.users: inherited branch scope/visibility pages, stat buttons, list/search extension;
- onehr.user.role: inherited list/form/search branch field plus pivot/graph role coverage;
- OneHR Organization menus for My Branches, Branches and Branch Role Coverage.

## Runtime tests

Exactly 18 post-install methods across three files covering registry, lifecycle, hierarchy, company/default integrity, ACL/server authorization, record-rule isolation, central visibility, role overlap, SoD branch semantics, managed-group reconciliation and audit evidence.
