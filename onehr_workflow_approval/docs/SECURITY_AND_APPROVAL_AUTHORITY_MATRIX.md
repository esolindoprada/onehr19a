
# OneHR Workflow Approval — Security & Approval Authority Matrix

| Group | Request visibility | Decision authority | Delegation | Rule/step config | Evidence/KPI |
|---|---|---|---|---|---|
| Approval User | requester/follower/participant in allowed company | none | none | read | participating evidence |
| Approver | participant/current | only if server resolves current authority | own delegations | read | participating evidence |
| Workflow Manager | allowed-company scope | only through resolved approval action | company-scope manage/reassign | create/write/version workflow | company reporting |
| Workflow Administrator | allowed-company scope | correction evidence + normal resolved approval | company-scope | highest workflow config authority | company reporting |

Separation rules:
- Approval User implies only `onehr_security.group_onehr_security_user` so role
  catalogue and own role assignment context are readable; it does NOT imply Security Manager/Admin.
- Workflow Administrator does NOT imply OneHR Security Administrator.
- Approval groups do NOT imply restricted/sensitive HR groups.
- Approval engine never sudo-writes or sudo-executes source business records.
- Role-assignment/delegation enumeration uses narrow routing-only sudo because a
  requester must not receive broad ACL to enumerate other users' security assignments.
  Only eligible user IDs cross that internal boundary.
- Automatic decision and SLA evidence use narrow system/evidence sudo after rule/
  action authorization; this does not authorize source business state.
- Opening Source Record still depends on independent source-model read access.
