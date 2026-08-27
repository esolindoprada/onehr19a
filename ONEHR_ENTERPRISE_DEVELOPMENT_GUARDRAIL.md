# OneHR Enterprise Development Guardrail v1

GUARDRAIL_ID: ONEHR-EDG-V1
STATUS: APPROVED_HARD_GATE
PROJECT: OneHR
TARGET_PLATFORM: Odoo 19 Community Edition
CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY: NONE
SIMPLIFICATION_AUTHORITY: NONE
DELETION_AUTHORITY: NONE
MODEL_OWNERSHIP_CHANGE_AUTHORITY: NONE
DEPENDENCY_CHANGE_AUTHORITY: NONE
MAX_CODEX_ATTEMPTS_PER_TASK: 2
MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1
STATIC_RUNTIME_PASS_IS_NOT_FUNCTIONAL_COMPLETENESS: TRUE
MOVE_FORWARD_REQUIRES_ALL_HARD_GATES: TRUE

## 1. Purpose

This document is a mandatory enterprise-development control for every OneHR addon.
It prevents implementation work, automated repair, runtime remediation, and upgrade
work from silently changing the approved architecture or reducing enterprise
functionality.

This guardrail is not advisory. It is a HARD GATE.

No OneHR addon may be declared FINAL, FROZEN, MOVE_FORWARD_READY, or safe for the
next addon unless every applicable gate in this document has passed with evidence.

## 2. Architecture authority

The architecture authority for OneHR is owned outside Codex.

The mandatory design authorities are:

1. OneHR Enterprise Architecture v2.
2. OneHR Master Model Registry v1.
3. The approved 25-addon topology and dependency ownership.
4. Odoo 19 CE native-model ownership where the Architecture/Registry designate
   Odoo-native canonical models.
5. The approved addon-specific implementation contract and prior accepted
   preservation decisions.

If any implementation request conflicts with these authorities, implementation
must STOP and the conflict must be reported. Codex must not resolve an
architecture conflict by inventing a new design.

## 3. Codex role — bounded implementation worker only

Codex is permitted to:

- inspect the exact assigned addon and approved references;
- implement explicitly approved models, fields, methods, views, security, data,
  tests, migrations, and compatibility repairs;
- diagnose a concrete runtime or test failure;
- make the smallest architecture-preserving correction that addresses the proven
  root cause;
- produce evidence and a precise change report.

Codex is NOT permitted to act as:

- architect;
- product owner;
- model-registry owner;
- scope reducer;
- simplifier;
- dependency redesign authority;
- deletion authority;
- cross-addon ownership authority;
- autonomous migration-policy author;
- endless retry engine.

## 4. Explicit prohibitions

Without an approved architecture/registry decision, Codex MUST NOT:

- delete a model, field, method, action, view, security rule, workflow, report,
  integration contract, historical behavior, or enterprise feature;
- merge two business models merely because one appears redundant;
- replace an approved model with a simpler model;
- move a model or feature to another addon;
- add a new canonical model that duplicates an Odoo-native canonical model;
- change an addon owner;
- add or remove a hard dependency;
- create a circular dependency workaround by changing ownership;
- weaken security, audit, history, effective dating, company isolation, or
  referential integrity to make tests pass;
- bypass a failing test by deleting, skipping, muting, or weakening the test;
- convert a required runtime test into a static-only assertion;
- treat PASS of syntax, install, upgrade, runtime, or tests as proof of complete
  enterprise functionality;
- rewrite an addon from scratch unless the approved task explicitly authorizes a
  registry-preserving rewrite;
- edit sibling addons unless the task explicitly authorizes each sibling and its
  approved change contract.

## 5. Preservation gate

Before implementation or repair, establish the expected structure from the
approved baseline:

- addon name and owner;
- manifest version and hard dependencies;
- registered models;
- inherited Odoo-native models;
- fields;
- methods/business actions;
- views/actions/menus;
- ACLs and record rules;
- seed/reference data;
- tests;
- effective-dating classification;
- security/privacy obligations;
- downstream extension contracts.

After implementation, compare actual structure against that expected structure.

Any unexplained loss is a HARD FAIL.

## 6. Master Model Registry gate

Every persistent/abstract/transient model touched by the task must have one of
the approved classifications/owners in the Master Model Registry.

Codex may not invent a registry decision.

If a required model/owner/classification is absent or ambiguous:

STOP_REASON: ARCHITECTURE_DECISION_REQUIRED

No code change may substitute for that missing decision.

## 7. Odoo-native-first gate

Where OneHR Architecture v2 designates an Odoo 19 CE model as canonical, OneHR
must extend/inherit that model rather than create a parallel canonical master.

Examples already frozen for OneHR include:

- hr.department for organization hierarchy;
- hr.job for generic job/role catalogue;
- hr.work.location for work locations;
- hr.employee + hr.version for employee/versioned employment facts where owned
  by Odoo;
- other Odoo-native domains exactly as recorded in the Registry.

A prohibited parallel canonical model is a HARD FAIL.

## 8. Effective-dating/history gate

ED0–ED5 behavior defined by the architecture/registry must not be reduced.

At minimum, implementation must preserve applicable:

- valid_from / valid_to semantics;
- future-dated updates;
- overlap prevention;
- temporal referential integrity;
- version history;
- update-versus-correction distinction;
- immutable/completed transaction evidence;
- regulatory version binding;
- as-of-date behavior.

A repair that makes runtime pass by weakening history is a HARD FAIL.

## 9. Security and privacy gate

Security changes must preserve least privilege and separation of duties.

