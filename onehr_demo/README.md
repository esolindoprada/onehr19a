
# OneHR Enterprise Demo Dataset

`onehr_demo` is the non-production Enterprise Demo Dataset control plane for
**OneHR NEW on Odoo 19 Community Edition**.

This release is **19.0.1.0.7** and advances the bounded roadmap through
**MASTER PROMPT 05–06 — Enterprise Foundation plus Jobs, Positions, Grades & Work Locations**.

## Frozen authority

- Authoritative composite source: `onehr19a(20260910-065304).md`
- Authoritative source SHA-256: `db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`
- Governing Master Prompt SHA-256: `21da5974ff755c03ffb2cc12d0e073832370c3e4dcefc3af21376e5b3dc52457`
- Oracle HRMS benchmark SHA-256: `a02355585ce8a5a33427e3ac5a7ef424618986a778b906b165606a178a5ceb98`
- Root Guardrail SHA-256: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`
- Frozen production OneHR addons: `25`
- Whole-path business generator contracts: `20`
- Implemented bounded generators in this release: `2` (`foundation.enterprise`, `organization.jobs_positions`)
- Explicit production sequence policies: `34`

The complete MP05–MP24 production capability graph is still audited before the first
business mutation. Implementing one phase does **not** reduce compatibility preflight
to that phase.

## Control-plane ownership remains unchanged

Exactly six persistent demo-only models remain owned by `onehr_demo`:

- `onehr.demo.scenario`
- `onehr.demo.run`
- `onehr.demo.generator`
- `onehr.demo.checkpoint`
- `onehr.demo.reference`
- `onehr.demo.log`

No employee, branch, department, job, assignment, recruitment, payroll, learning,
appraisal, talent, discipline, portal, integration, or analytics business master is
re-owned by this addon.

## MP05 business dataset

The scenario's selected `res.company` remains the canonical legal company. MP05 does
not create a parallel company master and does not rename the selected company.

The generator creates/reuses deterministic synthetic masters:

| Profile | Branches | Organization Units |
|---|---:|---:|
| QUICK | 2 | 7 |
| STANDARD | 4 | 12 |
| FULL ENTERPRISE | 6 | 16 |

Branches use `onehr.branch`; organization units use canonical `hr.department`.
Hierarchy, company scope and effective dates are validated inside the same generator
savepoint before the checkpoint can PASS.

## Deterministic identity rule

`onehr_demo` never calls `ir.sequence.next_by_code()` directly.

The orchestration identity is:

`<scenario>.<domain>.<entity>.<stable-key>`

Production sequences remain production-owned business/presentation identifiers. They
are never used as the demo idempotency key, dependency key, resume cursor, or
chronology source. The 34 production sequence contracts are audited explicitly on
every compatibility refresh.

## Reset / rebuild rule

MP05 masters are classified `REUSE_ON_REBUILD`.

**Reset Preview → Execute Safe Reset** invalidates only the scenario provenance
references. The selected company, generated branches and generated departments remain
intact. **Rebuild Dataset** re-runs whole-path compatibility/readiness and rebinds to
the exact retained target IDs. There is no broad company/date/name cleanup and no
generic unlink fallback.

## Windows upgrade / first MP05 trial

1. Replace the complete existing `onehr_demo` folder with this release.
2. Stop/restart Odoo so Python imports are cold.
3. Update Apps List.
4. **Upgrade** `OneHR Enterprise Demo Dataset`.
5. Open **OneHR → Configuration → Enterprise Demo Dataset**.
6. Open the existing scenario or create one.
7. Click **Refresh Source Compatibility**.
8. If compatibility fails, inspect the **complete Compatibility Evidence** from the
   same run; do not repair only the first line.
9. Tick the NON-PRODUCTION acknowledgement and click **Enable Demo Generation**.
10. Click **Validate Readiness**.
11. If readiness is PASS, run **Generate Quick Dataset** first.
12. Click **Validate Dataset**.
13. Then test **Reset Preview → Execute Safe Reset → Rebuild Dataset**.

Readiness audits the actual current operator before generation. It must be allowed to
read/create `onehr.branch` and `hr.department`, and the selected company must have
OneHR Branch Scope enabled. The generator does not weaken production ACLs or grant
itself broader roles.

`SOURCE_ACCEPTANCE_PASS != WINDOWS_RUNTIME_PASS != MP05_GENERATION_PASS != FULL_ENTERPRISE_CERTIFIED`

## Operator navigation — 19.0.1.0.5 closure

Use **OneHR → Configuration → Enterprise Demo Dataset → Demo Control Center** to create or open a Demo Scenario.
The **Demo Evidence** branch (Generator Registry, Runs, Checkpoints, References, Logs) is intentionally evidence/control-plane output and is not the dataset creation surface.

The parent **Enterprise Demo Dataset** menu is deliberately action-free because an Odoo menu that owns child menus acts as a navigation container; the creatable Scenario action is exposed through the dedicated leaf menu instead.

## 19.0.1.0.5 deterministic sequence closure

Production `ir.sequence` policies remain audited for whole-path traceability, but their mutable database rows and counters are no longer a prerequisite for the currently implemented demo generation path. `onehr_demo` identity is derived from deterministic scenario/domain/entity/stable-key values and provenance.


## 19.0.1.0.7 — bounded batch execution and MP06 prerequisite closure

The Control Center executes the frozen generator contracts model-by-model using deterministic `(phase, key)` ordering. MP06 adds bounded Jobs, Positions, Grades and Work Locations generation with explicit provenance.

**Execute Next 10** is an execution accelerator over the same deterministic engine. It processes at most ten next implemented contracts, stops immediately on failure or an unimplemented contract, never skips a requirement, and uses one bounded generation run for the batch. On runtime failure the notification intentionally does **not** reload the form, so the operator can copy the exact error while the failed checkpoint/run evidence remains persisted.

MP06 also reconciles the exact MP05 department provenance required by the selected profile. This closes the earlier profile mismatch where a QUICK scenario could have MP05 PASS while the IT department required by the rank-1 IT Manager job was absent.

