from odoo import _
from odoo.exceptions import AccessError


def _require_group(recordset, xmlid, message):
    if recordset.env.su:
        return True
    if not recordset.env.user.has_group(xmlid):
        raise AccessError(_(message))
    return True


def require_task_owner(recordset):
    return _require_group(
        recordset,
        "onehr_retirement_offboarding.group_onehr_offboarding_task_owner",
        "Offboarding Task Owner authority is required.",
    )


def require_offboarding_officer(recordset):
    return _require_group(
        recordset,
        "onehr_retirement_offboarding.group_onehr_offboarding_officer",
        "Offboarding Officer authority is required.",
    )


def require_offboarding_manager(recordset):
    return _require_group(
        recordset,
        "onehr_retirement_offboarding.group_onehr_offboarding_manager",
        "Offboarding Manager authority is required.",
    )


def require_offboarding_admin(recordset):
    return _require_group(
        recordset,
        "onehr_retirement_offboarding.group_onehr_offboarding_admin",
        "Offboarding Administrator authority is required.",
    )


def require_system_admin(recordset):
    return _require_group(
        recordset,
        "base.group_system",
        "System Administrator authority is additionally required for Odoo access revocation.",
    )
