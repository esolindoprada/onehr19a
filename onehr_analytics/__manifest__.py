{
    "name": "OneHR Analytics & KPI Dashboards",
    "summary": "Enterprise HR KPI tiles, immutable snapshots, trends, thresholds and drill-through analytics",
    "description": """
OneHR Analytics is the enterprise analytics and KPI layer for OneHR NEW on Odoo 19
Community Edition. It owns KPI tile configuration, immutable periodic KPI snapshots,
threshold evidence, trend comparisons and executive drill-through while keeping
transaction ownership in the source OneHR addons.

The addon is intentionally soft-coupled to Recruitment, Attendance, Time Off,
Learning, Payroll, Appraisal, Career/Succession and Discipline. Optional providers
are resolved only when their models/services are installed, and source-domain access
remains authoritative. No public API endpoint, spreadsheet engine, payroll engine,
or branch master is duplicated here.
""",
    "author": "OneHR",
    "website": "https://github.com/onehr",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_security"],
    "data": [
        "security/onehr_analytics_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_analytics_rules.xml",
        "data/analytics_cron.xml",
        "views/analytics_tile_views.xml",
        "views/kpi_snapshot_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
