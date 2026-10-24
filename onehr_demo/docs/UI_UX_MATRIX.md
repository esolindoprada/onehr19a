
# OneHR Demo — UI / UX Matrix

| Model | List | Form | Search | Statusbar | Smart/Action Buttons | Purpose |
|---|---|---|---|---|---|---|
| `onehr.demo.scenario` | Yes | Yes | Yes | Full lifecycle | Compatibility, readiness, safety, generation boundary, reset, evidence navigation | Enterprise Demo Control Center |
| `onehr.demo.run` | Yes | Yes | Yes | Run state | Checkpoint smart/action button | One orchestration execution |
| `onehr.demo.generator` | Yes | Yes | Yes | Implementation state | Open | Fixed registry metadata |
| `onehr.demo.checkpoint` | Yes | Yes | Yes | Checkpoint state | Run/Generator navigation | Bounded generator evidence |
| `onehr.demo.reference` | Yes | Yes | Yes | Reference state | Target/Run navigation | Deterministic provenance |
| `onehr.demo.log` | Yes | Yes | Yes | N/A | N/A | Immutable sanitized evidence |

The Scenario form visibly carries a NON-PRODUCTION ribbon, statusbar, compatibility
and readiness badges, deterministic clock/seed, smart counters, progress, first root
cause, compatibility evidence and related run/reference/log tabs.

## Navigation / create policy

- **Enterprise Demo Dataset** is a pure menu container.
- **Demo Control Center** is the explicit leaf action for `onehr.demo.scenario`; Demo Administrators may create a scenario there.
- **Demo Evidence** is secondary evidence navigation. Generator Registry is code-owned/frozen, while Runs, Checkpoints, References and Logs are orchestration evidence; their menu actions intentionally suppress manual creation.
- The five evidence lists are therefore not a substitute for the Scenario/Control Center creation surface.


