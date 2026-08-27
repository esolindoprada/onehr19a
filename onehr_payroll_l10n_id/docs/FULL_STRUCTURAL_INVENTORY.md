# onehr_payroll_l10n_id — Full Structural Inventory

## Persistent ownership

Exactly one custom persistent model:

### `onehr.payroll.l10n.param`

Responsibilities:

- company/currency identity;
- effective dating and no-overlap control;
- revision/predecessor/successor history;
- explicit regulatory-review evidence;
- PPh21/PTKP/TER and Article 17 parameter tables;
- gross/gross-up default-method parameter;
- job-expense parameters;
- optional special PPh21 policy JSON hand-off;
- BPJS Kesehatan PPU rates/floor/ceiling;
- JHT/JKK/JKM/JP/JKP configuration;
- effective-dated JP wage ceiling;
- THR minimum service, prorata, wage basis, deadline and optional company calendar;
- JSON/CSV parameter export/import as a governed new version;
- immutable SHA-256 parameter material;
- human-readable history/navigation/reporting.

## Inherited existing models — no new ownership

### `onehr.payroll.export`

Adds only:

- `onehr_l10n_param_id`;
- `onehr_l10n_snapshot_json`;
- `onehr_l10n_sha256`;
- generation/reset/payload extension hooks.

### `onehr.payroll.bridge.config`

Adds manager navigation to Indonesia localization parameters.

## Files

- `models/localization_parameter.py` — single approved business model.
- `models/payroll_bridge_extension.py` — downstream bridge extensions.
- `models/regulatory_defaults.py` — readable regulatory defaults only.
- `models/action_helpers.py` — UI action helpers only.
- `security/*` — Officer read / Manager administration + company isolation.
- `views/parameter_views.xml` — List/Form/Search/Calendar.
- `views/payroll_bridge_views.xml` — localization evidence in Payroll Bridge.
- `reports/localization_parameter_report.xml` — parameter record QWeb PDF.
- `tests/*` — runtime acceptance source.
- `docs/*` and `tools/source_acceptance.py` — hard-gate evidence.

## Tutorial scaffold removed

No generic tutorial controller, generic placeholder model, demo data, `views/views.xml`,
or `views/templates.xml` remains active in the package.
