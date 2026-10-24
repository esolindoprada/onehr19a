
# OneHR Demo — Demo Control Center Navigation Closure

VERSION: `19.0.1.0.2`
ROOT_CAUSE_CLASSIFICATION: `ADDON_SOURCE_FAILURE`
AUTHORITATIVE_SOURCE_LABEL: `onehr19a(20260910-065304).md`
AUTHORITATIVE_SOURCE_SHA256: `db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`
WRITE_SCOPE: `onehr_demo` only

## Runtime symptom

Under **Configuration → Enterprise Demo Dataset**, the operator could only see the five Demo Evidence lists: Generator Registry, Runs, Checkpoints, References and Logs. Those surfaces intentionally do not expose manual creation.

## Full-path root cause

`menu_onehr_enterprise_demo_dataset` carried both `action_onehr_demo_scenarios` and child menus. In Odoo's application menu navigation, a menu that owns children is used as a navigation container, so the child branch was surfaced while the Scenario action was not a reliable operator entry point. The Scenario model/action/ACL itself already allowed a Demo Administrator to create a controlled scenario.

## Bounded repair

- Keep **Enterprise Demo Dataset** as an action-free parent container.
- Add **Demo Control Center** as an explicit leaf menu pointing to `action_onehr_demo_scenarios`.
- Keep **Demo Evidence** as a sibling child branch.
- Preserve read-only/no-manual-create semantics for Generator Registry, Runs, Checkpoints, References and Logs.
- Add static and post-install regression gates proving the Control Center remains reachable and scenario creation is not suppressed.

No production sibling addon, model ownership, dependency, workflow, record rule, sequence, deterministic key, generator order, reset policy, effective dating, or enterprise business feature is changed.

