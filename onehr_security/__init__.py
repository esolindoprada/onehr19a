from odoo.fields import Command

from . import models


def uninstall_hook(env):
    """Remove OneHR-managed Odoo group memberships before uninstall.

    A group becomes OneHR-managed when at least one `onehr.role` maps to it.
    Because Odoo's direct user/group M2M does not record whether a membership
    originated manually or from OneHR, OneHR deliberately owns all direct
    memberships for mapped groups while installed. Groups never mapped by a
    OneHR role are preserved.
    """
    managed_groups = (
        env["onehr.role"]
        .with_context(active_test=False)
        .search([])
        .mapped("group_ids")
    )
    if not managed_groups:
        return

    users = env["res.users"].search([("group_ids", "in", managed_groups.ids)])
    unlink_commands = [Command.unlink(group_id) for group_id in managed_groups.ids]

    for user in users:
        user.write({"group_ids": unlink_commands})
