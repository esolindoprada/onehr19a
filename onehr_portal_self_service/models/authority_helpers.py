
from odoo import _
from odoo.exceptions import AccessError

GROUP_EMPLOYEE = "onehr_portal_self_service.group_onehr_portal_employee"
GROUP_MANAGER = "onehr_portal_self_service.group_onehr_portal_manager"
GROUP_HR = "onehr_portal_self_service.group_onehr_portal_hr"
GROUP_ADMIN = "onehr_portal_self_service.group_onehr_portal_admin"


def is_portal_employee(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_EMPLOYEE))


def is_portal_manager(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_MANAGER))


def is_portal_hr(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_HR))


def is_portal_admin(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_ADMIN))


def require_portal_hr(recordset):
    if not is_portal_hr(recordset.env):
        raise AccessError(_("This action requires OneHR Portal HR authority."))


def require_portal_admin(recordset):
    if not is_portal_admin(recordset.env):
        raise AccessError(_("This action requires OneHR Portal Administrator authority."))


def display_notification(message, *, title="OneHR Portal Self-Service", notification_type="success", sticky=False):
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


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
    }

