# OneHR SOP

Enterprise Standard Operating Procedure governance for OneHR NEW on Odoo 19 CE.

Persistent business models are **exactly**:

- `onehr.sop`
- `onehr.sop.version`
- `onehr.sop.ack`

Hard dependencies are **exactly**:

- `onehr_security`
- `onehr_document`

The addon implements Draft → Review → Approved → Published → Obsolete,
targeted publication by department/job/employee, employee read-and-agree,
periodic review, retention, acknowledgement audit export, archived immutable
Document snapshots, compliance KPIs, Portal-safe payloads and API-ready model services.

The package intentionally contains no legacy tutorial controller, demo data,
generic `onehr_sop.onehr_sop` model, or public route.

Source/static acceptance is not runtime acceptance. Fresh install, test execution,
security UAT, scheduler, QWeb, Document archive integration and upgrade/idempotency
must pass on the user's Odoo 19 runtime before the addon can be frozen.
