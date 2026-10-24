
# Cross-Model Comodel-Read Closure Gate

## Purpose

In Odoo, an owner-model read is not enough for a relational field to render. A list/form/search surface that exposes a Many2one/Many2many relation may require the client/server to read the relation's comodel to resolve labels. Therefore access must be closed across the whole surface contract:

`surface actor → owner model read → relational field → comodel read ACL → existing comodel record rules`.

The repair intentionally closes only the missing **ACL** edge. Existing record-rule semantics remain unchanged and continue to narrow legal-company/branch visibility.

## Approved closure matrix

| Surface field | Comodel | Odoo Technical Admin | Branch Admin | Central Office | Security Manager | Security Admin |
|---|---|---:|---:|---:|---:|---:|
| `res.users.onehr_allowed_branch_ids` | `onehr.branch` | Read | Read | Read | Read | Read |
| `res.users.onehr_default_branch_id` | `onehr.branch` | Read | Read | Read | Read | Read |
| `res.users.onehr_effective_branch_ids` | `onehr.branch` | Read | Read | Read | Read | Read |
| `onehr.user.role.branch_id` | `onehr.branch` | N/A | Read | Read | Read | Read |

`N/A` means this addon does not grant Odoo Technical Admin a new OneHR Role Assignment owner-model authority. It only repairs the native Settings / Users branch-comodel dependency.

## Static generic gate

`tools/source_acceptance.py` now:

1. parses model field declarations with Python AST;
2. derives the actual relational comodel for each approved Users/Role Assignment surface field;
3. loads `security/ir.model.access.csv`;
4. verifies that every approved consumer group has explicit read ACL on that derived comodel;
5. verifies the three new production-repair ACLs remain read-only;
6. fails source acceptance if a relation or consumer changes without a corresponding reviewed closure update.

This is intentionally generic at the relational-field/comodel level rather than checking only the literal error field name.

## Runtime generic gate

`tests/test_cross_model_read_closure.py` uses Odoo field metadata (`field.comodel_name`) to discover each relation's comodel. It then reads the owner surface as the target actor and resolves related `display_name` values through the actor's own environment. This reproduces the web-client failure class while retaining normal record rules.

## Security invariant

A comodel-read closure is not a security bypass. PASS requires all three conditions:

- owner surface is legitimately readable;
- comodel ACL permits read;
- comodel record rules still constrain which records can be read.

The runtime negative test explicitly proves another-company branch records remain inaccessible to the repaired actor set.
