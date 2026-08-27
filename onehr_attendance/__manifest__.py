{
    "name": "OneHR Attendance",
    "summary": "Enterprise shifts, attendance reconciliation, exceptions, imports and native Odoo overtime integration",
    "description": """
OneHR Attendance extends Odoo 19 Community hr.attendance as the canonical attendance
transaction. It adds effective-dated shift definitions, reusable rotation patterns,
employee shift schedules, governed attendance exceptions, device/fingerprint import
staging, reconciliation, professional operational UI, and policy metadata on Odoo's
native overtime models without rebuilding the native overtime engine.
""",
    "version": "19.0.1.0.2",
    "category": "Human Resources/Attendances",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "hr_attendance",
    ],
    "data": [
        "security/onehr_attendance_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_attendance_rules.xml",
        "data/attendance_sequence_data.xml",
        "data/attendance_cron_data.xml",
        "views/shift_views.xml",
        "views/attendance_views.xml",
        "views/exception_views.xml",
        "views/reconciliation_views.xml",
        "views/native_overtime_views.xml",
        "reports/attendance_reports.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
