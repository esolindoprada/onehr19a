# OneHR Employment Contract — Direct Full Addon Build v1

This is a coherent full-addon reconstruction, not an open-ended Codex patch loop.
The incoming generic scaffold has been replaced by an enterprise implementation
aligned to the approved OneHR architecture and 25-addon functional specification.

Key design decisions:
- Odoo 19 `hr.version` remains canonical for contract start/end, trial end and wage.
- OneHR legal wrapper stores workflow/evidence, not a competing employment master.
- Contract templates are versioned/effective-dated policy records.
- Contract and termination approvals use the existing OneHR approval engine.
- Renewal uses native Odoo contract-version creation.
- Termination updates the canonical native contract interval and requires governed
  clearance checklist allocation, while broader offboarding remains outside ownership.
- onehr_document is a genuine soft integration; contract-document generation and
  e-signature delegation preserve OneHR Document's own Document Manager authority.
- line managers receive controlled direct-report contract visibility without being
  granted private HR/version/configuration ACLs.
- no business `sudo()` is used in this addon.

SOURCE_DIRECT_FULL_BUILD: PASS
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_EMPLOYMENT_CONTRACT_MOVE_FORWARD_READY: NO
