# OneHR Integrations API — Security & Privacy Matrix

| Role/identity | Configuration | Logs/Queue | Business domain authority |
|---|---|---|---|
| API Operator | read | read | none implied |
| API Administrator | governed create/write | read + governed queue actions | none implied |
| API Key Service User | no automatic Integration Hub admin | n/a | exactly its existing Odoo groups/ACL/rules, one company context |
| Inbound Webhook Service User | no automatic Integration Hub admin | n/a | exactly its existing Odoo groups/ACL/rules, one company context |
| Public HTTP user | no model CRUD | no model CRUD | none; credential verification occurs first |

Security controls:
- no custom-model CRUD for `base.group_user`;
- API Admin does not imply HR Officer/Manager or Settings/System authority;
- global company rules on key/webhook/log/queue;
- API keys bind one company and internal service user;
- domain adapters use `with_user` + `with_company` + `allowed_company_ids`, never business `sudo()`;
- PBKDF2-HMAC-SHA256 API secrets: plaintext shown once, never stored;
- webhook signing secret is reversibly stored only because outbound signing requires it; field is API-Admin restricted and never logged;
- optional HMAC binds timestamp, request ID, method/path and body hash; mutating calls require request ID;
- body hashes are always logged; bodies are optional and redacted;
- branch-scoped key is rejected when the domain owner exposes no verifiable branch field;
- outbound targets are SSRF-checked, HTTPS by default, private/loopback blocked by default, redirects disabled;
- no arbitrary user-supplied model/method dispatch.
