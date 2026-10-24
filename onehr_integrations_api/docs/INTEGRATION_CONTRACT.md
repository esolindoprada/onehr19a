# OneHR Integrations API — Integration Contract

`onehr_integrations_api` owns transport/authentication only: REST v1, API key/scope,
HMAC/replay/rate controls, webhooks, retry/dead-letter and technical audit.

Business-domain ownership remains soft and runtime-discovered. Accepted adapters used when the
owning addon is installed include:

- Attendance: `hr.attendance.onehr_ingest_interval(payload)`.
- Appraisal: `onehr.appraisal.form.onehr_ingest_external_rating(payload)`.
- Learning: `onehr.learning.enrollment.onehr_ingest_external_result(payload)` and `onehr_external_enroll(payload)`.
- Career/Succession: `onehr.talent.pool.onehr_ingest_talent_assessment(payload)`.
- Payroll Bridge: `onehr.payroll.export.onehr_payroll_export_payload()` and `onehr.payroll.import.onehr_ingest_payroll_result(payload)`.
- PnP: `onehr.policy.onehr_pnp_ack_status(...)` and `onehr_pnp_submit_evidence(payload)`.
- SOP: `onehr.sop.onehr_sop_ack_status(...)`.
- Job Description: `onehr.jd.onehr_jd_api_payload(reference)`.
- Portal: `onehr.portal.request.onehr_my_hr_dashboard_payload()`.
- Document e-Sign: `onehr.esign.transaction.apply_provider_status(...)`.
- Workflow Approval: normal governed `action_approve()` / `action_reject()`.
- Time Off: normal `onehr.leave.request` creation + `action_submit_for_approval()` when available.
- Recruitment: normal Odoo `hr.applicant` creation under Recruitment/HR ACLs.

If an owner addon/model/service is absent, the API returns capability-unavailable rather than
inventing replacement business logic. No reverse hard dependency is created.
