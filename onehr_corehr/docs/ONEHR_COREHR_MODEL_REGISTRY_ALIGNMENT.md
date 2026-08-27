# onehr_corehr — Master Model Registry Alignment

| # | Model | Classification | ED | OneHR Core HR implementation |
|---:|---|---|---|---|
| 1 | `hr.employee` | INHERIT_ODOO | ED2 | Canonical worker/person; employee number, completeness, lifecycle/history links |
| 2 | `hr.employee.public` | INHERIT_ODOO | ED0 | Directory-safe `onehr_employee_number` only |
| 3 | `hr.version` | INHERIT_ODOO | ED2 | Engagement, grade and approved primary-position target fields |
| 4 | `onehr.employee.dependent` | NEW | ED1 | Family/dependent history |
| 5 | `onehr.employee.emergency.contact` | NEW | ED1 | Effective emergency contacts and primary-contact control |
| 6 | `onehr.employee.identifier` | NEW | ED1 | Restricted, masked, effective-dated enterprise identifier portfolio |
| 7 | `onehr.employee.education` | NEW | ED1 | Multi-row education/qualification history |
| 8 | `onehr.employee.employment.history` | NEW | ED1 | Prior external employment only |
| 9 | `onehr.engagement.type` | NEW | ED1 | Enterprise refinement mapped to native `hr.version.employee_type` |
| 10 | `onehr.work.incident` | NEW | ED3 | Restricted occupational-health/work-incident case |
| 11 | `onehr.medical.assessment` | NEW | ED3 | Restricted medical work-fitness evidence with superseding corrections |
| 12 | `onehr.disability.record` | NEW | ED1 | Restricted minimum-necessary disability/accommodation administration |
| 13 | `res.config.settings` | INHERIT_ODOO | ED0 | Company-keyed masking/retention/governance policy settings |

## Native ownership preserved

- `hr.employee` is the worker master.
- `hr.version` remains the temporal store for Odoo employment facts.
- `hr.employee.public` is never used to expose identifiers/medical/disability/private payload.
- Native identification/passport/work-permit singleton fields remain native; the
  OneHR identifier portfolio is for enterprise identifiers requiring independent
  multiplicity, masking, validity and history.

## Ownership explicitly kept outside Core HR

- Personal HR document versions/expiry/reminders: `onehr_document`.
- Internal assignment/movement history: `onehr_assignment`.
- Branch master/scope: `onehr_multicompany_branch`.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
