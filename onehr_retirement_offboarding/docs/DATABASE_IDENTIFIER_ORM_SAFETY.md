# Database Identifier & ORM Naming Safety — Hard Gate 11

Checked identifiers include:

- `onehr_offboarding`
- `onehr_offboarding_checklist`
- `onehr_clearance_item`
- `onehr_exit_interview`
- `onehr_offboarding_checklist_attachment_rel`

All are below PostgreSQL's 63-byte identifier limit. The attachment Many2many relation is explicitly named to prevent implicit-name drift.

ORM safety controls:

- Odoo 19 `models.Constraint` is used; legacy `_sql_constraints` is absent.
- `UNIQUE(offboarding_id, clearance_item_id)` prevents duplicate generated clearance duties.
- `UNIQUE(offboarding_id)` prevents duplicate governed exit interviews.
- score and SLA CHECK constraints are explicit.
- no generic tutorial table/model survives.
- no duplicate XML IDs are permitted by source acceptance.
- Odoo 19 `<list>` and action `group_ids` conventions are used for window actions and `ir.actions.report`; legacy report `groups_id` is explicitly rejected by source acceptance.
