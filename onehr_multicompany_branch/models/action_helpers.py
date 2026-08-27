# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import AccessError


BRANCH_ADMIN_GROUP = "onehr_multicompany_branch.group_onehr_branch_admin"


def require_branch_admin(env):
    """Enforce branch-master/scope administration on the server side.

    View groups improve usability but are never treated as authorization.  Any
    method that changes branch master data or another user's branch scope calls
    this helper before mutation.
    """
    if not env.user.has_group(BRANCH_ADMIN_GROUP) and not env.user.has_group("base.group_system"):
        raise AccessError(_("OneHR Branch Admin permission is required for this operation."))
    return True


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    """Build a conventional Odoo window action without embedding UI logic in models."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
    }


def open_record_action(*, name, res_model, res_id):
    """Open one record using a small reusable, human-readable action contract."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": "form",
        "res_id": res_id,
        "target": "current",
    }
