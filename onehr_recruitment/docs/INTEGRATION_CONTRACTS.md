# OneHR Recruitment — Cross-Addon Integration Contracts

## onehr_base

Consumes approved base-owned `onehr.position`, generic lifecycle/checklist models and HIRE lifecycle event. Recruitment does not re-own them.

## onehr_corehr

Core employee profile stays with CoreHR/Odoo canonical `hr.employee`. Recruitment calls Odoo's native applicant-to-employee conversion and never creates a duplicate employee master.

## onehr_security

Recruitment privileges are layered on top of OneHR security. No broad custom-model access is granted to ordinary internal users.

## onehr_workflow_approval

Requisition and offer inherit `onehr.mixin.approvable`. Approval engine owns routing/decision evidence; recruitment owns source state and execution. The approval payload contains only structured non-executable facts.

## onehr_document — soft

When installed, an approved offer can open `wizard.document.generate` using an active `onehr.document.template` with code `RECRUITMENT_OFFER`. Recruitment does not own document binaries, e-sign provider secrets or document-retention history.

## onehr_multicompany_branch — architecture-compatible, no hard dependency

Company remains the required legal/security partition here. Branch-specific recruitment scope may later be added only through the branch owner's approved extension contract, without creating a reverse dependency.

## future hire-domain owners

`_onehr_post_hire_orchestration(employee)` is intentionally narrow. Employment Contract, Assignment, Attendance/access provisioning, Payroll and other owners may extend it when their addons are implemented. This addon does not create placeholder downstream records.

## onehr_integrations_api — soft/future

Job-board imports, career-site webhooks, external assessment providers and outbound recruitment API endpoints belong to the integrations adapter. Recruitment exposes business records/hooks; it does not store integration credentials or implement public controllers in this build.
