
from odoo import _
from odoo.exceptions import AccessError


def require_assignment_officer(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not env.user.has_group("onehr_assignment.group_onehr_assignment_officer"):
        raise AccessError(_("OneHR Assignment Officer authority is required."))
    return True


def require_assignment_manager(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not env.user.has_group("onehr_assignment.group_onehr_assignment_manager"):
        raise AccessError(_("OneHR Assignment Manager authority is required."))
    return True


def require_assignment_proposer(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not env.user.has_group("onehr_assignment.group_onehr_assignment_proposer"):
        raise AccessError(_("OneHR Assignment Proposer authority is required."))
    return True
