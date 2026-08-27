# OneHR Payroll Bridge — Bounded Implementation Evidence

TASK_ID: `ONEHR-PAYROLL-BRIDGE-DIRECT-FULL-20260820-A1`

ATTEMPT: `1 / 2`

ROLE: `BOUNDED_IMPLEMENTATION_WORKER`

TARGET_ADDON: `onehr_payroll_bridge`

WRITE_SCOPE: `/mnt/data/onehr_payroll_bridge_direct_full_20260820`

INPUT_BASELINE:
- latest uploaded OneHR workspace dump: `onehr19a(20260820-065355).md`
- OneHR root Enterprise Development Guardrail
- OneHR 25 Addons Specification
- Oracle HRMS functional benchmark
- currently accepted sibling integration contracts

NORMALIZED_TARGET_BASELINE_FILE_COUNT: `10`

NORMALIZED_TARGET_BASELINE_SHA256:
`e981aab509dd74ab8159cd3479e12b69d0175509934613dfc5d037628dbb9f88`

ROOT_CAUSE_CLASSIFICATION:
`ADDON_SOURCE_FAILURE`

ROOT_CAUSE:
The supplied `onehr_payroll_bridge` target remained a generic Odoo tutorial scaffold and
did not implement the approved OneHR Payroll Bridge product contract.

APPROVED_CHANGE:
Registry/product-preserving Direct Full reconstruction of the target addon only.

FILES_CHANGED:
All generated files are under the isolated target build path. No sibling addon source
was written.

CUSTOM_PERSISTENT_MODELS:
Exactly three:
1. `onehr.payroll.bridge.config`
2. `onehr.payroll.export`
3. `onehr.payroll.import`

HARD_DEPENDENCIES:
Exactly:
- `onehr_corehr`
- `onehr_security`

SECURITY:
- explicit Payroll Officer / Payroll Manager;
- company record rules;
- no `base.group_user` custom CRUD;
- no business `sudo()`;
- no API credential ownership;
- immutable posted/reconciled evidence.

ENTERPRISE UI:
Statusbar, header actions, smart buttons, body actions, One2many row actions, chatter,
Calendar, Pivot, Graph, explicit Search views and QWeb reconciliation report.

SOURCE_ACCEPTANCE:
Executed by `tools/source_acceptance.py`.

WINDOWS_RUNTIME:
Not executed in this build environment.

REGISTRY_ED_CLASSIFICATION:
Pending exact Master Model Registry row verification; ED labels were not invented.

STOP / MOVE-FORWARD STATUS:
No architecture redesign was performed. Source is ready for Windows runtime acceptance,
but FINAL/FROZEN/MOVE_FORWARD_READY remains prohibited until Registry ED and runtime
gates pass.

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: NO`
