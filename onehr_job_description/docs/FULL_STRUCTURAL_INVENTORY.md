# OneHR Job Description — Full Structural Inventory

## Persistent business models — exactly two

### `onehr.jd`
JD master identity, position mapping, job-family template identity, company boundary,
review/approval routing, version navigation, current publication, position coverage,
version age and governance reminders.

### `onehr.jd.version`
Versioned JD content and lifecycle evidence:
purpose, responsibilities, accountabilities, KPI, competencies, qualifications,
education/experience/skills, decision rights, reporting relationships, working
conditions, HSE/K3 risk/controls/PPE, source document evidence, change control,
approval/publication timestamps and SHA-256 content fingerprint.

## Consumed canonical models — not duplicated
- `onehr.position`
- `onehr.job.family`
- `onehr.grade`
- `hr.job`
- `hr.department`
- `res.company`
- `res.users`
- `ir.attachment`
- `mail.activity`

## Deliberate non-invention
No new persistent/transient model for:
- JD responsibility line;
- JD KPI line;
- JD competency line;
- JD K3 risk line;
- JD template line;
- approval-matrix master;
- document-import wizard;
- portal publication;
- API credential/webhook;
- analytics snapshot.

Those concerns are represented inside the exact approved two-model contract or remain
owned by downstream modules.

## Dependency topology
Hard exactly:
- `onehr_base`
- `onehr_security`

Soft:
- Recruitment
- Appraisal
- Career/Succession
- Portal Self Service
- Integrations API / Analytics downstream consumers
