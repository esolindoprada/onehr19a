
# OneHR Demo — Reset Capability Matrix

Reset starts only from active `onehr.demo.reference` rows for the selected scenario.
There is no generic unlink fallback.

| Generator / Model | Policy | Current Reset Action |
|---|---|---|
| MP05 `res.company` | `REUSE_ON_REBUILD` | Retain record; invalidate demo reference |
| MP05 `onehr.branch` | `REUSE_ON_REBUILD` | Retain record; invalidate demo reference |
| MP05 `hr.department` | `REUSE_ON_REBUILD` | Retain record; invalidate demo reference |
| MP06+ models | Frozen per generator contract | Block until that phase adds its bounded handler |

Reset Preview reports each stable key, model, company, policy and planned action.
Any active reference without an exact `(model, reset_policy)` handler is
`PROTECTED_NO_HANDLER` and blocks Execute Safe Reset.

MP05 reset never says “all demo data deleted” because the intended business masters
are explicitly retained for deterministic rebuild.

Production audit/chatter evidence emitted by canonical branch administration is not
demo-owned destructive data. It remains intentionally immutable/protected and is
outside the reset deletion objective. This is reported/documented rather than hidden.

