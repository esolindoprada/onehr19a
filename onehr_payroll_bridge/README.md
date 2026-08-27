# OneHR Payroll Bridge

Enterprise payroll interchange boundary for **Odoo 19 Community Edition**.

## Core model ownership

- `onehr.payroll.bridge.config`
- `onehr.payroll.export`
- `onehr.payroll.import`

Hard dependencies are exactly `onehr_corehr` and `onehr_security`.

## Main workflow

1. Configure payroll mapping and exchange policy.
2. Prepare a Draft payroll export for a period.
3. Generate the frozen CSV/source package.
4. Payroll Manager posts the package to the payroll boundary.
5. Import vendor payroll result CSV or ingest results through an authorized downstream adapter.
6. Validate current employee result revisions.
7. Reconcile the payroll batch.
8. Review/print reconciliation and department costing evidence.

## Ownership boundaries

This addon does not calculate payroll, PPh21/BPJS/THR, execute payment, own GL/analytic
masters, or store API credentials. Those responsibilities remain with their approved
engines/adapters.

## Runtime status

Source acceptance is included under `docs/SOURCE_ACCEPTANCE_REPORT.txt`.
Windows/Odoo runtime acceptance is intentionally separate and still required before
the addon may be declared FINAL/FROZEN.
