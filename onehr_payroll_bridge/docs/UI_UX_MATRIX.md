# onehr_payroll_bridge — UI/UX Matrix

| Model | List | Form | Search | Enterprise interaction |
|---|:---:|:---:|:---:|---|
| `onehr.payroll.bridge.config` | YES | YES | YES | Smart buttons to Exports/Imports/Latest, body Validate Mapping + Prepare Previous Month, JSON mapping notebooks, scheduler policy, recent-export O2M row buttons |
| `onehr.payroll.export` | YES | YES | YES | Statusbar, Generate/Post/Reconcile/Cancel header actions, Configuration/Result smart buttons, Download/Review/Validate/Costing body actions, vendor CSV import, import O2M row actions, frozen source/config evidence, Calendar/Pivot/Graph, chatter, QWeb reconciliation report |
| `onehr.payroll.import` | YES | YES | YES | Statusbar, Validate/Correction header actions, Export/Employee smart buttons, body navigation, revision-history O2M, validation/raw-evidence tabs, Pivot/Graph, chatter |

## UX quality rules

- Header buttons represent lifecycle transitions only.
- Smart buttons navigate related evidence.
- Body buttons perform operational work without overloading the header.
- One2many row buttons reduce repeated form navigation.
- State badges/decorations make lists decision-oriented.
- Search views expose business identifiers, status, date and group-by.
- Payroll amounts and raw vendor evidence remain inside Payroll groups.
- UI visibility never substitutes for model security.
