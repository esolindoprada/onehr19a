from odoo import _
from odoo.exceptions import AccessError


GROUP_OFFICER = "onehr_learning.group_onehr_learning_officer"
GROUP_TRAINER = "onehr_learning.group_onehr_learning_trainer"
GROUP_MANAGER = "onehr_learning.group_onehr_learning_manager_approver"


def is_learning_manager(env):
    return bool(getattr(env, "su", False) or env.user.has_group(GROUP_MANAGER))


def is_learning_officer(env):
    return bool(is_learning_manager(env) or env.user.has_group(GROUP_OFFICER))


def is_learning_trainer(env):
    return bool(is_learning_manager(env) or env.user.has_group(GROUP_TRAINER))


def require_learning_officer(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not is_learning_officer(env):
        raise AccessError(_("OneHR L&D Officer authority is required."))
    return True


def require_learning_manager(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not is_learning_manager(env):
        raise AccessError(_("OneHR Learning Manager Approver authority is required."))
    return True


def require_learning_trainer_or_officer(record_or_env):
    env = getattr(record_or_env, "env", record_or_env)
    if not (is_learning_officer(env) or is_learning_trainer(env)):
        raise AccessError(_("OneHR Trainer or L&D Officer authority is required."))
    return True
