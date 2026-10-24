# OneHR Analytics — Database Identifier & ORM Naming Safety

HARD GATE 11 requires PostgreSQL/Odoo identifier safety before runtime.

## Model table identifiers
- `onehr.analytics.tile` → `onehr_analytics_tile` (20 bytes)
- `onehr.kpi.snapshot` → `onehr_kpi_snapshot` (18 bytes)

Both are below PostgreSQL's 63-byte identifier limit.

## Explicit Many2many relations
- `onehr_analytics_tile_alert_user_rel` (35 bytes)
- `onehr_analytics_tile_favorite_user_rel` (38 bytes)

Both relation names are explicit, human-readable and below 63 bytes. Columns are `tile_id` and
`user_id`.

## Constraints
- Tile company/code uniqueness uses Odoo 19 `models.Constraint`.
- Snapshot tile/period uniqueness uses Odoo 19 `models.Constraint`.
- Legacy `_sql_constraints` is forbidden.

## XML / ORM naming checks
- duplicate XML IDs are a hard failure;
- every manifest data file must exist;
- persistent models have stable `_name` values;
- action records use Odoo 19 `group_ids`, never obsolete/invalid `groups_id`;
- no implicit long Many2many relation identifier is allowed;
- no tutorial `onehr_analytics.onehr_analytics` model remains.

`HARD_GATE_11_SOURCE_RESULT: PASS_FOR_RUNTIME`
