# OneHR Integrations API — Endpoint / Ownership Matrix

| Endpoint | Scope | Domain owner / service |
|---|---|---|
| `GET /onehr/api/v1/health` | `system.health` | Integration Hub capability check |
| `GET /onehr/api/v1/employees` | `corehr.employee.read` | native/CoreHR `hr.employee` under service-user ACL |
| `POST /onehr/api/v1/attendance` | `attendance.write` | `hr.attendance.onehr_ingest_interval()` |
| `POST /onehr/api/v1/recruitment/applicants` | `recruitment.applicant.write` | Recruitment/native `hr.applicant.create()` |
| `POST /onehr/api/v1/timeoff/requests` | `timeoff.request.write` | `onehr.leave.request` + governed submit action |
| `POST /onehr/api/v1/approvals/events` | `workflow.approval.decide` | `onehr.approval.request` actions |
| `POST /onehr/api/v1/documents/esign/status` | `document.esign.write` | `onehr.esign.transaction.apply_provider_status()` |
| `POST /onehr/api/v1/learning/results` | `learning.result.write` | `onehr.learning.enrollment.onehr_ingest_external_result()` |
| `POST /onehr/api/v1/learning/enrollments` | `learning.enrollment.write` | `onehr.learning.enrollment.onehr_external_enroll()` |
| `POST /onehr/api/v1/appraisals/ratings` | `appraisal.rating.write` | `onehr.appraisal.form.onehr_ingest_external_rating()` |
| `POST /onehr/api/v1/career/assessments` | `career.assessment.write` | `onehr.talent.pool.onehr_ingest_talent_assessment()` |
| `GET /onehr/api/v1/payroll/exports/<id>` | `payroll.export.read` | `onehr.payroll.export.onehr_payroll_export_payload()` |
| `POST /onehr/api/v1/payroll/results` | `payroll.result.write` | `onehr.payroll.import.onehr_ingest_payroll_result()` |
| `GET /onehr/api/v1/policies/acknowledgements` | `pnp.ack.read` | `onehr.policy.onehr_pnp_ack_status()` |
| `POST /onehr/api/v1/policies/evidence` | `pnp.evidence.write` | `onehr.policy.onehr_pnp_submit_evidence()` |
| `GET /onehr/api/v1/sops/acknowledgements` | `sop.ack.read` | `onehr.sop.onehr_sop_ack_status()` |
| `GET /onehr/api/v1/job-descriptions/<reference>` | `jd.read` | `onehr.jd.onehr_jd_api_payload()` |
| `GET /onehr/api/v1/portal/my-hr` | `portal.myhr.read` | `onehr.portal.request.onehr_my_hr_dashboard_payload()` |
| `GET /onehr/api/openapi.json` | `system.docs` | Integrations API OpenAPI document |

All mutating REST calls require `X-Request-ID`; when the key requires HMAC they also require
`X-Timestamp` and `X-Signature`. Absence of an optional owner addon is a controlled 501 capability
response, never permission for this addon to duplicate the owner model.
