# Contract Termination Boundary

The current OneHR Employment Contract implementation already owns legal contract termination, Workflow Approval evidence and the base `TERMINATION` lifecycle checklist. It explicitly leaves broader employee exit orchestration to Retirement/Offboarding.

Accordingly this addon:

1. owns the broad exit case and cross-functional clearance orchestration;
2. does **not** inherit or replace `onehr.contract`;
3. resolves `onehr.contract` only when installed;
4. uses normal source-model ACL/security and never `sudo()` to force termination;
5. treats Employment Contract approval/execution as a closure gate;
6. permits `not_applicable` only with documented manager exception evidence;
7. does not archive `hr.employee` automatically when a contract terminates.

Employee archival is a separate explicit action after Closed state and requires both Offboarding Administrator and HR Manager authority.
