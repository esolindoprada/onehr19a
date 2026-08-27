# onehr_payroll_l10n_id — Integration Contracts

## onehr_payroll_bridge — exact hard dependency

Localization is downstream of Payroll Bridge and uses its approved extension points.

When a Draft Payroll Export is generated:

1. localization resolves exactly one active parameter version for export company + period end;
2. the version must have Payroll Manager regulatory-review evidence;
3. the full parameter payload is frozen on `onehr.payroll.export`;
4. SHA-256 is frozen separately;
5. each employee source row contains only a compact localization code/revision/hash reference;
6. base Payroll Bridge source generation then hashes the employee source rows normally.

Resetting the generated package also clears localization binding. Posting/reconciliation continues
to be owned by Payroll Bridge.

## External payroll engine / OCA adapter

`onehr.payroll.export.onehr_payroll_export_payload()` is extended with a top-level
`indonesia_localization` payload. The external engine remains responsible for actual employee
PPh21/BPJS/THR calculation, payroll rules, payslips and statutory filing.

## onehr_integrations_api — downstream only

No hard dependency and no public route is introduced. The future integration owner can call
normal model payload services and expose authenticated GET/push/pull transport. API keys,
OAuth, SSO, webhook signatures, rate limits and retry queues remain outside localization.

## onehr_corehr / employee tax identity

No new NPWP/NIK/PTKP-status field is added to `hr.employee`. The current Core HR contract does
not expose a product-approved employee tax-status ownership row for this addon. Employee-specific
tax identity/status remains with its approved master/payroll engine; this addon supplies company
statutory parameter tables.

## onehr_timeoff

The product allows optional leave effects on certain THR/components. No statutory leave-deduction
rule is invented. `thr_leave_impact_mode` can explicitly hand employer-specific interpretation to
the external payroll engine.

## onehr_multicompany_branch

Company is the current hard security partition. No `onehr.branch` field is invented because the
branch addon is later and not a hard dependency. An approved branch owner may extend this model
without reversing dependency direction.

## accounting / payment

No GL, analytic, bank-payment or payroll-payment posting is owned here.
