# OneHR Integrations API — Enterprise Completeness Matrix

| Area | Source status | Runtime status |
|---|---|---|
| Project identity / root guardrail | PASS | n/a |
| Generic scaffold replacement | PASS | PENDING install |
| Exact five persistent models | PASS source | PENDING registry |
| Registry ED classification | PENDING exact rows | PENDING |
| Hard dependency exactly `onehr_security` | PASS source | PENDING loader |
| API key/scopes/lifecycle | PASS source | PENDING UAT |
| PBKDF2 one-time API secret | PASS source | PENDING UAT |
| HMAC/timestamp/request-ID replay control | PASS source | PENDING HTTP UAT |
| Per-key rate limiting | PASS source | PENDING load UAT |
| Service-user least privilege/company scope | PASS source | PENDING security UAT |
| Branch fail-closed boundary | PASS source | PENDING branch UAT |
| REST v1/error/CORS/OpenAPI/Postman | PASS source | PENDING HTTP UAT |
| Inbound allow-listed HMAC webhook | PASS source | PENDING HTTP UAT |
| Outbound HMAC webhook | PASS source | PENDING network UAT |
| SSRF/no-redirect/bounded response | PASS source | PENDING network UAT |
| Retry/backoff/dead-letter cron | PASS source | PENDING scheduler UAT |
| Immutable API audit/body hashes | PASS source | PENDING UAT |
| Payload redaction/log retention | PASS source | PENDING UAT |
| Soft sibling adapters | PASS source contract | PENDING installed-suite smoke |
| Search view every persistent model | PASS source | PENDING UI |
| Webhook Dead Letter search field is searchable/stored | PASS repaired 19.0.1.0.1 | PENDING re-activation |
| Enterprise Lists/Forms/actions | PASS source | PENDING UI |
| Kanban/Pivot/Graph where useful | PASS source | PENDING UI |
| Hard Gate 11 DB/ORM naming | PASS source | PENDING registry loader |
| No business sudo / no broad base user CRUD | PASS source | PENDING security UAT |
| 26 post-install test methods | PASS source inventory | PENDING execution |
| Fresh install | NOT RUN | PENDING |
| Upgrade / repeat upgrade | NOT RUN | PENDING |
| Post-upgrade contract smoke | NOT RUN | PENDING |
| Cross-addon preservation | PASS package scope | PENDING deployment fingerprint |

SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME when source acceptance passes.  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO
