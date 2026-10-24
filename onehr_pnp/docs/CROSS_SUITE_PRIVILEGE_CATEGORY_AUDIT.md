
# OneHR Cross-Suite Privilege Category Dynamic-XML Audit

AUTHORITATIVE_COMPOSITE: `onehr19a(20260910-032255).md`  
AUDIT_DATE: `2026-09-10`  
PRIVILEGE_BEARING_CATEGORY_COUNT: `24`  
UNSAFE_BEFORE_BOUNDED_OVERLAY: `2`  
UNSAFE_AFTER_BOUNDED_OVERLAY: `0`

The audit decodes XML entities first, then applies the Odoo 19 dynamic Users/Access Rights render-safety contract to `ir.module.category.name`. Only privilege-bearing OneHR categories are in scope.

| Module | Category XML ID | Baseline stored name | Repaired stored name | Before | After |
|---|---|---|---|---|---|
| `onehr_analytics` | `module_category_onehr_analytics` | OneHR Analytics | OneHR Analytics | SAFE | SAFE |
| `onehr_appraisal` | `module_category_onehr_appraisal` | OneHR Appraisal | OneHR Appraisal | SAFE | SAFE |
| `onehr_assignment` | `module_category_onehr_assignment` | OneHR Assignment | OneHR Assignment | SAFE | SAFE |
| `onehr_attendance` | `module_category_onehr_attendance` | OneHR Attendance | OneHR Attendance | SAFE | SAFE |
| `onehr_career_succession` | `module_category_onehr_career_succession` | OneHR Career & Succession | OneHR Career and Succession | UNSAFE | SAFE |
| `onehr_corehr` | `module_category_onehr_corehr` | OneHR Core HR | OneHR Core HR | SAFE | SAFE |
| `onehr_demo` | `module_category_onehr_demo` | OneHR Enterprise Demo | OneHR Enterprise Demo | SAFE | SAFE |
| `onehr_discipline` | `module_category_onehr_discipline` | OneHR Employee Relations — Discipline | OneHR Employee Relations — Discipline | SAFE | SAFE |
| `onehr_document` | `module_category_onehr_document` | OneHR Document | OneHR Document | SAFE | SAFE |
| `onehr_employment_contract` | `module_category_onehr_contract` | OneHR Employment Contract | OneHR Employment Contract | SAFE | SAFE |
| `onehr_integrations_api` | `module_category_onehr_integrations_api` | OneHR Integration Hub | OneHR Integration Hub | SAFE | SAFE |
| `onehr_job_description` | `module_category_onehr_job_description` | OneHR Job Description | OneHR Job Description | SAFE | SAFE |
| `onehr_learning` | `module_category_onehr_learning` | OneHR Learning | OneHR Learning | SAFE | SAFE |
| `onehr_mobile_kiosk` | `module_category_onehr_mobile_kiosk` | OneHR Mobile Kiosk | OneHR Mobile Kiosk | SAFE | SAFE |
| `onehr_multicompany_branch` | `module_category_onehr_branch` | OneHR Branch | OneHR Branch | SAFE | SAFE |
| `onehr_payroll_bridge` | `module_category_onehr_payroll_bridge` | OneHR Payroll Bridge | OneHR Payroll Bridge | SAFE | SAFE |
| `onehr_pnp` | `module_category_onehr_pnp` | OneHR Policies & Procedures | OneHR Policies and Procedures | UNSAFE | SAFE |
| `onehr_portal_self_service` | `module_category_onehr_portal` | OneHR Portal Self-Service | OneHR Portal Self-Service | SAFE | SAFE |
| `onehr_recruitment` | `module_category_onehr_recruitment` | OneHR Recruitment | OneHR Recruitment | SAFE | SAFE |
| `onehr_retirement_offboarding` | `module_category_onehr_offboarding` | OneHR Offboarding | OneHR Offboarding | SAFE | SAFE |
| `onehr_security` | `module_category_onehr_security` | OneHR Security | OneHR Security | SAFE | SAFE |
| `onehr_sop` | `module_category_onehr_sop` | OneHR SOP | OneHR SOP | SAFE | SAFE |
| `onehr_timeoff` | `module_category_onehr_timeoff` | OneHR Time Off | OneHR Time Off | SAFE | SAFE |
| `onehr_workflow_approval` | `module_category_onehr_approval` | OneHR Approvals | OneHR Approvals | SAFE | SAFE |

`CROSS_SUITE_DYNAMIC_CATEGORY_CLOSURE: PASS_FOR_RUNTIME`  
`WINDOWS_BROWSER_RUNTIME: PENDING`

