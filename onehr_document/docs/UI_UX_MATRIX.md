# onehr_document — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart Buttons | Header / Body Actions | Row / One2many Actions | Chatter |
|---|---|---|---|---|---|---|---|---|
| `onehr.document.category` | yes | yes | yes | N/A | Documents, Templates | governed configuration | N/A | yes |
| `onehr.document` | yes | yes | yes | Draft/Active/Archived | Versions, Current, Employee, Source, E-Sign | Activate, New Version, Generate, Archive; body Create/Generate | Current, New Version, Print, Sign | yes |
| `onehr.document.version` | yes | yes | yes | Draft/Issued/Signature Pending/Signed/Expired/Archived/Superseded | Document, E-Sign | Issue, Store PDF, Request Sign, Mark Signed, Successor, Expire, Archive, Print; body expiry reminder | Print, Sign, Document; E-sign evidence rows | yes |
| `onehr.document.template` | yes | yes | yes | active ribbon | Versions, Generated | Create Template Version; body successor action | New Version, Versions | yes |
| `onehr.document.template.version` | yes | yes | yes | Draft/Active/Retired | Template, Generated | Activate, Retire, Successor | Activate, Successor, Template | yes |
| `onehr.esign.transaction` | yes | yes | yes | Queued/Sent/Viewed/Signed/Rejected/Cancelled/Error | Document Version | Cancel (manager) | Version, Cancel | yes |
| `wizard.document.generate` | N/A | modal | N/A | N/A | N/A | Preview, Generate | N/A | N/A |
| `wizard.document.publish.sign` | N/A | modal | N/A | N/A | N/A | Queue Signature Request | N/A | N/A |

Additional analysis views:
- Document Version pivot/graph for status and expiry governance.
- E-Sign Transaction pivot/graph for provider/status evidence.

UI visibility never substitutes for ACL, record rule or server-side authorization.
