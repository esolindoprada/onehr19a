
# OneHR Assignment — Master Model Registry Alignment

| # | Model | Classification | ED | Ownership / implementation |
|---:|---|---|---|---|
| 1 | `onehr.assignment` | NEW persistent | ED2 | Effective-dated primary/secondary placement, reporting, FTE, occupancy consumption, history and native HR sync |
| 2 | `onehr.assignment.change.request` | NEW persistent | ED3 | Governed single/batch movement request and approval/execution evidence |
| 3 | `onehr.assignment.change.line` | NEW persistent | ED3 | Per-employee source→target movement line and generated-successor evidence |
| 4 | `onehr.assignment.cost.allocation` | NEW persistent | ED1 | Effective assignment-level percentage costing dimensions, adapter-neutral |
| 5 | `onehr.workforce.plan` | NEW persistent | ED2 | Versioned workforce plan/scenario with approval and plan activation |
| 6 | `onehr.workforce.plan.line` | NEW persistent | ED2 | Position-level planned headcount/FTE/cost and budget materialization |
| 7 | `onehr.position.budget` | NEW persistent | ED1 | Effective position headcount/FTE/budget authorization and capacity control |
| 8 | `hr.version` | SHARED ODOO REFERENCE | ED2 | Canonical native employment-version store synchronized by approved primary assignment |

## Native ownership preserved

- `hr.employee`: Odoo worker master.
- `hr.version`: Odoo employment/versioned facts.
- `hr.department`, `hr.job`, `hr.work.location`: Odoo native masters.
- `onehr.position` and `onehr.grade`: OneHR Base masters.

## Explicitly outside Assignment ownership

- legal contract lifecycle: `onehr_employment_contract`;
- branch master/scope: `onehr_multicompany_branch`;
- payroll posting/accounting/analytic masters: downstream payroll/accounting adapters;
- recruitment pipeline/hiring: `onehr_recruitment`;
- user/role entitlement: `onehr_security`.

## Dependency contract

Hard dependencies are exactly:

- `onehr_base`
- `onehr_corehr`
- `onehr_security`
- `onehr_workflow_approval`

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
