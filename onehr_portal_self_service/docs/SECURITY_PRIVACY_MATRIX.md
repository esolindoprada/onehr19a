
# OneHR Portal Self-Service — Security & Privacy Matrix

| Role | Request Type / Stage | Request | Portal scope | Decision authority |
|---|---|---|---|---|
| Portal Employee | Read active portal catalogue | Create/read/write own Draft; no delete | Own requests | Submit/cancel own request within lifecycle rules |
| Portal Manager | Employee catalogue | Read/write direct-team request under record rules | Own + direct-team requests | Manager approve/reject only assigned direct reports |
| Portal HR Officer | Company/shared config read/write | Company-scoped operations | Backend HR processing | HR approve/reject, processing, SLA and downstream execution |
| Portal HR Manager | Full governed config | Full company authority incl. Draft delete | Backend administration | Highest Portal configuration authority |

Security design:
- global company rule applies to Portal requests;
- shared/company rules apply to type/stage catalogues;
- group rules narrow employee and manager scope;
- model methods validate ownership and lifecycle even if a UI button is exposed accidentally;
- no Portal ACL is granted to `base.group_user`;
- no business `sudo()` is used;
- all website routes are `auth='user'`; no public HR route exists;
- controller record access is checked under the current user;
- downstream execution calls target models under the current HR user's normal access;
- expected target-addon authorization/configuration errors are retained as integration evidence, not bypassed;
- employee dashboard contracts expose safe display subsets and omit inaccessible soft-integration cards;
- confidential Discipline information is not surfaced by this addon.
Additional portal trust-boundary controls:
- portal detail pages render only non-internal `mail.message` comment subtypes; `mail.mt_note` and other internal chatter are never passed as the portal conversation stream;
- `auto_execute_on_approval` is not an authority-escalation mechanism: employee/Portal Manager final approval leaves the hand-off Pending, while only Portal HR may execute the downstream service;
- external Portal Employee/Manager actions do not require permission to create internal `mail.activity` records; internal activity scheduling is restricted to internal/system execution contexts;
- portal file uploads are created through the governed `mail.thread` attachment path, not through a broad direct `ir.attachment.create()` grant, and are bounded by count/per-file/total-size limits.


