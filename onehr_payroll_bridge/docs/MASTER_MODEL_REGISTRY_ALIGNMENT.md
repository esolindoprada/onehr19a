# OneHR Payroll Bridge — Master Model Registry / Product Baseline Alignment

The OneHR product specification proves the following three Payroll Bridge model names
and responsibilities. This package creates **exactly these three custom persistent
business models** and no additional staging/wizard/payslip/costing master.

| # | Model | Ownership / implementation responsibility | ED |
|---:|---|---|---|
| 1 | `onehr.payroll.bridge.config` | Company payroll exchange mapping, non-secret adapter policy, scheduling and reconciliation policy | PENDING exact Registry row |
| 2 | `onehr.payroll.export` | Payroll-period source package, frozen variable/work evidence, posting and reconciliation lifecycle | PENDING exact Registry row |
| 3 | `onehr.payroll.import` | Employee-level vendor payroll result, validation, immutable revision chain and reconciliation evidence | PENDING exact Registry row |

## Canonical ownership preserved

- `hr.employee`: Odoo/Core HR worker master.
- `hr.department`, `hr.job`: Odoo-native work structures.
- `onehr.grade`, `onehr.position`: OneHR Base/Core HR references.
- `hr.attendance` and Odoo-native overtime models: Attendance owner.
- `onehr.leave.*`: Time Off owner.
- `onehr.assignment.cost.allocation`: Assignment owner; Payroll Bridge consumes only if installed.
- localization parameter/rules: `onehr_payroll_l10n_id`.
- integration credentials/endpoints/webhooks: `onehr_integrations_api`.

## Deliberate non-invention

No custom model is created for:

- payroll payslip master;
- payroll work-entry master;
- payroll salary rule/structure master;
- payroll export line/import line;
- payroll reconciliation line;
- accounting cost-posting transaction;
- API credential or webhook log;
- transient import/export wizard.

Batch and employee evidence are represented inside the three product-approved models.
Import corrections reuse `onehr.payroll.import` with revision lineage instead of
inventing a fourth model.

## ED hard gate

The exact Master Model Registry ED classifications for the three Payroll Bridge models
were not surfaced in the authoritative material available to this build. They are not
invented.

`REGISTRY_MODEL_NAMES_ALIGNMENT: PASS`

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

This pending item prevents FINAL/FROZEN status but does not authorize a source worker
to invent or change ownership.
