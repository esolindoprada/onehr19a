# OneHR Payroll Bridge — Direct Full Implementation Report

The uploaded Payroll Bridge source was a generic Odoo tutorial scaffold and did not
implement the approved payroll bridge product contract. This Direct Full build replaces
that placeholder with the three product-specified models while preserving frozen
OneHR ownership and dependency direction.

## Enterprise behavior implemented

- company payroll interchange configuration;
- human-editable JSON field/structure mapping;
- CSV/manual exchange plus explicit adapter boundary;
- employee payroll-period source collection;
- optional Attendance/Overtime/Time Off/Assignment costing consumption without hard
  dependency reversal;
- deterministic CSV generation;
- frozen source/config snapshots and SHA-256 source fingerprint;
- Draft → Posted to Payroll → Reconciled lifecycle;
- vendor CSV result import;
- employee/vendor-reference validation;
- optional gross-deductions=net tolerance;
- immutable import corrections using revision lineage;
- reconciliation coverage %, imported totals and time-to-close KPI;
- department costing payload;
- QWeb reconciliation report plus Pivot/Graph analysis;
- monthly Draft preparation scheduler that never auto-posts payroll;
- least-privilege Officer/Manager security and company isolation.

## Ownership deliberately not taken

No payroll calculation engine, salary rule/structure master, PPh21/BPJS/THR formula,
payment execution, GL/analytic posting, API credential or public integration controller
is created.

`SOURCE_DIRECT_FULL_BUILD: BUILT`

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: NO`

- Native Odoo `hr.work.entry` is consumed dynamically when installed; Draft/Validated work entries are exported without generation or mutation.
