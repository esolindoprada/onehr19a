{
    "name": "OneHR Employment Contract",
    "summary": "Enterprise employment-contract governance on Odoo 19 native HR versions",
    "description": """
OneHR Employment Contract governs legal employment-contract templates, approval,
activation, renewal, probation visibility, expiry reminders, termination approval,
clearance checklists and document-generation hooks while keeping Odoo hr.version
as the canonical store for employment dates and wage facts.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Contracts",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "onehr_workflow_approval",
    ],
    "data": [
        "security/onehr_contract_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_contract_rules.xml",
        "data/contract_sequence_data.xml",
        "data/contract_cron_data.xml",
        "views/contract_template_views.xml",
        "views/contract_views.xml",
        "views/reporting_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
