
# OneHR Career & Succession — Full Structural Inventory

## Persistent business models — exactly four

### `onehr.competency`
Competency dictionary, category, level scale, behavioural anchors, evidence guidance,
company governance, usage navigation and native Odoo import compatibility.

### `onehr.position.competency`
Position-level competency requirement, required proficiency, optional weighting,
mandatory/evidence flags and target-position gap navigation.

### `onehr.talent.pool`
Employee talent-pool identity, high-potential classification, performance/potential/
competency/learning scoring, 9-box, readiness level, retention risk, career aspiration,
development needs and source-evidence references.

### `onehr.succession.plan`
Critical-position succession plan, incumbent, multiple successor candidates, primary
successor, coverage target, bench strength, average readiness, composite risk index,
strategy/mitigation and governed Draft → Proposed → Approved → Active lifecycle.

## Shared/native ownership — consumed, not duplicated
- `hr.employee`: worker identity.
- `onehr.position`: enterprise position.
- `hr.department`, `hr.job`, `res.company`: organizational context.
- `ir.attachment`, chatter/activity: collaboration/evidence.

## Deliberate non-invention
No extra persistent/transient model is created for:
- employee competency observation;
- competency assessment line;
- successor candidate line;
- career path stage;
- 9-box cell;
- talent scoring rule;
- talent configuration wizard;
- CSV import wizard;
- API token/webhook.

The exact product baseline authorizes four persistent models only. Detailed source
evidence is linked through soft Appraisal/Learning services; aggregate competency/readiness
facts remain on the approved Talent model.

## Dependencies
Hard exactly:
- `onehr_base`
- `onehr_corehr`

Soft:
- `onehr_appraisal`
- `onehr_learning`
- `onehr_analytics`
- downstream Portal / Integrations API / multicompany extension where installed.

