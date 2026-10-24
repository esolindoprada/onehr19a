
{
    "name": "OneHR Portal Self-Service",
    "summary": "Enterprise employee and manager self-service requests, approvals, SLA and portal integration",
    "description": """
OneHR Portal Self-Service for Odoo 19 Community Edition provides My HR and My Team
self-service, governed HR requests, manager/HR approvals, SLA monitoring, profile-change
workflow, portal collaboration and security-preserving soft integrations with the wider
OneHR suite.
""",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Self Service",
    "version": "19.0.1.0.2",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "portal",
        "web",
        "mail",
    ],
    "data": [
        "security/onehr_portal_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_portal_rules.xml",
        "data/sequence_data.xml",
        "data/request_stage_data.xml",
        "data/request_type_data.xml",
        "data/cron_data.xml",
        "views/request_type_views.xml",
        "views/request_stage_views.xml",
        "views/request_views.xml",
        "views/employee_views.xml",
        "views/wizard_views.xml",
        "views/portal_templates.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

