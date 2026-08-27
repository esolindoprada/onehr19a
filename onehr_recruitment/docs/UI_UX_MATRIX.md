# OneHR Recruitment — UI/UX Matrix

| Model | List | Form | Search | Enterprise interaction |
|---|---:|---:|---:|---|
| `onehr.recruitment.requisition` | Yes | Yes | Yes | statusbar; approval/start/fill/cancel header actions; approval/applicant/interview/offer/position smart buttons; body actions; applicant row drill-down |
| `onehr.interview.template` | Yes | Yes | Yes | version statusbar; activate/retire/new-version actions; session smart button; structured PropertiesDefinition criteria |
| `onehr.interview.session` | Yes | Yes | Yes | statusbar; confirm/calendar/score/complete/no-show/cancel; applicant/score/calendar smart buttons; body actions; score row actions; calendar view |
| `onehr.interview.score` | Yes | Yes | Yes | draft/final/superseded statusbar; finalize/correction actions; session smart button; structured scorecard |
| `onehr.offer` | Yes | Yes | Yes | governed approval statusbar; submit/generate/send/accept/decline/withdraw/expire; approval/applicant/preboarding smart buttons; compensation privacy; body actions |
| `onehr.preboarding` | Yes | Yes | Yes | statusbar; ready/prepare/complete/cancel; applicant/employee/checklist smart buttons; checklist progress; body orchestration/scheduling actions |
| `onehr.recruitment.source.metric` | Yes | Yes (read-only evidence) | Yes | immutable ribbon; list/pivot/graph reporting; generated from controlled Job action |
| `hr.applicant` | inherited | inherited | inherited | OneHR requisition, latest-offer badge, interview/offer/preboarding smart buttons and hiring-governance page |
| `hr.recruitment.stage` | inherited | inherited | native | OneHR phase, SLA and transition-policy metadata |
| `hr.job` | inherited | inherited | inherited | requisition smart button and 30-day source-snapshot body action |
| `hr.talent.pool` | inherited | inherited | native | target-job and governance-review fields |

UI security principle: visibility is usability only. ACL, record rules and Python authority guards are authoritative. Hiding a button never grants or removes business authority.

UI_UX_MATRIX_RESULT: PASS_SOURCE
