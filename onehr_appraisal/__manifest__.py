{
    "name": "OneHR Appraisal",
    "summary": "Enterprise OKR/KPI appraisal cycles, multi-rater scoring and development planning",
    "description": """
Enterprise performance management for OneHR NEW on Odoo 19 Community Edition:
appraisal cycles, weighted objectives/KPIs, self/manager/peer review, consolidation,
rating distribution, acknowledgement, development planning and governed soft integration.
""",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Performance",
    "version": "19.0.1.0.1",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
    ],
    "data": [
        "security/onehr_appraisal_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_appraisal_rules.xml",
        "data/sequence_data.xml",
        "data/cron_data.xml",
        "views/cycle_views.xml",
        "views/form_views.xml",
        "views/score_views.xml",
        "report/appraisal_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
