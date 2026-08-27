{
    "name": "OneHR Workflow & Approval Engine",
    "summary": "Enterprise matrix approval, delegation, SLA escalation and immutable decision evidence",
    "description": """
OneHR Workflow & Approval Engine is the generic approval orchestration layer for
OneHR on Odoo 19 Community Edition.

It owns approval configuration and approval evidence while each source addon
remains owner of its business state and execution. Routing is structured and safe:
no stored executable Python expressions, no reverse dependency to HR transaction
owners, and no approval-engine bypass around source-domain authorization.
""",
    "author": "OneHR",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_security", "mail"],
    "data": [
        "security/onehr_workflow_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_workflow_rules.xml",
        "data/approval_sequence.xml",
        "data/approval_cron.xml",
        "views/approval_rule_views.xml",
        "views/approval_request_views.xml",
        "views/delegation_views.xml",
        "views/reporting_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
