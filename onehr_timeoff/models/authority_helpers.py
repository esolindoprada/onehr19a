from odoo import _
from odoo.exceptions import AccessError


def require_timeoff_user(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group("onehr_timeoff.group_onehr_timeoff_user"):
        raise AccessError(_("OneHR Time Off User authority is required."))
    return True


def require_timeoff_manager(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group("onehr_timeoff.group_onehr_timeoff_manager"):
        raise AccessError(_("OneHR Time Off Manager authority is required."))
    return True


def require_timeoff_hr(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group("onehr_timeoff.group_onehr_timeoff_hr"):
        raise AccessError(_("OneHR Time Off HR authority is required."))
    return True
