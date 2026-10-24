
{
    "name": "OneHR Security & Access Control",
    "summary": "Enterprise roles, effective access, SoD and immutable security audit for OneHR",
    "description": """
OneHR Security is the security and compliance foundation of OneHR on Odoo 19 CE.

It owns OneHR business roles, effective user-role assignments, segregation-of-
duties policy/evidence, structured high-risk security audit and the OneHR
security extension of Odoo users. Odoo res.users and res.groups remain canonical.
Branch scope is intentionally extension-ready without a reverse dependency on
onehr_multicompany_branch.
""",
    "author": "OneHR",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_base", "mail"],
    "data": [
        "security/onehr_security_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_security_rules.xml",
        "data/security_cron.xml",
        "views/role_views.xml",
        "views/user_role_views.xml",
        "views/sod_views.xml",
        "views/audit_views.xml",
        "views/res_users_views.xml",
        "views/menus.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
}
