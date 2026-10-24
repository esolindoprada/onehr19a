{
    "name": "OneHR Retirement & Offboarding",
    "summary": "Enterprise retirement, resignation, clearance, exit interview, access revocation and final-benefit orchestration",
    "description": """
OneHR Retirement & Offboarding is the enterprise exit-orchestration layer for OneHR NEW
on Odoo 19 Community Edition. It coordinates resignation, retirement and other approved
exit cases across HR, line management, IT, Finance, Security and the employee while
preserving canonical ownership in Core HR, Employment Contract, Workflow Approval,
Payroll, Document, Portal, Analytics and Integration API addons.

The addon owns offboarding cases, generated clearance tasks, clearance-item catalogue
and exit-interview evidence. It does not create a parallel employee, contract, payroll,
document, branch, portal or API master. Optional sibling capabilities are resolved through
bounded runtime service contracts and never through business sudo bypasses.
""",
    "author": "OneHR",
    "website": "https://github.com/onehr",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_corehr", "onehr_security", "onehr_workflow_approval"],
    "data": [
        "security/onehr_offboarding_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_offboarding_rules.xml",
        "data/offboarding_sequence.xml",
        "data/offboarding_cron.xml",
        "views/clearance_item_views.xml",
        "views/offboarding_checklist_views.xml",
        "views/exit_interview_views.xml",
        "views/offboarding_views.xml",
        "views/hr_employee_views.xml",
        "report/offboarding_reports.xml",
        "report/offboarding_report_templates.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
