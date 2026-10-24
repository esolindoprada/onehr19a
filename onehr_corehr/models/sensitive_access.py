
"""Small security-audit helpers; this is plain Python, not an Odoo model."""

from odoo import _


def log_sensitive_read(records, requested_fields, sensitive_fields, label):
    """Log only reads that request protected payload.

    Routine list reads normally contain operational metadata only and should not
    flood the audit ledger. Full-form reads or explicit protected-field reads
    create one aggregate event for the recordset.
    """
    if not records or records.env.su or records.env.context.get("onehr_skip_sensitive_read_audit"):
        return

    requested = set(requested_fields or [])
    if requested_fields is not None and not (requested & set(sensitive_fields)):
        return

    sample = records[:1]
    company = getattr(sample, "company_id", False) or records.env.company
    records.env["onehr.audit.log"]._log_event(
        action="access_read",
        summary=_("%s sensitive payload read", label),
        severity="high",
        record=sample,
        company=company,
        metadata={
            "model": records._name,
            "record_ids": records.ids,
            "record_count": len(records),
            "requested_sensitive_fields": sorted(
                set(sensitive_fields) if requested_fields is None
                else requested & set(sensitive_fields)
            ),
        },
    )


def log_sensitive_change(record, *, action, summary, severity="high", metadata=None):
    record.env["onehr.audit.log"]._log_event(
        action=action,
        summary=summary,
        severity=severity,
        record=record,
        company=record.company_id,
        metadata=metadata or {},
    )
