# OneHR Appraisal — Scope Isolation Report

TASK: Runtime activation repair  
ATTEMPT: 2/2  
WRITE_SCOPE: `onehr_appraisal` only  
LATEST_WORKSPACE_DUMP: `onehr19a(20260820-223313).md`  
LATEST_WORKSPACE_DUMP_SHA256: `a34865b4d9b965d1169dc7f4c7738898ec8089315679240b6add897d4fc1c971`

## Pre-repair fingerprint comparison

The latest supplied `docs/SOURCE_FINGERPRINT_SHA256.txt` was used as the baseline.

- Baseline files covered by fingerprint: 39
- Baseline files unchanged: 32
- Baseline files intentionally changed: 7
- Baseline files missing: 0

Intentionally changed baseline files:

- `__manifest__.py` — repair version `19.0.1.0.1`
- `models/cycle.py` — Odoo 19 `@api.depends` compatibility correction
- `tools/source_acceptance.py` — regression guard for `.id` dependency paths
- `docs/ENTERPRISE_COMPLETENESS_MATRIX.md` — runtime repair evidence
- `docs/IMPLEMENTATION_REPORT.md` — Attempt 2 evidence
- `docs/SOURCE_ACCEPTANCE_REPORT.txt` — regenerated source acceptance
- `docs/WINDOWS_RUNTIME_ACCEPTANCE.md` — Attempt 1 failure / Attempt 2 re-test note

New repair evidence files are permitted inside the target addon and do not alter model ownership.

No sibling OneHR addon source is emitted or modified by this package.

`SCOPE_ISOLATION_RESULT: PASS`
