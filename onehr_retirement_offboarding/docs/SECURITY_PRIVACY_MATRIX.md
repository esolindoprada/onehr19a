# Security & Privacy Matrix

| Role | Purpose | Deliberate limits |
|---|---|---|
| Offboarding Task Owner | Work assigned clearance tasks and see participating case context | No case create/write, no exit-interview CRUD, no catalogue config, no settlement/access governance |
| Offboarding Officer | Create/co-ordinate company cases, tasks and interviews | No approval governance, no catalogue mutation, no user revocation authority |
| Offboarding Manager | Submit approval, waive/reopen, settlement/contract orchestration, complete/close | Does not imply Contract Manager, Payroll, HR Manager or System Administrator |
| Offboarding Administrator | Catalogue/admin/evidence authority | Still does not imply `base.group_system`; user revocation requires both roles |

Global company rules apply to all four persistent models. Task-owner record rules are participation-based; officer visibility ORs the restrictive participation rule while the global company rule remains non-bypassable.

Sensitive evidence uses field groups. Direct writes to case state, access status/timestamps, final-benefit state, contract disposition and completion/closure evidence are blocked. Checklist/interview state and actor timestamps are action-only. `res.users` offboarding evidence is action-only. No business `sudo()` is used by the addon models.
