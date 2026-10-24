# OneHR Integrations API — Database Identifier & ORM Naming Safety

Hard Gate 11 is explicit for this addon.

- Custom models use short stable names; default table names remain under PostgreSQL 63-byte limits.
- Explicit Many2many relation: `onehr_api_key_scope_rel`.
- Queue/API constraint attribute names are short and deterministic.
- XML IDs are local, unique and human-readable.
- Odoo 19 action visibility uses `ir.actions.act_window.group_ids`, never invalid `groups_id`.
- Odoo 19 user membership uses native `res.users.group_ids`.
- `models.Constraint` is used; legacy `_sql_constraints` is forbidden.
- No custom field ends in ambiguous `_ids_id`; no auto-generated oversized M2M relation is relied upon.
- `tools/source_acceptance.py` checks model/relation identifier shape and length, duplicate XML IDs,
  Odoo 19 action field naming and forbidden legacy ORM/view patterns.
