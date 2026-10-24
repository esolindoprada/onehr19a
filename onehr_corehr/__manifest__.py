
{
    "name": "OneHR Core HR",
    "summary": "Native-first employee master, family, identifiers, history and restricted occupational health",
    "description": """
OneHR Core HR extends Odoo 19 canonical hr.employee, hr.employee.public and
hr.version. It owns effective-dated family/emergency/identifier/education/
external-employment records, engagement classification, and isolated
occupational-health records. Personal document storage belongs to onehr_document.
""",
    "author": "OneHR",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_base", "onehr_security", "hr"],
    "data": [
        "security/onehr_corehr_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_corehr_rules.xml",
        "data/sequence_data.xml",
        "views/engagement_views.xml",
        "views/relationship_views.xml",
        "views/identifier_views.xml",
        "views/qualification_views.xml",
        "views/occupational_health_views.xml",
        "views/employee_views.xml",
        "views/settings_views.xml",
        "report/employee_profile_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
