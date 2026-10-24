
# OneHR Portal Self-Service — Bounded Runtime Repair Attempt 2

TASK: `onehr_portal_self_service` activation repair  
ATTEMPT: 2 of 2  
DATE: 2026-08-29  
TARGET_PLATFORM: Odoo 19 Community Edition (`19.0.20251217`)  
SOURCE_WRITE_SCOPE: `onehr_portal_self_service` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Runtime evidence

Activation failed while Odoo loaded:

`security/onehr_portal_security.xml`

Observed first concrete root cause:

`ValueError: External ID not found in the system: portal.group_portal`

The failing expression was:

`Command.link(ref('portal.group_portal'))`

Odoo 19 owns the Portal user-type group under the `base` module as:

`base.group_portal`

The `portal.group_portal` external ID does not exist in the reported Odoo 19 runtime.

## Bounded architecture-preserving correction

Only the Odoo-owned external-ID reference is corrected:

- before: `portal.group_portal`
- after: `base.group_portal`

The Portal Employee role still means an authenticated Odoo Portal user. No OneHR role,
ACL, record rule, business model, workflow, controller route, dependency, integration
contract, company boundary, history rule or feature is removed or widened.

Manifest release marker is bumped from `19.0.1.0.0` to `19.0.1.0.1`.

## Regression prevention

`tools/source_acceptance.py` now:

- rejects any reappearance of `portal.group_portal`;
- requires `base.group_portal`;
- expects release `19.0.1.0.1`;
- inventories 33 post-install tests.

A runtime regression test also verifies that a Portal Employee has
`base.group_portal` and does not acquire `base.group_user`.

## Retry hard gate

This correction consumes bounded Attempt 2/2 for the current Direct Full Build task.

If deployment of this exact package exposes another activation failure, capture the FIRST
complete traceback. Do not perform an automatic third source mutation under this task.

`ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO`

