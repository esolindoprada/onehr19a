# OneHR Payroll Localization Indonesia

Enterprise Indonesian payroll-localization **parameter provider** for Odoo 19 Community Edition.

## Approved ownership

Exactly one custom persistent model:

- `onehr.payroll.l10n.param`

Hard dependency:

- `onehr_payroll_bridge`

The addon provides effective-dated PPh21/PTKP/TER, BPJS Kesehatan, BPJS Ketenagakerjaan
and THR parameters to Payroll Bridge or an external payroll engine. It does **not** own
payslip calculation, employee NPWP/PTKP identity, accounting, payment execution, public API
authentication, or API secrets.

## Main operational pattern

1. Payroll Manager creates an effective-dated parameter bundle.
2. Parameter structure is validated.
3. Payroll Manager explicitly records regulatory review evidence.
4. Payroll Bridge resolves the reviewed bundle by company and payroll-period end date.
5. Payroll Bridge freezes the complete localization snapshot + SHA-256 into the generated export.
6. Future changes use a new effective version or governed correction; historical payroll evidence stays frozen.

There is intentionally **no status workflow** because the approved product specification says
the addon is configuration-only. Enterprise interaction is provided through effective dating,
regulatory-review evidence, version/correction actions, smart buttons, row actions, parameter
interchange, Calendar, report and chatter.

Runtime acceptance remains separate from source acceptance.
