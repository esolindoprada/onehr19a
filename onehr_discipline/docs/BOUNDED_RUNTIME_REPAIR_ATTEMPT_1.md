
# OneHR Discipline — Bounded Runtime Repair Attempt 1

TASK: `onehr_discipline` activation repair  
ATTEMPT: 1 of 2  
DATE: 2026-08-24  
TARGET_PLATFORM: Odoo 19 Community Edition  
SOURCE_WRITE_SCOPE: `onehr_discipline` only  
INPUT_WORKSPACE: `onehr19a(20260824-093230).md`  
INPUT_WORKSPACE_SHA256: `211e6bc628ac2a4e85d31399d79fb7d4297e304cf06937c8c48a124c262591a8`  
ROOT_CAUSE_CLASSIFICATION: `ADDON_SOURCE_FAILURE`

## Runtime evidence

Windows activation failed during XML Search View validation:

`odoo.tools.convert.ParseError`

Failing view:

`onehr_discipline.view_onehr_discipline_case_search`

Failing filter:

`[('repeat_offense', '=', True)]`

Odoo error:

`Unsearchable field "repeat_offense" in path "repeat_offense"`

## Proven root cause

The latest supplied `onehr.discipline.case` source defines:

- `repeat_offense` as a computed, non-stored Boolean;
- compute method `_compute_prior_case_count`;
- no ORM `search=` method.

The Search View nevertheless uses `repeat_offense` in a domain.

That source/view contract is invalid: a non-stored computed field used in a Search
View domain must provide an explicit search implementation.

## Bounded correction

Version: `19.0.1.0.0` → `19.0.1.0.1`

`models/discipline_case.py`:
- preserves `repeat_offense` as non-stored;
- adds `search="_search_repeat_offense"`;
- adds `_search_repeat_offense(operator, value)`;
- translates the dynamic business meaning to an ID domain while respecting normal
  ORM record rules;
- supports Boolean `=` / `!=` semantics;
- preserves the original strict prior-case rule:
  same company + same employee + prior **closed** case with `reported_at` strictly
  earlier than the current case.

The field is deliberately **not** changed to `store=True`, because its value depends
on sibling case history. A stored value could become stale when another case is
closed or its relevant chronology changes.

## Regression prevention

`tools/source_acceptance.py` now fails if the Repeat Offense Search filter exists
without both:
- `search="_search_repeat_offense"` on the computed field; and
- the Python search method.

Runtime test inventory increases from 48 to 50:
- Repeat Offense search `= True`;
- Repeat Offense search `= False`.

## Preservation evidence

No model, field, workflow, security role, ACL, record rule, approval ownership,
sanction capability, report, integration contract, hard dependency, or sibling
OneHR addon is removed/moved/weakened.

FILES INTENTIONALLY CHANGED:
- `__manifest__.py`
- `models/discipline_case.py`
- `tests/test_case_governance.py`
- `tools/source_acceptance.py`
- bounded-repair evidence/status documents
- regenerated source acceptance/fingerprint/package evidence

SIBLING_SOURCE_MUTATION: NONE

## Retry hard gate

This is Runtime Repair Attempt 1/2 for the current Discipline activation task.

If a new activation failure appears after deploying this exact package:
- capture the FIRST complete traceback;
- classify the new root cause before any source mutation;
- Attempt 2 is permitted only for a distinct or incompletely addressed defect
  inside the approved `onehr_discipline` scope.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST_AFTER_ATTEMPT_1`

`ONEHR_DISCIPLINE_MOVE_FORWARD_READY: NO`

