
# OneHR Portal Self-Service — Upstream Contract and Scope Audit

AUTHORITATIVE_WORKSPACE: `onehr19a(20260826-124033).md`  
WORKSPACE_SHA256: `25f243eeed0da1bbc23739e7a48ede1b0255c284216c122f077beec09f91d351`

The latest supplied OneHR workspace was inspected before implementation so Portal could call
existing accepted model services rather than invent duplicate integration architecture.

Verified upstream/downstream contract points used by this build:
- CoreHR: canonical `hr.employee`, OneHR employee number, grade/position extensions.
- Time Off: `onehr.leave.type` + `onehr.leave.request.action_submit_for_approval()`.
- Learning: `onehr.learning.enrollment.onehr_external_enroll(payload)` and participant portal payload.
- Appraisal: `onehr.appraisal.form.onehr_employee_appraisal_payload(employee)`.
- Document: `onehr.document`, `onehr.document.version`, `onehr.document.category`.
- Payroll Bridge: employee-safe portal payroll payload on current import revisions.
- Job Description: `onehr_jd_portal_payload(...)`.
- Policies & Procedures: employee acknowledgement/status service.
- SOP: employee acknowledgement/status service.
- Career/Succession: employee career payload service.

No sibling OneHR source is modified by this package.
No new hard dependency is added merely to make optional cards or hand-offs available.

SCOPE_AUDIT_RESULT: PASS_SOURCE

