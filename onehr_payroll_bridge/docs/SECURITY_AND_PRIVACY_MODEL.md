# onehr_payroll_bridge — Security and Privacy Model

## Roles

### Payroll Officer

Can:

- read Payroll Bridge configuration;
- create/generate payroll export batches;
- upload/import vendor payroll results;
- validate current import rows;
- inspect payroll reconciliation evidence within allowed companies.

Cannot by role alone:

- modify configuration;
- post a payroll package;
- reconcile/close a payroll batch;
- create correction revisions;
- delete payroll history.

### Payroll Manager

Includes Payroll Officer and additionally can:

- maintain Payroll Bridge configuration;
- post frozen exports to the payroll boundary;
- reconcile batches;
- create governed import correction revisions;
- delete only records still allowed by model history guards.

## Data minimization

Payroll Bridge intentionally consumes:

- internal employee number;
- employee name;
- current company/department/job/grade/position;
- approved time/payroll variables;
- vendor payroll result amounts.

It does not request OneHR sensitive/restricted reader groups and does not consume raw
national identifiers, medical/occupational-health records, dependents, personal document
copies or unrelated PII.

## Company isolation

Every custom model has `company_id` and an explicit allowed-company record rule.
Cross-company references are validated at model level.

## History

Posted exports, validated/reconciled imports and their revision lineage are immutable.
No direct state/evidence field write is accepted outside governed methods.

## Secrets

No password, token, API key, OAuth secret, private key or webhook secret field exists
in Payroll Bridge. External authentication remains the Integration addon's responsibility.
