
{
    "name": "OneHR Assignment",
    "summary": "Enterprise employee placement, movement, position occupancy, workforce planning and assignment costing",
    "description": """
OneHR Assignment owns enterprise employee placement history, primary and secondary
assignments, governed mass movement, position occupancy, assignment-level costing,
workforce planning and position budgets while synchronizing approved primary placement
to Odoo 19 native hr.version employment facts.
""",
    "version": "19.0.1.0.1",
    "category": "Human Resources/Employees",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_base",
        "onehr_corehr",
        "onehr_security",
        "onehr_workflow_approval",
    ],
    "data": [
        "security/onehr_assignment_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_assignment_rules.xml",
        "data/assignment_sequence_data.xml",
        "data/assignment_cron_data.xml",
        "views/assignment_views.xml",
        "views/movement_views.xml",
        "views/workforce_views.xml",
        "views/native_extension_views.xml",
        "reports/assignment_history_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}

