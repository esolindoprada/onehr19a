# -*- coding: utf-8 -*-
{
    "name": "OneHR Multicompany & Branch",
    "summary": "Enterprise branch master, branch-scoped access and OneHR security integration",
    "description": """
OneHR Multicompany & Branch provides the operational branch layer inside Odoo
legal companies without replacing res.company. It owns the effective-dated
onehr.branch master, reusable onehr.mixin.branch scope helpers, allowed/default
branch preferences on Odoo users, company branch configuration, and branch-aware
OneHR role assignments.

The addon preserves Odoo company security as the top partition, integrates with
the branch-extension hooks deliberately exposed by onehr_security, and keeps
OneHR role-to-group reconciliation branch-aware without granting broader raw Odoo
security authority.
""",
    "author": "OneHR",
    "category": "Human Resources",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["onehr_security"],
    "data": [
        "security/onehr_branch_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_branch_rules.xml",
        "views/branch_views.xml",
        "views/res_company_views.xml",
        "views/res_users_views.xml",
        "views/user_role_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
