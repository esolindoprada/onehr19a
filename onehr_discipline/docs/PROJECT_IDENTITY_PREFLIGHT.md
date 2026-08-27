# OneHR Discipline — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_discipline`  
TARGET: Odoo 19 Community Edition  
DELIVERY: Direct Full Addon Build  
WRITE_SCOPE: `onehr_discipline` only

LATEST_WORKSPACE: `onehr19a(20260824-093230).md`  
LATEST_WORKSPACE_SHA256: `211e6bc628ac2a4e85d31399d79fb7d4297e304cf06937c8c48a124c262591a8`

## Latest supplied target baseline
The target contains 11 scaffold files: generic `0.1` manifest, `base`-only
dependency, commented tutorial controller/model, generic demo/views/templates
and generic full-CRUD tutorial ACL. No accepted Discipline business runtime
implementation exists to preserve.

The supplied Apps description preserves richer domain intent: violation
classification, case pipeline, investigation, hearing, sanctions, appeals,
letters/notifications, SLA/reminders, privacy and audit.

## Authoritative product contract
The approved 25-addon specification defines:
- persistent models exactly `onehr.discipline.case` and
  `onehr.discipline.sanction`;
- hard dependencies exactly `onehr_corehr`, `onehr_security`,
  `onehr_workflow_approval`;
- soft dependencies `onehr_document`, `onehr_payroll_bridge`;
- workflow Reported → Under Investigation → Hearing → Decision → Closed;
- strict HR Legal/IR security;
- outcome/lead-time reporting, violation classification/weight, investigation SLA,
  repeat-offense rate and average resolution time;
- optional discipline-statistics API;
- multi-company/branch readiness and audit/retention expectations.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING

## Current runtime-repair baseline

The latest uploaded workspace contains the accepted Direct Full Discipline source
at version `19.0.1.0.0`. Its supplied `SOURCE_FINGERPRINT_SHA256.txt` matches all
43 fingerprinted files reconstructed for this repair.

The first Windows activation traceback proves one source/view contract defect:
the Search View filters on computed `repeat_offense`, while that field has no
ORM search method.

CURRENT_RUNTIME_REPAIR_ATTEMPT: 1/2  
ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE  
REPAIR_VERSION: 19.0.1.0.1
