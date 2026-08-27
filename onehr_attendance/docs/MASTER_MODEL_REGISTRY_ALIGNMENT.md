# OneHR Attendance — Master Model Registry Alignment

| # | Registry / runtime model | Classification | ED | Implementation contract |
|---:|---|---|---|---|
| 1 | `hr.attendance` | INHERIT_ODOO | ED3 | Canonical check-in/out transaction; OneHR adds governed processing, shift resolution, reconciliation trace and exception evidence. |
| 2 | `hr.attendance.overtime` → **Odoo 19 runtime `hr.attendance.overtime.line`** | INHERIT_ODOO | ED3 | Registry concept mapped to the actual Odoo 19 model; no duplicate model is created. OneHR adds payroll/policy export metadata only. |
| 3 | `hr.attendance.overtime.rule` | INHERIT_ODOO | ED1 | Native overtime rule remains calculation owner; OneHR adds stable policy/payroll codes and notes. |
| 4 | `hr.attendance.overtime.ruleset` | INHERIT_ODOO | ED1 | Native ruleset remains policy/calculation owner; OneHR adds effective policy-reference metadata. |
| 5 | `onehr.shift` | NEW persistent | ED1 | Effective shift definition with work calendar, location/position scope, grace, rounding, geofence and working days. |
| 6 | `onehr.shift.pattern` | NEW persistent | ED2 | Versioned rotation pattern using bounded human-readable cycle tokens without inventing an unregistered line model. |
| 7 | `onehr.shift.assignment` | NEW persistent | ED1 | Effective employee schedule linked to one direct shift or one rotation pattern; optional soft enterprise-assignment reference. |
| 8 | `onehr.attendance.exception` | NEW persistent | ED3 | Immutable detected exception evidence with controlled review/resolution/waiver. |
| 9 | `onehr.attendance.reconciliation` | NEW persistent | ED3 | Governed candidate batch from device/API/import/manual sources before canonical posting. |
| 10 | `onehr.attendance.import.batch` | NEW persistent | ED3 | Immutable import staging/evidence using structured JSON rows; no unregistered staging-line model. |

## Explicitly rejected duplicate ownership

The following are intentionally **not** created:

- `onehr.attendance`
- `onehr.employee`
- `onehr.overtime`
- a parallel attendance device master
- a parallel payroll entry model
- a parallel time-off or learning record
- a transient or persistent pattern-line model absent from the Registry

## Dependency contract

Hard dependencies are exactly:

- `onehr_corehr`
- `onehr_security`
- `hr_attendance`

Soft integration contracts are documented in `INTEGRATION_CONTRACTS.md` and must not be converted to reverse hard dependencies.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS_BY_DESIGN
RUNTIME_REGISTRY_RESULT: PENDING
