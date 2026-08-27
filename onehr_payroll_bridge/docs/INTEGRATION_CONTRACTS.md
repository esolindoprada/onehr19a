# onehr_payroll_bridge — Integration Contracts

## onehr_corehr — hard dependency

- `hr.employee` remains the canonical worker.
- Payroll Bridge consumes the safe internal employee number and current work-structure
  facade (company, department, job, grade, primary position).
- Payroll roles imply `hr.group_hr_user` for required employee/work-structure access
  but deliberately do not imply Core HR Sensitive Data Reader or Restricted Data Reader.
- Payroll Bridge does not read raw identifiers, medical/occupational-health records,
  dependents or other unnecessary PII.

## onehr_security — hard dependency

- Payroll Officer and Payroll Manager are explicit privilege groups.
- company isolation is enforced by ACL/rules and business methods, not button visibility.
- audit/chatter evidence is inherited from the OneHR audit foundation.
- no broad internal-user payroll access and no `sudo()` business bypass.

## Odoo `hr_work_entry` — soft runtime consumer

When Odoo's native `hr.work.entry` model is installed, Payroll Bridge reads existing
Draft/Validated work entries for the payroll period (date, duration, type code/external
code and state). It does **not** generate, validate, cancel or rewrite work entries and
does not add `hr_work_entry` as a hard dependency.

## onehr_attendance — soft runtime consumer

When installed, Payroll Bridge reads Posted/approved attendance and native overtime
metadata owned by Attendance:

- attendance count;
- worked/rounded hours;
- lateness/early-leave minutes;
- approved/export-ready overtime hours and payroll-code snapshots.

No Attendance source row is modified and no reverse hard dependency is introduced.

## onehr_timeoff — soft runtime consumer

When installed, approved/done leave is consumed through the Time Off payroll payload
contract and overlap is bounded to the payroll period. Payroll Bridge derives paid/unpaid
period days for exchange evidence; it never owns leave entitlement or approval.

## onehr_assignment — optional downstream costing contract

No hard dependency is introduced. If the accepted Assignment costing model exists,
effective `onehr.assignment.cost.allocation` dimensions are serialized into the employee
source package. Assignment remains owner of percentages/effective dates; Payroll Bridge
only transports the evidence.

## onehr_discipline — soft future extension

The current uploaded Discipline addon does not expose an accepted enterprise payroll
deduction schema. This build does not guess one. Optional domains may contribute
variables through a narrow employee-side `onehr_payroll_variable_payload(period_start,
period_end)` hook after their own ownership is approved.

## onehr_payroll_l10n_id — downstream extension

Payroll localization depends on Payroll Bridge. It may extend the export-row hook and
validation/adapter services with PPh21/BPJS/THR parameters. Payroll Bridge itself owns
no Indonesian tax/social-security formula.

## onehr_integrations_api — downstream transport owner

Payroll Bridge exposes normal model services:

- `onehr.payroll.export.onehr_payroll_export_payload()`
- `onehr.payroll.import.onehr_ingest_payroll_result(payload)`

Public routes, authentication, API keys, webhooks, throttling and retries belong to
`onehr_integrations_api`. Payroll Bridge stores no API secret.

## external/OCA payroll adapter boundary

`provider_mode` supports CSV/manual plus adapter modes. CSV/manual is functional in
this addon. API/OCA modes intentionally require an installed adapter to override the
transport hook; Payroll Bridge refuses to pretend it owns an unavailable payroll engine.

## accounting / analytics

Reconciliation creates a department costing payload and QWeb/Pivot/Graph analysis.
Actual GL/analytic posting is outside this addon's ownership and must be performed by an
approved accounting adapter.
