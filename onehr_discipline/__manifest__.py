{
    "name": "OneHR Discipline Management",
    "summary": "Enterprise employee discipline cases, investigations, hearings, sanctions, appeals and audit evidence",
    "description": '''
Enterprise Discipline Management for OneHR NEW on Odoo 19 Community Edition.

The addon governs confidential employee-relations cases from reported incident,
investigation and hearing through disciplinary decision, approved sanction,
appeal and closure. It integrates with canonical OneHR employee and approval
ownership while keeping Document, Payroll, Contract, Appraisal, Branch,
Analytics and API integrations soft and security-preserving.
''',
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Employee Relations",
    "version": "19.0.1.0.1",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "onehr_workflow_approval",
    ],
    "data": [
        "security/onehr_discipline_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_discipline_rules.xml",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "views/discipline_case_views.xml",
        "views/discipline_sanction_views.xml",
        "views/settings_views.xml",
        "report/discipline_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
