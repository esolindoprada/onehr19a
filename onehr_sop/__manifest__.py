
{
    "name": "OneHR SOP",
    "summary": "Enterprise SOP versioning, targeted publication, acknowledgement and compliance governance",
    "description": '''
Enterprise Standard Operating Procedure governance for OneHR NEW on Odoo 19 Community Edition:
controlled SOP versions, targeted unit/role publication, employee read-and-agree,
periodic review and retention, Document archive integration, compliance analytics,
audit export and downstream Portal/API service contracts.
''',
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "onehr_base",
        "onehr_security",
        "onehr_document",
    ],
    "data": [
        "security/onehr_sop_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_sop_rules.xml",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "views/sop_views.xml",
        "views/sop_version_views.xml",
        "views/sop_ack_views.xml",
        "report/sop_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

