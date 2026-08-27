# OneHR Payroll Localization Indonesia — Direct Full Implementation Report

## Root cause

`ADDON_SOURCE_FAILURE`

The supplied target remained the generic Odoo tutorial scaffold and had no approved localization
business implementation.

## Direct Full result

Replaced the target scaffold with a Registry/product-preserving enterprise addon that:

- owns exactly `onehr.payroll.l10n.param`;
- depends exactly on `onehr_payroll_bridge`;
- provides effective-dated Indonesian statutory/company parameter bundles;
- includes complete editable PPh21/PTKP/Article17/TER A/B/C default tables;
- includes BPJS Health + Employment program parameters;
- includes THR prorata/wage-basis/deadline/calendar parameters;
- requires explicit regulatory-review evidence before payroll use;
- freezes parameter snapshot + SHA-256 into Payroll Bridge generation;
- preserves frozen employee-source hash behavior via a compact localization reference;
- supports governed version/correction history;
- imports/exports parameter JSON/CSV without a staging/wizard model;
- uses Manager administration + Officer read-only integration security;
- provides professional List/Form/Search/Calendar, smart/body/O2M actions, QWeb report and chatter.

## Deliberate non-features

- no fake lifecycle/statusbar because product workflow is none;
- no full employee PPh21 simulation because employee tax identity/status and payroll engine
  ownership are not approved here;
- no payslip/salary-rule engine;
- no accounting/payment;
- no public API/controller or credentials;
- no branch hard dependency;
- no extra statutory table models.

`DIRECT_FULL_SOURCE_BUILD: BUILT`

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: NO`
