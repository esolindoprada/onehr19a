# OneHR Appraisal — Full Structural Inventory

## Persistent business models — exactly three

1. `onehr.appraisal.cycle`
   - annual/biannual/quarterly/custom cycle schedule
   - rating scale and rater mix
   - Objective/KPI templates using the approved score model
   - form generation, KPI CSV import, result CSV export
   - cycle completion/rating metrics and consolidation/closure

2. `onehr.appraisal.form`
   - employee appraisal transaction
   - Draft → In Review → Consolidation → Closed lifecycle
   - self/manager/peer progress, narratives, final calibration and acknowledgement
   - downstream KPI/career/portal result contracts

3. `onehr.appraisal.score`
   - target, multi-rater rating, feedback and development action in one governed model
   - parent/child target-to-rater structure
   - target/actual/achievement and normalized/weighted rating
   - soft Learning hand-off by explicit session reference

## Shared/native ownership used, not duplicated
- `hr.employee`: worker and manager.
- `hr.department`, `hr.job`, `res.company`: organization context.
- `ir.attachment`, chatter/activity: evidence/collaboration.

## Intentionally not created
- tutorial `onehr_appraisal.onehr_appraisal`
- separate objective/KPI/reviewer/rating-scale/IDP canonical table
- competency/talent/succession master
- Learning course/session/enrollment duplicate
- Analytics dashboard/snapshot table
- public API/token/webhook table

## Hard dependencies
Exactly:
- onehr_corehr
- onehr_security

## Soft/downstream integrations
- onehr_learning
- onehr_analytics
- onehr_career_succession
- onehr_discipline
- onehr_portal_self_service
- onehr_integrations_api
- onehr_multicompany_branch

No sibling OneHR source is modified by this build.
