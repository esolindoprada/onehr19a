from odoo import _
from odoo.exceptions import AccessError

GROUP_API_USER = "onehr_integrations_api.group_onehr_api_user"
GROUP_API_ADMIN = "onehr_integrations_api.group_onehr_api_admin"


def is_api_user(env):
    return env.user.has_group(GROUP_API_USER)


def is_api_admin(env):
    return env.user.has_group(GROUP_API_ADMIN)


def require_api_admin(recordset):
    if not is_api_admin(recordset.env):
        raise AccessError(_("This operation requires OneHR API Administrator authority."))


def display_notification(message, *, title="OneHR Integrations API", notification_type="success", sticky=False):
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": title,
            "message": message,
            "type": notification_type,
            "sticky": sticky,
        },
    }
