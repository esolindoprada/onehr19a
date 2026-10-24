
# OneHR Security — Enterprise Completeness Matrix

| Dimension | Status before Windows runtime | Evidence |
|---|---|---|
| Project Identity | PASS | `PROJECT_IDENTITY_PREFLIGHT.md` |
| Architecture Alignment | PASS (source) | Native users/groups; branch dependency direction preserved |
| Registry Alignment | PASS (source) | Exactly six Registry rows/extension ownership |
| Existing Function Preservation | PASS (source design) | Historical intended roles/provisioning/SoD/audit/privacy/compliance capability reconstructed |
| Full Structural Inventory | PASS | `FULL_STRUCTURAL_INVENTORY.md` |
| Human-Friendly Structure | PASS (source) | Domain-focused model/view files |
| Professional Forms | PASS (source) | Workflow, smart/body/row actions, notebooks/chatter |
| UI/UX Matrix | PASS | `UI_UX_MATRIX.md` |
| Search Views | PASS (source) | All five custom persistent models |
| Enterprise Lists | PASS (source) | Operational fields, badges/decorations/actions |
| Server-Side Security | PASS (source design) | ACL/rules/model guards; no broad generic-user CRUD |
| Effective Dating | PASS (source) | Role, user-role and SoD policy |
| History/Audit | PASS (source design) | Append-only audit; immutable conflict decisions |
| Workflow/Actions | PASS (source) | Activate/revoke/reconcile/scan/resolve/retention |
| Tests | PASS (source inventory) | Exactly 12 post-install methods |
| Fresh Install | PENDING | Target Windows/Odoo disposable DB |
| Runtime Tests | PENDING | Target Windows/Odoo |
| Upgrade | PENDING | Target Windows/Odoo |
| Repeat Upgrade / Idempotency | PENDING | Target Windows/Odoo |
| Post-Upgrade Smoke | PENDING | Target Windows/Odoo |
| Uninstall Safety | SOURCE HARDENED / RUNTIME PENDING | `@api.ondelete(at_uninstall=False)` + uninstall/reinstall gate |
| Documentation | PASS | Governance, registry, inventory, UI/security/completeness reports |
| Runtime Evidence | PENDING | Windows acceptance gate |
| Functional Completeness | PENDING FINAL RUNTIME REVIEW | Static PASS is not enterprise completion |
| Final Freeze | PENDING | After runtime/completeness acceptance |
| MOVE_FORWARD_READY | NO | Runtime evidence still pending |

A static/source PASS cannot turn `MOVE_FORWARD_READY` into YES.
