# onehr_payroll_l10n_id — Enterprise Completeness Matrix

| Area | Source | Windows/runtime | Acceptance |
|---|---|---|---|
| Project identity / target scaffold diagnosis | PASS | N/A | Preflight |
| Exact one product-approved persistent model | PASS | PENDING | Registry/source |
| Exact Registry ED classification | PENDING | PENDING | Exact Registry row required |
| Hard dependency exactly Payroll Bridge | PASS | PENDING | Manifest |
| No payroll/payslip/accounting/API-secret ownership | PASS | PENDING | Source/contracts |
| Effective dating + overlap control | PASS_SOURCE | PENDING | Runtime UAT |
| Regulatory review gate | PASS_SOURCE | PENDING | Runtime UAT |
| Reviewed/used history immutability | PASS_SOURCE | PENDING | Runtime UAT |
| Governed new version/correction | PASS_SOURCE | PENDING | Runtime UAT |
| PPh21/PTKP/Article17/TER parameters | PASS_SOURCE | PENDING | Regulatory sampling |
| Temporary/special PPh21 policy hand-off | PASS_SOURCE | PENDING | External-engine UAT |
| BPJS Kesehatan parameters | PASS_SOURCE | PENDING | Regulatory sampling |
| BPJS TK JHT/JKK/JKM/JP/JKP parameters | PASS_SOURCE | PENDING | Regulatory sampling |
| JP ceiling effective-date guard | PASS_SOURCE | PENDING | Regulatory sampling |
| THR prorata/calendar parameters | PASS_SOURCE | PENDING | Regulatory sampling |
| JSON/CSV parameter export | PASS_SOURCE | PENDING | Runtime UAT |
| JSON/CSV import as new version | PASS_SOURCE | PENDING | Runtime UAT |
| Payroll Bridge frozen localization snapshot/hash | PASS_SOURCE | PENDING | Cross-addon runtime |
| Payroll Bridge source-row compact reference | PASS_SOURCE | PENDING | Cross-addon runtime |
| Integration payload localization section | PASS_SOURCE | PENDING | API-adapter UAT |
| Least-privilege security/company isolation | PASS_SOURCE | PENDING | Security UAT |
| List/Form/Search/Calendar | PASS_SOURCE | PENDING | Browser UAT |
| Smart/body/O2M actions + chatter/report | PASS_SOURCE | PENDING | Browser UAT |
| Statusbar | N/A | N/A | Product workflow explicitly none |
| Fresh install | NOT_RUN | PENDING | Windows Odoo 19 |
| Runtime tests | SOURCE_READY | PENDING | `--test-tags /onehr_payroll_l10n_id` |
| First upgrade | NOT_RUN | PENDING | Windows Odoo 19 |
| Repeated upgrade/idempotency | NOT_RUN | PENDING | Windows Odoo 19 |
| Uninstall/reinstall disposable DB | NOT_RUN | PENDING | Windows Odoo 19 |
| Current regulatory review at deployment | DOCUMENTED | PENDING | Payroll Manager evidence |
| Cross-addon regression | NOT_RUN | PENDING | Current OneHR suite |
| Final enterprise completeness | NOT_RUN | PENDING | All applicable gates |

`SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME_WITH_REGISTRY_AND_DEPLOYMENT_REGULATORY_REVIEW_PENDING`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: NO`