Codex must not solve an access error by granting broad CRUD to
base.group_user or by removing record rules.

Applicable company/branch isolation, PII restrictions, sensitive-domain
isolation, approval authority, and audit evidence must be tested.

## 10. Runtime and upgrade gate

A source-stage PASS is not sufficient.

For an addon to become MOVE_FORWARD_READY, applicable evidence must include:

- source/static validation;
- exact dependency/model-registry validation;
- fresh install on disposable database;
- automated addon tests;
- security/record-rule tests;
- upgrade from the supported prior/deployed version when applicable;
- repeated upgrade/idempotency when applicable;
- post-upgrade contract smoke;
- source-preservation/fingerprint check;
- disposable database cleanup;
- explicit final move-forward decision.

Runtime harness failures must be distinguished from addon-source failures.

## 11. Enterprise functional completeness gate

STATIC PASS != RUNTIME PASS != TEST PASS != ENTERPRISE FUNCTIONAL COMPLETENESS.

Before FINAL/FROZEN/MOVE_FORWARD_READY, the reviewer must separately verify:

- approved feature preservation;
- complete model/field/method/action/view/security inventory;
- business behavior model by model;
- enterprise workflows and state transitions;
- temporal semantics;
- security/privacy;
- integration contracts;
- migration/upgrade behavior;
- audit/history;
- expected reports/configuration where in scope.

A technically installable but functionally reduced addon is NOT complete.

## 12. Bounded retry policy

Each Codex implementation/repair task has:

MAX_CODEX_ATTEMPTS_PER_TASK: 2
MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1

Meaning:

- Attempt 1: diagnose from evidence and implement the bounded approved correction.
- Attempt 2: allowed only when new evidence proves a distinct or incompletely
  addressed implementation defect within the same approved scope.
- The same root cause may not be retried repeatedly.
- If attempt 2 fails, STOP.
- If a failure is caused by architecture ambiguity, missing baseline, ownership
  conflict, unsupported destructive migration, or cross-addon redesign need,
  STOP immediately without consuming retries.

Required stop markers include one of:

STOP_REASON: ARCHITECTURE_DECISION_REQUIRED
STOP_REASON: BASELINE_MISSING
STOP_REASON: OWNERSHIP_CONFLICT
STOP_REASON: REPEATED_ROOT_CAUSE
STOP_REASON: DESTRUCTIVE_CHANGE_NOT_APPROVED
STOP_REASON: OUT_OF_SCOPE_CHANGE_REQUIRED
STOP_REASON: MAX_ATTEMPTS_REACHED

Codex must report evidence and wait for the architecture/reviewer decision.

## 13. Root-cause-first repair rule

A failed gate must be classified before source modification:

- HARNESS_FAILURE
- ENVIRONMENT_FAILURE
- ODOO_VERSION_COMPATIBILITY_FAILURE
- ADDON_SOURCE_FAILURE
- TEST_DEFECT
- DATA/MIGRATION_FAILURE
- ARCHITECTURE_CONFLICT

No addon source modification is allowed for HARNESS_FAILURE or ENVIRONMENT_FAILURE
unless evidence separately proves a source defect.

This prevents changing working business code to compensate for a broken runner.

## 14. Scope isolation gate

Default write scope is exactly one assigned addon.

Before and after every Codex task:

- hash/fingerprint all non-target OneHR addons or otherwise prove they are
  unchanged;
- record all intentionally changed files;
- fail if an unauthorized sibling addon changes.

For foundation/runtime validation, runtime harness files and disposable evidence
are outside addon source and must not silently rewrite business source.

## 15. Change-control rule

Every source change must map to:

- an approved Registry row;
- an approved Architecture v2 responsibility;
- a proven defect;
- or an explicitly approved enhancement.

Every deletion/merge/move requires an explicit architecture decision.
"Cleaner", "simpler", "not currently used", or "tests pass without it" are not
valid deletion reasons.

## 16. Required Codex prompt contract

Every future Codex prompt for OneHR must contain or load this guardrail and must
state at least:

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MAX_ATTEMPTS = 2
TARGET_ADDON = <exact addon>
WRITE_SCOPE = <exact approved paths>
APPROVED_ARCHITECTURE = OneHR Enterprise Architecture v2
APPROVED_REGISTRY = OneHR Master Model Registry v1
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

A Codex run lacking this contract is not an approved OneHR implementation run.

## 17. Evidence contract

Every bounded implementation/repair run must produce:

- task identifier;
- target addon;
- attempt number;
- input/baseline references;
- root-cause classification;
- files changed;
- models/fields/methods/views/security changed;
- tests added/changed;
- gates executed;
- exact failures;
- source fingerprint before/after where applicable;
- stop reason or move-forward status.

No "PASS" summary may omit failed/not-run gates.

## 18. Move-forward decision

ONEHR_<ADDON>_MOVE_FORWARD_READY may be YES only when:

- architecture/registry alignment PASS;
- preservation PASS;
- source/static PASS;
- runtime install PASS;
- required tests PASS;
- upgrade/idempotency PASS where applicable;
- security PASS;
- temporal/history PASS where applicable;
- post-upgrade smoke PASS;
- functional completeness review PASS;
- evidence complete;
- no unauthorized source changes;
- no unresolved architecture decision.

Otherwise:

ONEHR_<ADDON>_MOVE_FORWARD_READY: NO

## 19. Guardrail integrity

This document must be stored at the OneHR project root as:

ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md

Automation may verify its SHA-256. A missing or modified guardrail must stop the
job before implementation/runtime work begins.

END_GUARDRAIL: ONEHR-EDG-V1
