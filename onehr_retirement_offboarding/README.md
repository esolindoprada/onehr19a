# OneHR Retirement & Offboarding

Enterprise retirement, resignation and exit orchestration for **OneHR NEW on Odoo 19 Community Edition**.

This Direct Full Addon Build replaces the supplied generic tutorial scaffold. The addon owns exactly four persistent business models:

- `onehr.offboarding` — governed exit case and orchestration state.
- `onehr.offboarding.checklist` — generated cross-functional clearance task/evidence.
- `onehr.clearance.item` — reusable clearance-item catalogue/template.
- `onehr.exit.interview` — governed exit-interview evidence.

It extends `hr.employee` only with derived offboarding indicators/navigation and extends `res.users` only with controlled access-revocation evidence. It does **not** create a parallel employee, employment contract, payroll, document, branch, portal, analytics or API master.

## Hard dependencies

- `onehr_corehr`
- `onehr_security`
- `onehr_workflow_approval`

Employment Contract, Document, Payroll Bridge, Portal Self Service, Analytics, Integrations API and Branch remain **soft/downstream integration contracts**. Their own ACLs and business authority remain authoritative.

## Main workflow

Requested → Approval → In Progress → Completed → Closed, with governed Rejected and Cancelled branches.

Closure is blocked until mandatory clearance tasks, exit-interview disposition, access-revocation disposition, final-benefit disposition and legal contract-termination disposition are complete or explicitly marked not applicable.

## Installation

Replace the complete old `onehr_retirement_offboarding` folder. Do not merge this package with the tutorial scaffold. Restart Odoo, Update Apps List, then install **OneHR Retirement & Offboarding**.

Source/static acceptance is not runtime acceptance. Windows Odoo 19 install, security and workflow acceptance remain mandatory before move-forward.
