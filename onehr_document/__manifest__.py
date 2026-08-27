{
    "name": "OneHR Document",
    "summary": "Enterprise HR document governance, versioning, expiry and e-sign evidence",
    "description": """
OneHR Document provides governed employee and business HR documents for Odoo 19
Community Edition. It centralizes document metadata, immutable document versions,
effective-dated templates, controlled generation, expiry/reminder governance and
e-sign transaction evidence while keeping binary content on Odoo attachments.
""",
    "author": "OneHR",
    "website": "https://github.com/onehr",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_corehr", "onehr_security", "mail"],
    "data": [
        "security/onehr_document_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_document_rules.xml",
        "data/document_sequence_data.xml",
        "data/document_cron_data.xml",
        "views/category_views.xml",
        "views/document_views.xml",
        "views/template_views.xml",
        "views/esign_views.xml",
        "views/wizard_views.xml",
        "report/document_version_report.xml",
        "views/menus.xml"
    ],
    "installable": True,
    "application": False,
}
