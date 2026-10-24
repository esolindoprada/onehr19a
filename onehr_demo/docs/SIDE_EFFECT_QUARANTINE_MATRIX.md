
# OneHR Demo — Side-Effect Quarantine Matrix

The frozen registry classifies every MP05–MP24 domain before generation.

| Classification | Meaning |
|---|---|
| `SAFE_INTERNAL` | Internal OneHR state/evidence only |
| `SAFE_WITH_DEMO_CONTEXT` | Safe only after production-supported demo-safe behavior is proven |
| `DISABLED_FOR_DEMO` | External/downstream behavior remains disabled |
| `REQUIRES_STUB/LOCAL_ENDPOINT` | Integration demo must use a stub/local test endpoint |
| `PROHIBITED` | The action must not be invoked |
| `UNVERIFIED` | Blocks the generator |

MP05 `foundation.enterprise` is `SAFE_INTERNAL`. It creates/reuses only the selected
company reference, `onehr.branch` masters and canonical `hr.department` organization
masters. Canonical `onehr.branch.create()` also emits normal OneHR append-only audit
and chatter evidence. That evidence is an intentional production-side
`IMMUTABLE_PROTECTED` side effect: it is not used as demo identity, is not reset or
rewritten by `onehr_demo`, and may contain real execution timestamps/correlation IDs
only as observability evidence. MP05 sends no outgoing mail/SMS, portal invitation,
webhook, API call, payroll export, or accounting post.

Payroll Bridge remains `DISABLED_FOR_DEMO`; Integrations API remains
`REQUIRES_STUB/LOCAL_ENDPOINT` until their later bounded phases.

