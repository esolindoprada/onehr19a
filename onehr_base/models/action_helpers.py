

"""Window-action helpers.

Pure functions are intentional: Odoo 19 dynamically builds registry classes, so
plain Python helper classes must not be inserted into Odoo model Python bases.
"""


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
        "target": "current",
    }


def open_record_action(*, name, res_model, res_id):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
        "target": "current",
    }
