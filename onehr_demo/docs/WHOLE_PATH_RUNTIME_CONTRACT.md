
# OneHR Demo — Whole-Path Runtime Contract

This contract prevents serial one-error-at-a-time repair.

Every **Refresh Source Compatibility** performs one non-short-circuiting audit of:

1. Odoo 19 major version;
2. module-operation quiescence (`to install`, `to upgrade`, `to remove`);
3. root Guardrail raw + declared SHA-256;
4. installed/runtime versions for all 25 production OneHR addons;
5. normalized production manifest fingerprints;
6. published addon source fingerprints where available;
7. all 20 MP05–MP24 generator model/field/method/selection/XML-ID/group contracts;
8. native Odoo runtime fields explicitly used by implemented generators;
9. all 34 production `ir.sequence` policies and their stable identity contracts, with mutable sequence rows/counters explicitly non-blocking for current demo generation;
10. explicit side-effect and reset classifications.

The audit records the complete failure set. Sequence configuration remains evidence only and
never becomes a hidden generation prerequisite. `first_actionable_root_cause` is a navigation
aid only; it never means later failures were skipped.

The compatibility fingerprint hashes content/runtime/scenario truth only. Database
name, operator, execution timestamp and the human source filename/label are retained
as evidence metadata but are excluded from the compatibility hash. Therefore renaming
an otherwise byte-identical composite export cannot make a different business
compatibility lock.

Current frozen source: `onehr19a(20260910-065304).md`  
SHA-256: `db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`

## Readiness is separate from compatibility

Compatibility proves the production path exists. Readiness then proves the current
operator and selected scenario can safely execute every **currently implemented**
generator. For MP05 that includes:

- selected company is allowed to the operator;
- OneHR Branch Scope is enabled;
- branch administration authority is present;
- `res.company` read is allowed;
- `onehr.branch` read/create is allowed;
- `hr.department` read/create is allowed;
- non-production acknowledgement and explicit enablement are active.

No source mutation is authorized by a readiness failure.

## Operator entry-point closure

The whole-path contract now also requires a reachable, creatable `onehr.demo.scenario` Control Center leaf. The five Demo Evidence menus are explicitly non-creation surfaces and cannot substitute for the Scenario entry point.

