{
    "name": "OneHR Time Off",
    "summary": "Enterprise leave, accrual, carry-over, team calendar and governed absence approvals",
    "description": """
OneHR Time Off provides enterprise leave types, effective leave policies, governed
leave requests, entitlement allocations, automatic accrual, carry-over, team-calendar
conflict control, balance analytics and workflow-approval integration for Odoo 19 CE.

The addon intentionally owns only the three Time Off persistent models explicitly
identified by the approved OneHR product baseline. Attendance and Payroll remain
soft/downstream integrations so model ownership and dependency direction stay clean.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Time Off",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "onehr_attendance",
        "onehr_workflow_approval",
    ],
    "data": [
        "security/onehr_timeoff_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_timeoff_rules.xml",
        "data/timeoff_sequence_data.xml",
        "data/timeoff_cron_data.xml",
        "views/leave_type_views.xml",
        "views/leave_request_views.xml",
        "views/leave_allocation_views.xml",
        "views/native_extension_views.xml",
        "reports/leave_request_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
