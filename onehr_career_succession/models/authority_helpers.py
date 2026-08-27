from odoo import _
from odoo.exceptions import AccessError

GROUP_HRBP = "onehr_career_succession.group_onehr_career_hrbp"
GROUP_TALENT_MANAGER = "onehr_career_succession.group_onehr_talent_manager"


def is_hrbp(env):
    return env.user.has_group(GROUP_HRBP)


def is_talent_manager(env):
    return env.user.has_group(GROUP_TALENT_MANAGER)


def require_hrbp(recordset):
    if not is_hrbp(recordset.env):
        raise AccessError(_("This action requires Career & Succession HRBP authority."))


def require_talent_manager(recordset):
    if not is_talent_manager(recordset.env):
        raise AccessError(_("This action requires Talent Manager authority."))


def display_notification(
    message,
    *,
    title="OneHR Career & Succession",
    notification_type="success",
):
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": title,
            "message": message,
            "type": notification_type,
            "sticky": False,
        },
    }
