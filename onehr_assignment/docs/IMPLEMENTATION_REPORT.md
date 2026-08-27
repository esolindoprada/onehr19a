# OneHR Assignment — Direct Full Implementation Report

The uploaded Assignment addon was a generic tutorial scaffold. This build replaces that scaffold with the Registry-approved enterprise Assignment domain rather than polishing a placeholder model.

The implementation treats Assignment as the authoritative internal placement/movement ledger. It supports primary/secondary placement, direct reporting, FTE, effective dating, movement type, predecessor/successor history, governed approval, due-date execution and position capacity. Primary activation uses Odoo native employee versioning and writes the approved placement to the returned `hr.version`; secondary assignments remain non-destructive overlays.

Mass movement uses the approved persistent ED3 `onehr.assignment.change.request` and `onehr.assignment.change.line`, not an invented transient wizard. This gives approval/execution evidence and a durable per-employee line trail.

Assignment-level costing is effective-dated and percentage-based. It deliberately uses neutral external dimension codes so Payroll/Finance can map later without hard dependency or accounting ownership leakage.

Workforce planning is versioned and approval-ready. Plan lines materialize effective Position Budgets, which override Base Position headcount/FTE capacity during their active intervals. Capacity validation also checks the first day after a budget expires so a fallback to lower Base capacity cannot silently create an over-capacity placement.

Security is model-level: proposer is direct-report/own-request limited, officer operates assignment data within allowed companies, manager executes movement and workforce controls. Private employee relation fields remain restricted; safe stored names support proposer UX without granting broad private employee access.

SOURCE_DIRECT_FULL_BUILD: BUILT
SOURCE_ACCEPTANCE: EXECUTED_BY_PACKAGE_TOOL
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: NO
