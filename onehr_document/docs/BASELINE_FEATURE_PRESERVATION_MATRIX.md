# onehr_document — Baseline Feature Preservation Matrix

| Historical / approved intent | Direct Full implementation | Decision |
|---|---|---|
| Document library | `onehr.document` + immutable `onehr.document.version` | PRESERVED + HARDENED |
| Category/classification | `onehr.document.category` with sensitivity and governance defaults | PRESERVED + HARDENED |
| Numbering | Canonical `ir.sequence`, code `onehr.document` | PRESERVED WITHOUT NEW NUMBERING MODEL |
| Tags/search metadata | `keywords` on document + governed category | PRESERVED WITHOUT INVENTING TAG MODEL |
| QWeb/Jinja-style variables | Bounded `{{ token }}` contract + QWeb PDF shell | PRESERVED SAFELY |
| Template versions | `onehr.document.template` + immutable `onehr.document.template.version` | EXPANDED TO REGISTRY MODEL |
| Validity | ED2 header/version dates and expiry/grace/retention dates | PRESERVED + HARDENED |
| Reminder cron | Daily expiry/reminder governance + `mail.activity` | PRESERVED |
| Draft → issued → signed → archived/expired | Explicit document/version state machines and server actions | PRESERVED + EXPANDED |
| Generate Wizard | `wizard.document.generate` | PRESERVED |
| Publish & Sign Wizard | `wizard.document.publish.sign` | PRESERVED |
| E-sign status | `onehr.esign.transaction` metadata and adapter hook | PRESERVED + REGISTRY-ALIGNED |
| Provider endpoint/credentials in settings | Not stored here; soft integration owns provider plumbing | MOVED BY ARCHITECTURE, NO FUNCTION LOSS |
| `res.config.settings` document extension | Omitted because no Registry ownership row; category/template defaults replace local policy settings | REJECTED WITH REGISTRY REASON |
| Portal download | No portal hard dependency/controller here; future portal addon references secured document/version | DEFERRED WITH CONTRACT |
| Per-branch access | No reverse hard dependency; company boundary now, branch addon may narrow later through integration | DEFERRED WITH OWNERSHIP CONTRACT |
| Reports | QWeb controlled PDF + list/pivot/graph expiry and e-sign analysis | PRESERVED + EXPANDED |
| Audit | Chatter/activity + `onehr.audit.log` high-risk evidence | PRESERVED + HARDENED |
| Lock signed/issued evidence | Server-side immutability + uninstall-safe `@api.ondelete` | PRESERVED + HARDENED |
| Attachment URLs must not bypass access | Attachment-backed model field, no public controller, record rules on owning version | HARDENED |

No feature was removed merely to make static/runtime tests easier.
