# Model Registry Alignment

The supplied product contract explicitly names these four core models and the Direct Full Build preserves them:

| Model | Build treatment | Ownership |
|---|---|---|
| `onehr.offboarding` | persistent | Retirement & Offboarding |
| `onehr.offboarding.checklist` | persistent | Retirement & Offboarding |
| `onehr.clearance.item` | persistent | Retirement & Offboarding |
| `onehr.exit.interview` | persistent | Retirement & Offboarding |
| `hr.employee` | Odoo-native extension only | Odoo/Core HR |
| `res.users` | Odoo-native extension only | Odoo Security |

The old marketing text referred generically to `hr.contract`; current OneHR architecture already establishes `onehr.contract` + `hr.version` boundaries, so this addon does not create or inherit a second canonical contract fact model.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

No ED0–ED5 classification is invented in the absence of exact governing registry rows.
