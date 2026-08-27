{
    "name": "OneHR Career & Succession",
    "summary": "Enterprise competency, talent pool, readiness and succession planning",
    "description": '''
Career and succession management for OneHR NEW on Odoo 19 Community Edition:
competency dictionary, position competency requirements, high-potential talent pools,
readiness/gap analysis, critical-position succession plans and governed soft integrations.
''',
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Talent",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "onehr_base",
        "onehr_corehr",
    ],
    "data": [
        "security/onehr_career_succession_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_career_succession_rules.xml",
        "data/sequence_data.xml",
        "data/cron_data.xml",
        "views/competency_views.xml",
        "views/position_competency_views.xml",
        "views/talent_pool_views.xml",
        "views/succession_plan_views.xml",
        "report/career_succession_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
