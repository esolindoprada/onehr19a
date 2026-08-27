{
    "name": "OneHR Payroll Bridge",
    "summary": "Enterprise payroll interchange, work-variable export, vendor payslip import, reconciliation and costing payload bridge",
    "description": '''
OneHR Payroll Bridge is the governed interchange boundary between OneHR and external
or OCA payroll engines. It prepares payroll-variable export batches, imports payroll
results, preserves immutable reconciliation evidence, and exposes downstream costing
payloads without taking ownership of payroll calculation, tax localization, accounting,
or external API credentials.
''',
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
    ],
    "data": [
        "security/onehr_payroll_bridge_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_payroll_bridge_rules.xml",
        "data/payroll_sequence_data.xml",
        "data/payroll_cron_data.xml",
        "views/config_views.xml",
        "views/export_views.xml",
        "views/import_views.xml",
        "reports/payroll_reconciliation_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
