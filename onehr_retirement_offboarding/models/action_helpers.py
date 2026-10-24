from odoo import _


def open_record_action(*, name, res_model, res_id):
    """Return a predictable current-window form action."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
        "target": "current",
    }


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    """Return a reusable company/rule-safe records action."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
        "target": "current",
    }


def display_notification(message, *, title=None, notification_type="info", sticky=False):
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": title or _("OneHR Offboarding"),
            "message": message,
            "type": notification_type,
            "sticky": sticky,
        },
    }
