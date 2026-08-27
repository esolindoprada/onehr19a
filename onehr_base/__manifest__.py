{
    "name": "OneHR Base",
    "summary": "Enterprise HR foundation for organization, positions, grades, hierarchies and lifecycle checklists",
    "description": """
OneHR Base is the native-first enterprise HR foundation for Odoo 19 Community Edition.
It extends Odoo departments, jobs and work locations and provides governed positions,
grades, versioned position hierarchies, sequence rules, eligibility, lifecycle events
and history-safe operational checklists.
""",
    "author": "OneHR",
    "website": "https://github.com/onehr",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/onehr_security.xml",
        "data/lifecycle_event_type_data.xml",
        "views/native_views.xml",
        "views/organization_views.xml",
        "views/hierarchy_views.xml",
        "views/configuration_views.xml",
        "views/checklist_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
