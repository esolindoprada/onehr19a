# onehr_timeoff — Project Identity Preflight

## HARD GATE 0 — PROJECT IDENTITY PREFLIGHT

PROJECT: OneHR NEW

ADDON: `onehr_timeoff`

TARGET PLATFORM: Odoo 19 Community Edition

DELIVERY METHOD: Direct Full Addon Build

AUTHORITATIVE BASELINE:

- OneHR Enterprise Architecture v2 and Master Model Registry v1 as the project authority.
- Approved 25-addon ownership/dependency topology.
- Latest user-provided OneHR workspace export dated 18 Aug 2026.
- Current accepted contracts of `onehr_corehr`, `onehr_security`, and `onehr_workflow_approval`.
- OneHR 25 Addons Specification for the explicit Time Off product scope.
- Oracle HRMS R12.1 blueprint for integrated HR, effective-date/history, security, workforce structure, absence and accrual concepts.
- Odoo 19 CE native HR/resource-calendar behavior where consumed without taking native ownership.

PRESERVATION RULE:

- Canonical employee identity remains `hr.employee`; OneHR Time Off does not create an employee master.
- Time Off owns only the product-baseline leave policy, leave request, and leave allocation domains.
- Workflow Approval owns generic approval route/evidence; Time Off owns leave business state and balance reservation.
- Attendance remains a soft integration for shift/calendar blocking and is not made a reverse hard dependency.
- Payroll remains downstream; Time Off exposes paid/unpaid leave payload but does not own payroll work entries or payroll posting.
- Leave entitlement and approved request evidence must remain historically auditable.

ALLOWED CHANGE:

- Replace the obsolete tutorial scaffold with a complete registry-preserving enterprise implementation.
- Add Odoo 19 compatible constraints, security, workflow integration, accrual/carry-over, analytics, report, tests and professional UI.
- Use the three explicitly approved Time Off core model names only.
- Extend `hr.employee` narrowly for smart navigation/counts without re-owning it.

FORBIDDEN CHANGE:

- No duplicate employee, department, job, grade, branch, payroll or attendance master.
- No new persistent/transient balance, accrual-rule, carry-over-ledger or mass-wizard business model merely for convenience.
- No hard dependency on `onehr_attendance`, payroll, analytics, branch or `hr_holidays`.
- No broad `base.group_user` CRUD.
- No business `sudo()` bypass.
- No state/history weakening to make tests install.
- No sibling-addon modification in this package.

CURRENT VERIFIED STATUS:

- The supplied `onehr_timeoff` baseline is a generic version-0.1/base-only scaffold and is not an enterprise implementation.
- The OneHR product baseline explicitly names three Time Off core models: `onehr.leave.type`, `onehr.leave.request`, `onehr.leave.allocation`.
- Exact ED-number labels for these three rows were not surfaced in the supplied Registry excerpts/search results; this build therefore does **not invent ED codes**. It implements effective-dating/history behavior required by the product/Oracle benchmark while retaining the Registry as architecture authority.
- Source/static acceptance can be executed in this package.
- Windows/Odoo runtime install, upgrade and UAT remain PENDING until executed on the user's real OneHR environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD
RUNTIME_MOVE_FORWARD_RESULT: PENDING
