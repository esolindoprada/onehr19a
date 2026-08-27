{
    "name": "OneHR Payroll Localization Indonesia",
    "summary": "Effective-dated Indonesian payroll parameters for PPh21, PTKP, BPJS and THR",
    "description": '''
Enterprise Indonesian payroll-localization parameter provider for OneHR.
It owns effective-dated statutory/configuration parameters and extends the
Payroll Bridge with frozen localization evidence. It does not own payslip
calculation, employee tax identity, accounting, payment execution, or API secrets.
''',
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_payroll_bridge",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/onehr_payroll_l10n_id_rules.xml",
        "views/parameter_views.xml",
        "views/payroll_bridge_views.xml",
        "reports/localization_parameter_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
