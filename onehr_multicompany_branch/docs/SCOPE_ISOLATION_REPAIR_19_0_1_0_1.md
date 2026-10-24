
# Scope Isolation — Bounded Repair 19.0.1.0.1

TASK_ID: `ONEHR-MULTICOMPANY-BRANCH-CROSS-MODEL-READ-CLOSURE-20260908`

WRITE_SCOPE: `onehr_multicompany_branch/**` only

## Frozen production logic hashes

The bounded repair does not alter production model implementation or XML views.

| Surface | Baseline SHA-256 | Repaired SHA-256 | Result |
|---|---|---|---|
| `models/**` | `119D9CA1181E4FA7FAA7A6ED4036375536A865081F05002770D0AF3CB5600DB9` | `119D9CA1181E4FA7FAA7A6ED4036375536A865081F05002770D0AF3CB5600DB9` | SAME |
| `views/**` | `D04F6D9F6A24A1F80B5EB96D057177E90321FA1405E73D119CB6EB336C409A20` | `D04F6D9F6A24A1F80B5EB96D057177E90321FA1405E73D119CB6EB336C409A20` | SAME |
| `security/onehr_branch_rules.xml` | `4C9F8DB16CCA71A9A56F72D7AA9EC902DCDF341300C5359C8103A61B8D185930` | `4C9F8DB16CCA71A9A56F72D7AA9EC902DCDF341300C5359C8103A61B8D185930` | SAME |
| `security/onehr_branch_groups.xml` | `E4CD685D44E04FB970A79679C73C8E176C67FF15BB5E745012E1D73798454683` | `E4CD685D44E04FB970A79679C73C8E176C67FF15BB5E745012E1D73798454683` | SAME |

This proves the repair does not change branch business methods, workflow, effective dating, model ownership, UI architecture, group hierarchy, or record-rule semantics.

## Intentional production change

Only `security/ir.model.access.csv` changes production access behavior, by adding three explicit read-only ACL rows on `onehr.branch` for:

- Odoo Technical Admin (`base.group_system`);
- OneHR Security Manager;
- OneHR Security Admin.

All three rows are `read=1, write=0, create=0, unlink=0`.

## Test/tool/documentation changes

The remaining changes are limited to:

- manifest version bump to `19.0.1.0.1`;
- test fixture additions for Technical Admin and Security Admin;
- five new runtime regression methods;
- generic static comodel-read closure gate;
- repair evidence/governance documentation.

## Sibling isolation

No `onehr_security` source file is modified. The reference hash of the supplied sibling source snapshot used during this review is:

`27A09DAC37CEA3B4D1BF1702A42F5CF046D6A633EAED5AE0FDEADE71255C449B`

SIBLING_SOURCE_MUTATION: `NONE`

SCOPE_ISOLATION: `PASS`
