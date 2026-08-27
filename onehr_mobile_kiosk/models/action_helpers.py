from odoo import _


def display_notification(title, message, notification_type="success", sticky=False):
    """Return a small reusable Odoo client notification action."""
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


def open_records_action(name, res_model, domain=None, context=None, view_mode="list,form"):
    """Keep action construction readable in business models."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
    }
