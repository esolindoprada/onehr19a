# Master Model Registry Alignment

The product baseline proves exactly one localization business model:

| # | Model | Ownership | ED |
|---:|---|---|---|
| 1 | `onehr.payroll.l10n.param` | Effective-dated Indonesia payroll-localization parameters | PENDING exact Registry row |

No other custom persistent or transient model is created.

## Deliberate non-invention

Not created:

- PTKP child table model;
- TER bracket child model;
- BPJS scheme/rate child model;
- THR calendar child model;
- PPh21 simulation wizard/model;
- employee tax identity model;
- payroll payslip/salary-rule model;
- accounting/payment model;
- API credential/webhook model.

Structured statutory tables are explicit human-readable JSON fields inside the single
product-approved model. Payroll Bridge is extended only through normal `_inherit`.

The exact Master Model Registry ED classification for `onehr.payroll.l10n.param` was not
surfaced in the authoritative material available to this build. It is not guessed.

`REGISTRY_MODEL_NAME_ALIGNMENT: PASS`

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

`ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: NO`
