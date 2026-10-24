
# OneHR Discipline Management

Enterprise employee-relations discipline management for OneHR NEW on Odoo 19 CE.

Authoritative persistent business models are exactly:

- `onehr.discipline.case`
- `onehr.discipline.sanction`

The richer legacy scaffold intent is preserved without inventing extra persistent
models. Violation classification, pipeline/SLA, investigation, hearing and appeal
are structured domains of `onehr.discipline.case`; sanction/decision execution is
owned by `onehr.discipline.sanction`.

Hard dependencies are exactly:

- `onehr_corehr`
- `onehr_security`
- `onehr_workflow_approval`

Soft integrations remain runtime/downstream contracts:
OneHR Document, Payroll Bridge, Employment Contract, Appraisal, PnP,
Multi-company Branch, Analytics and Integrations API.

Main case workflow:
Reported → Under Investigation → Hearing → Decision → Closed.

Sanction workflow:
Draft → Approval → Approved → Executed, with Rejected/Cancelled exception states.

Source/static acceptance is not runtime completeness. See
`docs/WINDOWS_RUNTIME_ACCEPTANCE.md`.

