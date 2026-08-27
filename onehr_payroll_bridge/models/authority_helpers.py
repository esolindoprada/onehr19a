from odoo import _
from odoo.exceptions import AccessError


PAYROLL_OFFICER_GROUP = "onehr_payroll_bridge.group_onehr_payroll_officer"
PAYROLL_MANAGER_GROUP = "onehr_payroll_bridge.group_onehr_payroll_manager"


def require_payroll_officer(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group(PAYROLL_OFFICER_GROUP):
        raise AccessError(_("OneHR Payroll Officer authority is required."))
    return True


def require_payroll_manager(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if getattr(env, "su", False):
        return True
    if not env.user.has_group(PAYROLL_MANAGER_GROUP):
        raise AccessError(_("OneHR Payroll Manager authority is required."))
    return True
