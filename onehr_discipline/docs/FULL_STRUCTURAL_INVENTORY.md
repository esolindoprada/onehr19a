
# OneHR Discipline — Full Structural Inventory

## Persistent business models — exactly two

### `onehr.discipline.case`
Owns the confidential employee-relations case:
- immutable case/employee/company identity and standardized reference;
- incident report, chronology, witnesses and attachment evidence;
- policy/rule soft reference;
- violation category, severity and configurable weight;
- assigned owner/investigator/HRBP/Legal roles;
- authoritative case pipeline Reported → Under Investigation → Hearing →
  Decision → Closed, plus controlled Cancelled exception;
- investigation questions/findings/evidence assessment/recommendation;
- hearing schedule/attendees/employee statement/witness statement/minutes;
- final disposition/decision/rationale;
- embedded appeal submission/review/outcome;
- SLA dates, overdue status, activities and daily reminder cron;
- repeat-offense indicator and resolution lead time;
- soft Appraisal evidence snapshot;
- One2many governed sanctions;
- retention date and audit history.

### `onehr.discipline.sanction`
Owns disciplinary decision approval/execution:
- standardized sanction reference;
- warning/SP-1/SP-2/SP-3/suspension/probation/payroll deduction/
  last-chance/termination/no-action/other types;
- decision/effective/expiry/follow-up dates;
- decision basis, legal basis, terms and management expectations;
- probation/last-chance conditions;
- discipline-owned payroll deduction request amount/period, while Payroll Bridge
  remains owner of actual payroll execution;
- contract review recommendation/reference without mutating contract ownership;
- OneHR Workflow Approval source contract;
- Draft → Approval → Approved → Executed, with Rejected/Cancelled exceptions;
- employee service/receipt and execution evidence;
- downstream payroll callback evidence.

## Transient configuration extension
`res.config.settings`:
- investigation SLA;
- hearing SLA;
- decision SLA;
- appeal SLA;
- retention years;
- Minor/Moderate/Serious/Critical classification weights.

## Legacy scaffold concept preservation map
The old description named eight models. The authoritative suite registry later
reduced the Discipline core contract to two. Functional intent is preserved as:

| Legacy concept | Approved implementation |
|---|---|
| Discipline policy | `policy_reference` on Case; PnP remains separate owner |
| Violation catalog | structured category/severity/code/weight on Case + Settings |
| Case | `onehr.discipline.case` |
| Case stage | Case `state` + governed action methods + SLA fields |
| Investigation | structured section on Case |
| Hearing | structured section on Case |
| Sanction | `onehr.discipline.sanction` |
| Appeal | structured section on Case |

This is registry alignment, not feature deletion.

## Upstream/downstream ownership not duplicated
- Employee: canonical `hr.employee` / OneHR CoreHR.
- Approval: OneHR Workflow Approval.
- PnP/SOP policy records: their owning addons.
- Appraisal evidence: OneHR Appraisal.
- Document archive: OneHR Document.
- Payroll execution: Payroll Bridge/payroll.
- Employment contract lifecycle: Employment Contract.
- Branch master: Multi-company Branch.
- Dashboard/API transport: Analytics / Integrations API.

