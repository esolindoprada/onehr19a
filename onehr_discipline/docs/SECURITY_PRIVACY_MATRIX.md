# OneHR Discipline — Security & Privacy Matrix

| Role | Case visibility | Case mutation | Sanction |
|---|---|---|---|
| Discipline Investigator | assigned/owned cases only | assigned investigation/hearing evidence only | linked sanctions read-only |
| Discipline HRBP / Employee Relations | assigned/owned cases | case progression, classification, hearing/decision, sanction creation/submission | create/edit Draft/Rejected; submit approval |
| Discipline Manager | allowed-company cases | management assignment/closure | company scope; Workflow approval only when engine resolves eligibility |
| Discipline Legal / IR | allowed-company cases | legal review, appeal outcome, cancellation, highest domain control | execute approved decision, record downstream execution evidence, guarded deletion |

Privacy/security controls:
- no custom Discipline access for generic `base.group_user`;
- global allowed-company rule on Case and Sanction;
- investigator/HRBP record rules are assignment-scoped;
- Manager/Legal company scope remains intersected by global company rule;
- raw employee relation/number shown only HRBP+ where practical;
- safe employee/department/job display fields use `compute_sudo=True`;
- model ACL/record rules/Python methods are the security boundary;
- client context cannot bypass lifecycle guards;
- incident/classification locks after Hearing;
- sanction definition locks after submission;
- execution/service evidence cannot be entered before execution;
- historical deletion is guarded;
- no business `.sudo()` and no public controller;
- optional Appraisal/PnP/Payroll/Document/Contract services run under normal
  source-module access or narrow explicit authority.

Discipline Legal does not automatically gain Workflow Manager, Security Admin,
Payroll authority, PnP authority, Appraisal HR or Document authority.
