{
    "name": "OneHR Policies & Procedures",
    "summary": "Enterprise policy governance, approval, publication, acknowledgement and compliance evidence",
    "description": '''
Enterprise Policies & Procedures governance for OneHR NEW on Odoo 19 Community Edition:
controlled policy versions, OneHR workflow approval, targeted publication,
employee acknowledgement, compliance evidence, periodic review, Document archive,
reporting and governed downstream Portal/Analytics/API integration contracts.
''',
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "onehr_security",
        "onehr_document",
        "onehr_workflow_approval",
    ],
    "data": [
        "security/onehr_pnp_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_pnp_rules.xml",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "views/policy_views.xml",
        "views/ack_views.xml",
        "views/evidence_views.xml",
        "views/settings_views.xml",
        "report/pnp_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
