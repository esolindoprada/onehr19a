# onehr_document — Master Model Registry Alignment

| # | Model | Class | ED | Implementation responsibility |
|---:|---|---|---|---|
| 1 | `onehr.document.category` | NEW persistent | ED1 | Classification, sensitivity, employee visibility, validity/reminder/grace/retention defaults |
| 2 | `onehr.document` | NEW persistent | ED2 | Logical HR document header linked to employee/business source; canonical document identity |
| 3 | `onehr.document.version` | NEW persistent | ED2 | Issued/uploaded immutable version, attachment-backed binary, validity/expiry/signature state |
| 4 | `onehr.document.template` | NEW persistent | ED2 | Effective-dated document/letter template master |
| 5 | `onehr.document.template.version` | NEW persistent | ED2 | Immutable template version and bounded variable contract |
| 6 | `onehr.esign.transaction` | NEW persistent | ED3 | Append-oriented provider transaction/status/correlation evidence; no credentials |
| 7 | `wizard.document.generate` | NEW TransientModel | ED0 | Controlled template-to-document/version generation |
| 8 | `wizard.document.publish.sign` | NEW TransientModel | ED0 | Controlled e-sign request creation |

## Canonical ownership

- `hr.employee` remains canonical worker identity through `onehr_corehr`.
- `onehr.document` / `onehr.document.version` are canonical HR document facts.
- Binary content is represented through Odoo `ir.attachment` via an
  attachment-backed Binary field on `onehr.document.version`.
- Other OneHR domains reference document/version IDs; they do not copy binary
  payloads into domain-specific tables.
- Approval decision evidence remains owned by `onehr_workflow_approval`.
- Branch master/scope remains owned by `onehr_multicompany_branch`.
- External provider credentials/connectors remain outside this addon and may be
  supplied by the soft `onehr_integrations_api` layer.

## Approved dependency contract

Hard dependencies, exactly:

`onehr_corehr, onehr_security, mail`

Soft integration:

`onehr_integrations_api`

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING
