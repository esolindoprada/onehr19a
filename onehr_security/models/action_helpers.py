
"""Small readable action/security helpers for OneHR Security."""

from odoo import _
from odoo.exceptions import AccessError


SECURITY_MANAGER_GROUP = "onehr_security.group_onehr_security_manager"
SECURITY_ADMIN_GROUP = "onehr_security.group_onehr_security_admin"
COMPLIANCE_GROUP = "onehr_security.group_onehr_compliance_officer"


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
        "target": "current",
    }


def open_record_action(*, name, res_model, res_id):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
        "target": "current",
    }


def require_security_manager(env):
    """Server-side guard for access-provisioning actions.

    UI groups are usability only. This check is intentionally repeated in
    privileged object methods so RPC/manual invocation cannot bypass policy.
    """
    user = env.user
    if not (
        user.has_group(SECURITY_MANAGER_GROUP)
        or user.has_group(SECURITY_ADMIN_GROUP)
    ):
        raise AccessError(_("Only a OneHR Security Manager or Admin may perform this action."))


def require_security_admin_or_compliance(env):
    user = env.user
    if not (
        user.has_group(SECURITY_ADMIN_GROUP)
        or user.has_group(COMPLIANCE_GROUP)
    ):
        raise AccessError(_("Only OneHR Security Admin or Compliance may perform this action."))
