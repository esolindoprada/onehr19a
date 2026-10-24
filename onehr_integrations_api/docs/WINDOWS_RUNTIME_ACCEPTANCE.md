# OneHR Integrations API — Windows Runtime Acceptance

Source/static PASS is not runtime completion.

1. Back up the database and old addon; replace the whole `onehr_integrations_api` folder, never merge.
2. Restart Odoo 19 CE and Update Apps List.
3. Install OneHR Integrations API; capture the FIRST complete traceback if activation fails.
4. Verify exactly five custom persistent models and native settings extension register.
5. Verify hard dependency graph adds only `onehr_security` directly.
6. Run all 26 post-install tests on a disposable database.
7. Verify API Operator read-only behavior and API Admin configuration behavior.
8. Verify API Admin does not gain HR/System authority.
9. Create a least-privilege service user, API key and scope; generate credential once; confirm plaintext is not stored.
10. Test correct/wrong/revoked/expired key, missing scope, HMAC mismatch, timestamp expiry, duplicate request ID and 429 behavior.
11. Test multi-company denial and branch-key fail-closed behavior.
12. Exercise Health and Employee GET using only the service user's normal ACL/rules.
13. Install each relevant domain addon and smoke its specific API adapter under a correctly permissioned service user.
14. Verify absent optional addon returns capability-unavailable without dependency mutation.
15. Configure inbound webhook; test HMAC, duplicate request, rate limit and fixed allow-listed dispatch.
16. Configure outbound HTTPS webhook; test success, non-2xx, timeout, DNS/private-address rejection and redirect rejection.
17. Verify bounded retry → dead letter; manual Retry/Process buttons; no duplicate queue fan-out for same dedupe key.
18. Verify API logs, hashes, optional redaction, Pivot/Graph and retention archive cron.
19. Validate OpenAPI JSON/static YAML and Postman collection.
20. Run `-u onehr_integrations_api --stop-after-init`, repeat upgrade, and verify credentials/config/evidence preserved.
21. Compare exact Registry ED rows; do not infer them from runtime success.
22. Run post-upgrade cross-addon contract smoke and sibling fingerprint comparison.

Any failure must be root-cause classified before source mutation. Attempt limit remains two per bounded task.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO


## Attempt 1 activation evidence / Attempt 2 re-test

Attempt 1 (`19.0.1.0.0`) failed during XML view validation before installation completed:

`Unsearchable field "failed_count" in path "failed_count" in domain of filter dead_letters.`

Attempt 2 (`19.0.1.0.1`) stores the existing computed `failed_count` metric so the
existing `Has Dead Letters` filter is valid and searchable. Re-run activation from step 1.

This is the final bounded source attempt for the current task. Any further failure must
be captured and classified; no automatic third repair is authorized.
