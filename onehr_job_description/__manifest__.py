{
    "name": "OneHR Job Description",
    "summary": "Enterprise position Job Description governance, versioning, KPI, competency and HSE",
    "description": '''
Enterprise Job Description governance for OneHR NEW on Odoo 19 Community Edition:
position JD dictionary, job-family templates, governed version history, KPI and
competency snapshots, HSE risk content, publication, comparison and downstream
Recruitment/Appraisal/Portal integration services.
''',
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "onehr_base",
        "onehr_security",
    ],
    "data": [
        "security/onehr_job_description_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_job_description_rules.xml",
        "data/sequence_data.xml",
        "data/cron_data.xml",
        "views/jd_views.xml",
        "views/jd_version_views.xml",
        "report/job_description_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
