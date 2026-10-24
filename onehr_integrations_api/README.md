# OneHR Integrations API

Enterprise integration boundary for OneHR NEW on Odoo 19 Community Edition.

This Direct Full Addon Build replaces the supplied tutorial scaffold and implements
the five product-approved persistent integration models:

- `onehr.api.key`
- `onehr.api.scope`
- `onehr.webhook`
- `onehr.api.log`
- `onehr.api.queue`

It also extends the native transient `res.config.settings`; no sixth persistent
business model is introduced.

## Enterprise capabilities

- versioned `/onehr/api/v1/*` REST endpoints;
- API key + granular scope authorization;
- PBKDF2-HMAC-SHA256 API-secret hashing; plaintext API secrets are never stored;
- optional request HMAC using the presented API secret;
- timestamp + request-ID replay protection; domain retries remain idempotent where the owning OneHR service provides an external-reference contract;
- per-key and inbound-webhook rate limits;
- single-company execution boundary per API key/webhook service identity;
- soft adapters to installed CoreHR, Attendance, Recruitment, Time Off,
  Workflow Approval, Document/e-Sign, Learning, Appraisal, Career/Succession,
  Payroll Bridge, PnP, SOP, Job Description and Portal contracts;
- outbound HMAC webhooks, SSRF-aware target validation, no redirect following,
  bounded exponential retry and dead-letter evidence;
- immutable API audit logs with body hashes and optional sanitized payload logging;
- OpenAPI and Postman assets;
- operational list/form/search/kanban/pivot/graph views and professional actions.

## Hard dependency

Exactly `onehr_security`.

`onehr_security` already provides the OneHR Base/mail/security foundation transitively.
All business-domain adapters are soft and are activated only when their owner addon is
installed. This avoids reverse dependencies and preserves domain ownership.

## Install

Replace the complete old `onehr_integrations_api` folder. Do **not** merge the old
tutorial scaffold.

1. Restart Odoo.
2. Update Apps List.
3. Install **OneHR Integrations API**.
4. Assign **API Administrator** to integration administrators.
5. Create API keys and bind each key to a least-privilege internal service user.
6. Configure scopes before activation.
7. Run the Windows runtime acceptance checklist.

## Source acceptance

```text
python tools/source_acceptance.py
```

Source/static PASS is only permission to start runtime validation. It is not proof
of Windows/Odoo runtime, security UAT, upgrade/idempotency or enterprise completeness.

`ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO` until runtime evidence is completed.


## Runtime repair 19.0.1.0.1

Odoo 19 activation exposed that the Webhook `Has Dead Letters` search filter referenced
a non-searchable computed `failed_count`. Version 19.0.1.0.1 preserves the feature and
stores that metric so the search domain is valid. This is bounded repair Attempt 2/2.
