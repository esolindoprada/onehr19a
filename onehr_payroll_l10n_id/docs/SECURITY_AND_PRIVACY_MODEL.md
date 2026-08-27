# onehr_payroll_l10n_id — Security and Privacy

## Payroll Manager

The product-specified management authority. Can create/edit unused parameter versions, record
regulatory review, create new versions/corrections, import/export parameters, inspect history,
open linked payroll exports and print the parameter record.

## Payroll Officer

Read-only ACL is intentionally provided because Payroll Bridge Officers generate payroll exports
and the bridge must resolve/read a reviewed localization bundle. There is no localization
configuration menu for Officers and model methods prevent modification.

## Internal users without payroll authority

No custom-model ACL.

## Company isolation

Explicit allowed-company record rule applies to the single localization model. Cross-company
parameter identity is validated by the model.

## Historical integrity

- used parameter versions cannot be rewritten;
- reviewed/versioned identity cannot be rewritten;
- regulatory edits invalidate review evidence;
- new versions close predecessors through governed action;
- corrections supersede but preserve prior versions;
- effective/used history cannot be deleted;
- uninstall is not blocked because deletion protection uses `@api.ondelete(at_uninstall=False)`.

## Privacy minimization

The localization model stores no employee PII, NPWP/NIK, salary, bank data, medical data,
dependents or document copies.

## Secrets

No token, password, API key, OAuth secret, webhook secret or private key field exists.
