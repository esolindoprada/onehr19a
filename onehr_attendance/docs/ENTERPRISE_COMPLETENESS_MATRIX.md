# onehr_attendance — Enterprise Completeness Matrix

| Dimension | Source status | Runtime status / evidence required |
|---|---|---|
| Project Identity | PASS | Verify exact deployed addon and root Guardrail hash |
| Architecture Alignment | PASS (source) | Registry must load on Odoo 19 |
| Registry Alignment | PASS (source) | Native overtime concept must map to `hr.attendance.overtime.line` |
| Existing Function Preservation | PASS (source design) | UAT shift/device/reconciliation/overtime |
| Full Structural Inventory | PASS | Compare deployed tree |
| Human-Friendly Structure | PASS | Manual maintainability review |
| Professional Forms | PASS (source) | Open every major form on Odoo web client |
| UI/UX Matrix | PASS | Exercise buttons/statusbars/smart buttons/row actions |
| Search Views | PASS (source) | Search/group filters load without view error |
| Enterprise Lists | PASS (source) | Row actions and decision fields render |
| Server-Side Security | PASS (source design) | Positive/negative user tests on Windows DB |
| Multi-company isolation | PASS (source design) | Cross-company negative runtime test |
| Canonical Odoo Attendance | PASS (source design) | Fresh/upgrade registry + CRUD/runtime test |
| Native Odoo Overtime | PASS (source design) | Native calculate/approve/refuse/regenerate smoke |
| Shift / Pattern / Schedule | PASS (source design) | Day/night/pattern/overlap/missing-punch runtime |
| Import / Timezone / Idempotency | PASS (source design) | Fingerprint CSV runtime scenarios |
| Reconciliation | PASS (source design) | Draft→Review→Approved→Posted runtime scenario |
| ED3 Evidence Protection | PASS (source design) | Delete/write negative runtime tests |
| Reports | PASS (source XML) | Render both QWeb PDFs |
| Upgrade | PENDING | First + repeated upgrade |
| Uninstall / Reinstall | PENDING | Disposable DB evidence, retained business ondelete must not block uninstall |
| Runtime tests | PENDING | Exactly 29 tagged methods must PASS |
| Final functional completeness | PENDING | No applicable FAIL/PENDING before freeze |

SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_ATTENDANCE_MOVE_FORWARD_READY: NO
