# onehr_assignment — Full Structural Inventory

## Models

- `models/assignment.py`: `onehr.assignment`; primary/secondary placement, effective dating, approval, capacity, native HR version sync, cron execution.
- `models/costing.py`: `onehr.assignment.cost.allocation`; 100% costing coverage and frozen evidence.
- `models/movement.py`: `onehr.assignment.change.request` + `onehr.assignment.change.line`; persistent batch movement.
- `models/workforce.py`: `onehr.workforce.plan`, `onehr.workforce.plan.line`, `onehr.position.budget`.
- `models/native_extensions.py`: controlled smart/occupancy extensions of `hr.employee` and `onehr.position` only.
- `models/action_helpers.py`, `models/authority_helpers.py`: pure helper modules, no Registry models.

## Security

- 3 explicit roles: Assignment Proposer, Officer, Manager.
- no broad `base.group_user` custom-model ACL.
- proposer direct-report/own-request rules.
- allowed-company partition for operational/planning models.
- field-level restriction for private employee relations.

## Data

- governed Assignment and Movement Request sequences.
- daily effective-date scheduler; no business sudo bypass.

## UI

- 7 custom models: explicit List + Form + Search.
- Assignment: Calendar + Pivot + Graph.
- Workforce Plan and Position Budget: Pivot + Graph.
- native employee/position smart-button integration.
- Assignment History QWeb PDF restricted to Assignment Officer+.

## Tests and acceptance

- 26 post-install runtime test methods.
- static source acceptance tool.
- Windows runtime checklist.

## Legacy scaffold removed

No tutorial controller, generic placeholder model, demo records, `views/views.xml`, `views/templates.xml`, version 0.1 manifest or generic `base.group_user` full CRUD remains.
