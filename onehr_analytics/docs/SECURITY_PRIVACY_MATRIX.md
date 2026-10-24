# OneHR Analytics — Security & Privacy Matrix

| Capability | Analyst | Manager | Administrator |
|---|---:|---:|---:|
| Read KPI tiles | Yes | Yes | Yes |
| Favorite/unfavorite own tile | Yes | Yes | Yes |
| Create/configure KPI tiles | No | Yes | Yes |
| Activate/pause/resume/retire | No | Yes | Yes |
| Generate/test provider | No | Yes | Yes |
| Export snapshot CSV | No | Yes | Yes |
| Read snapshot evidence | Yes | Yes | Yes |
| Archive snapshot | No | Yes | Yes |
| Restore archived snapshot | No | No | Yes |
| Delete started KPI/snapshot evidence | No | No | No |

## Enforcement
- Groups use Odoo 19 `res.groups.privilege`.
- Analyst implies only the OneHR security user, not HR Officer/Manager or System Administrator.
- Global record rules restrict Tile and Snapshot by `company_ids`.
- Provider engine reuses the caller's normal source-model ACL/record rules.
- No business `sudo()` exists in the addon.
- No public HTTP controller exists.
- Raw source rows are not copied into KPI snapshots; only aggregate values, record count,
  sanitized provider metadata and drill-through domain are stored.
- Branch scope is a soft code reference and fails closed if source branch isolation cannot be
  proven.
- Snapshot evidence is immutable and deletion is blocked.
