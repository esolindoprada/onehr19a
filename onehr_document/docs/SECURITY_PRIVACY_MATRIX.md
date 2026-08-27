# onehr_document — Security / Privacy Matrix

| Control | Enforcement |
|---|---|
| Legal company partition | Global record rule on every persistent model |
| Employee self access | Own employee-linked + employee-visible + internal only |
| Confidential operations | Document Officer/Manager, company scoped |
| Restricted document visibility | Document Compliance; manager does not automatically imply restricted access |
| Restricted mutation | Requires a user holding Manager capability plus restricted/compliance visibility |
| Source business record | `check_access("read")` before source snapshot/open; no sudo |
| Attachment security | Binary stored as attachment-backed field on protected `onehr.document.version`; no public controller |
| High-risk audit | `onehr.audit.log._log_event()` after business authorization |
| Issued version history | Immutable business facts; uninstall-safe deletion protection |
| Template version history | Immutable after activation; successor version workflow |
| E-sign evidence | Terminal transaction immutable and non-deletable |
| External secrets | No token/password/API key/client secret fields |
| Broad internal-user CRUD | Not granted |
| Portal | No route/controller in this addon; later portal integration must reference secured records |
| Branch | No reverse dependency/ownership; branch narrowing remains extension responsibility |
| Approval | No duplicate approval evidence; workflow addon remains canonical owner |

| Category metadata | Employee sees only employee-visible internal categories; Officers see non-restricted; Compliance extends to restricted |
