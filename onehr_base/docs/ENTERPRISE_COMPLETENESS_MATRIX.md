# OneHR Base — Enterprise Completeness Matrix

| Dimension | Status | Evidence / Rule |
|---|---|---|
| Project Identity | PASS | `PROJECT_IDENTITY_PREFLIGHT.md` |
| Architecture Alignment | PASS (source) | Odoo-native first; no parallel HR masters |
| Registry Alignment | PASS (source) | Exactly 19 approved rows |
| Existing Function Preservation | PASS (source design) | Corrected source capabilities retained and expanded without model loss |
| Full Structural Inventory | PASS | `FULL_STRUCTURAL_INVENTORY.md` |
| Human-Friendly Structure | PASS (source) | Domain-split Python/XML; pure helpers; readable actions |
| Professional Forms | PASS (source) | Statusbars, smart buttons, notebooks, ribbons, body action |
| UI/UX Matrix | PASS | `UI_UX_MATRIX.md` |
| Search Views | PASS (source) | Every user-facing custom persistent model has search coverage |
| Enterprise Lists | PASS (source) | Business columns, state badges/decorations and row actions |
| Server-Side Security | PASS (source design) | 28 ACL rows; no `base.group_user`; company rules |
| Effective Dating | PASS (source) | Native ED1 + registry-approved effective-dated mixin |
| History/Audit | PASS (source) | mail tracking + completed checklist protection |
| Workflow/Actions | PASS (source) | Normal ORM; no business authorization `sudo()` bypass |
| Tests | PASS (source inventory) | Exactly 12 test methods |
| Fresh Install | PENDING | Target Odoo 19 runtime required |
| Runtime Tests | PENDING | Disposable DB required |
| Upgrade | PENDING | Runtime acceptance gate |
| Repeat Upgrade/Idempotency | PENDING | Runtime acceptance gate |
| Post-Upgrade Smoke | PENDING | Runtime acceptance gate |
| Uninstall Safety | SOURCE HARDENED / RUNTIME PENDING | `@api.ondelete(at_uninstall=False)` |
| Documentation | PASS | Preflight, registry, inventory, UI/UX, report, matrix |
| Runtime Evidence | PENDING | Windows runtime required |
| Functional Completeness | PENDING FINAL RUNTIME REVIEW | Source PASS is not runtime completion |
| Final Freeze | PENDING | After runtime acceptance |
| MOVE_FORWARD_READY | NO | Runtime items still PENDING |

`ONEHR_BASE_MOVE_FORWARD_READY: YES` is forbidden while any applicable runtime
item remains PENDING or FAIL.
