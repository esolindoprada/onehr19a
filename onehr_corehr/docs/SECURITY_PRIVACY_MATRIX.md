
# onehr_corehr — Security / Privacy Matrix

| Control | Enforcement |
|---|---|
| Broad internal user CRUD | Not granted |
| Core HR Officer | Dependents, emergency, education, external history; inherits sensitive-data reader intentionally |
| Core HR Manager | Core HR Officer + HR Manager + engagement policy maintenance |
| Identifier Steward | Explicit raw identifier authority; masked routine list display |
| Occupational Health Officer | Isolated work incident/medical/accommodation authority + restricted-data reader |
| HR Manager → Occupational Health | NOT implied |
| OneHR Security Admin → Occupational Health | NOT implied |
| `hr.employee.public` | Only `onehr_employee_number`; no identifier/medical/disability/private fields |
| Identifier uniqueness | Fingerprint + company/type uniqueness; raw identifier not logged |
| Identifier reads | Protected payload reads create structured security audit |
| Occupational-health reads | Protected payload reads create structured security audit |
| Occupational-health changes | High/critical structured security audit |
| Work incident closed evidence | Immutable |
| Medical finalized evidence | Immutable; correction creates superseding assessment |
| Disability/accommodation closed evidence | Immutable |
| Custom history deletion | Blocked normally with uninstall-safe `@api.ondelete(at_uninstall=False)` |
| Company boundary | Record rules on every custom persistent model |
| Branch boundary | Not owned here; later branch addon may narrow |
| Personal documents | Not stored here; `onehr_document` owns document security |
| PDF employee summary | Excludes identifiers, medical and disability detail |

UI groups/invisible attributes are never the authorization boundary.
