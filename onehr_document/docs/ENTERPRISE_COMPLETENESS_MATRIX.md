# onehr_document — Enterprise Completeness Matrix

| Dimension | Status | Evidence / rule |
|---|---|---|
| Project Identity | PASS | `PROJECT_IDENTITY_PREFLIGHT.md` |
| Architecture Alignment | PASS (source) | Canonical document ownership and hard dependency contract |
| Registry Alignment | PASS (source) | Exactly 8 approved rows |
| Existing Function Preservation | PASS (source design) | `BASELINE_FEATURE_PRESERVATION_MATRIX.md` |
| Full Structural Inventory | PASS | `FULL_STRUCTURAL_INVENTORY.md` |
| Human-Friendly Structure | PASS (source) | Domain-split models/wizards/views |
| Professional Forms | PASS (source) | Statusbars, smart buttons, body and row actions |
| UI/UX Matrix | PASS | `UI_UX_MATRIX.md` |
| Search Views | PASS (source) | All 6 persistent models |
| Enterprise Lists | PASS (source) | Business columns, badges/decorations and row actions |
| Server-Side Security | PASS (source design) | Company + sensitivity + ownership; no broad base-user ACL |
| Restricted Privacy | PASS (source design) | Compliance/dual gate; no provider secret fields |
| Source Record Authorization | PASS (source) | ORM `check_access("read")`, no sudo |
| Attachment Access Contract | PASS (source design) | Attachment-backed Binary on protected version; no public controller |
| Effective Dating / Versioning | PASS (source) | ED1/ED2 intervals, immutable issued/template versions |
| Expiry / Reminder | PASS (source) | dates, activity action, daily cron |
| E-Sign Evidence | PASS (source) | ED3 transaction/correlation/status + terminal immutability |
| QWeb PDF Report | PASS (source) | Odoo 19 report action + report template |
| Tests | PASS (source inventory) | 19 post-install test methods |
| Fresh Install | PENDING | Target Windows/Odoo runtime |
| Runtime Tests | PENDING | Disposable database |
| First Upgrade | PENDING | Runtime acceptance |
| Repeat Upgrade / Idempotency | PENDING | Runtime acceptance |
| Post-Upgrade Contract Smoke | PENDING | Runtime acceptance |
| Attachment URL Runtime Security | PENDING | Runtime HTTP/model-access verification |
| Uninstall / Reinstall | PENDING | Runtime acceptance |
| Sibling Addon Fingerprint | PENDING DEPLOY | `deploy_to_workspace.ps1` |
| Documentation | PASS | Preflight, Registry, preservation, inventory, UI/security/completeness |
| Functional Completeness Final Review | PENDING | After all runtime evidence |
| Final Freeze | PENDING | User/runtime acceptance |
| MOVE_FORWARD_READY | NO | Runtime and final review remain PENDING |

`ONEHR_DOCUMENT_MOVE_FORWARD_READY: YES` is forbidden while any applicable
runtime or enterprise-completeness item is PENDING or FAIL.
