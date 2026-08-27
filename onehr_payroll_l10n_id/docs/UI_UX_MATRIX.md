# onehr_payroll_l10n_id — UI/UX Matrix

| Model | List | Form | Search | Calendar | Enterprise interactions |
|---|:---:|:---:|:---:|:---:|---|
| `onehr.payroll.l10n.param` | YES | YES | YES | YES | History/Payroll Export smart buttons; Validate/Review/JSON/CSV body actions; New Version/Correction/Import actions; TER lookup preview; successor One2many row Open; effective-period ribbons; chatter; QWeb parameter report |
| `onehr.payroll.export` inherited | existing | inherited | existing | existing | ID Parameters smart button; frozen localization parameter/hash; full localization snapshot notebook |
| `onehr.payroll.bridge.config` inherited | existing | inherited | existing | N/A | Localization ID smart navigation |

## Statusbar decision

`STATUSBAR_WIDGET: NOT_APPLICABLE_BY_PRODUCT_CONTRACT`

The approved product specification explicitly states **Workflow: none — configuration only**.
Creating a fake Draft/Approved lifecycle would be architecture invention. Enterprise quality is
provided through effective dating, regulatory-review evidence, historical immutability, governed
version/correction actions and audit chatter instead.

## Pivot/Graph decision

A configuration-only one-model addon has no honest transaction-level KPI measure to aggregate.
The product KPI "calculation accuracy in audit sampling" belongs to payroll result/reconciliation
evidence downstream. A meaningless parameter-count graph is intentionally not created.
