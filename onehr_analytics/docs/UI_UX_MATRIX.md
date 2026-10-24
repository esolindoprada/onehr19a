# OneHR Analytics — UI / UX Matrix

| Model | List | Form | Search | Kanban | Pivot | Graph | Statusbar | Smart buttons | Body buttons | Row buttons |
|---|---|---|---|---|---|---|---|---|---|---|
| `onehr.analytics.tile` | Yes | Yes | Yes | Yes | N/A | N/A | Draft/Active/Paused/Retired | Snapshots, Breaches | Favorite, Test Provider, Open Source, Export CSV | Snapshot, Favorite; snapshot evidence Open/Source |
| `onehr.kpi.snapshot` | Yes | Yes | Yes | N/A | Yes | Yes | KPI outcome | Tile | Source, Archive/Restore | N/A |

## UX decisions
The tile Kanban is the executive dashboard surface because it is native CE, configurable,
security-aware and does not require a fabricated client-side dashboard framework. KPI snapshots
use Pivot/Graph for trend exploration. Snapshot form is immutable evidence rather than an edit
workspace.

Buttons never replace server-side authorization. Configuration pages are Manager-only while
Analysts can read dashboard/evidence and maintain only their own favorite membership through a
server-enforced constrained write path.
