# OneHR Appraisal — Project Identity Preflight

PROJECT: OneHR NEW
ADDON: onehr_appraisal
TARGET: Odoo 19 Community Edition
DELIVERY: Direct Full Addon Build

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- OneHR 25 Addons Specification for Odoo 19 CE.
- Root OneHR Enterprise Development Guardrail.
- Latest user-supplied OneHR workspace.
- Odoo 19 CE native ownership.
- Oracle HRMS Performance Management concepts only as a compatible functional benchmark.

CURRENT SUPPLIED BASELINE:
- Generic tutorial scaffold.
- Manifest version 0.1.
- Hard dependency only base.
- Commented public tutorial controller/model examples.
- No approved Appraisal business implementation.

APPRAISAL PRODUCT CONTRACT:
- Core models exactly onehr.appraisal.cycle, onehr.appraisal.form, onehr.appraisal.score.
- Hard dependencies exactly onehr_corehr and onehr_security.
- Soft dependencies onehr_learning and onehr_analytics.
- Workflow Draft → In Review → Consolidation → Closed.
- Multi-rater self/manager/peer; OKR/KPI targets; rating scale/weights; IDP to Learning.
- Result/rating distribution, KPI analytics and target CSV import.

OWNERSHIP:
- hr.employee remains canonical worker.
- Competency/talent/succession masters remain onehr_career_succession ownership.
- Learning session/enrollment remains onehr_learning ownership.
- Dashboard/snapshot tables remain onehr_analytics ownership.
- Public REST/authentication remains onehr_integrations_api ownership.

ALLOWED CHANGE:
Replace the generic scaffold completely with this approved enterprise implementation.

FORBIDDEN CHANGE:
Extra canonical Appraisal business tables, extra hard dependency, public endpoint,
worker/competency/learning/talent duplicate, sibling edit, broad base.group_user CRUD,
business sudo, legacy _sql_constraints or architecture drift.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD
ROOT_CAUSE_CLASSIFICATION_FOR_REBUILD: ADDON_SOURCE_FAILURE
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
