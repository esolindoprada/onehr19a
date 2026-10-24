
from odoo import _
from odoo.exceptions import AccessError

GROUP_VIEWER = "onehr_demo.group_onehr_demo_viewer"
GROUP_OPERATOR = "onehr_demo.group_onehr_demo_operator"
GROUP_ADMIN = "onehr_demo.group_onehr_demo_admin"

def is_demo_admin(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_ADMIN))

def require_demo_admin(env):
    if not is_demo_admin(env):
        raise AccessError(_("This action requires OneHR Demo Administrator authority."))
    return True

def require_system_demo_admin(env):
    require_demo_admin(env)
    if not (env.is_superuser() or env.user.has_group("base.group_system")):
        raise AccessError(_("This high-impact demo operation also requires Odoo System Administrator authority."))
    return True

