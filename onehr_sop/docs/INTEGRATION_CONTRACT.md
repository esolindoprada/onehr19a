# OneHR SOP — Integration Contract

## OneHR Document — hard owner
`onehr_document` remains the owner of immutable archived document snapshots.
Each SOP master reuses one `onehr.document` header. Every published SOP version
creates and issues one `onehr.document.version` containing the governed SOP body.
A successor archives the prior Document version. SOP does not duplicate Document
binary/template/e-sign masters.

## Portal — soft/downstream
`onehr_sop_portal_payload(sop_code)` exposes only the caller's currently assigned
Published SOP under normal SOP record rules. `onehr.sop.ack.action_acknowledge()`
records Read & Agree. Portal routes, sessions and authentication remain owned by
`onehr_portal_self_service`.

## Analytics — soft/downstream
`onehr_sop_kpi_snapshot(company=None)` exposes published SOP count, audience count,
acknowledgement count/rate, overdue review count and average days to 90% acknowledgement.
Dashboard persistence remains owned by `onehr_analytics`.

## Integrations API — downstream
`onehr_sop_ack_status(employee_number=None, sop_code=None)` is a model-service boundary.
HTTP endpoints, token/signature policy, throttling, retry and webhooks remain owned by
`onehr_integrations_api`.

## Multi-company/branch
Company is the hard legal/security partition. Branch remains optional downstream and
is not invented as a hard SOP field/dependency.
