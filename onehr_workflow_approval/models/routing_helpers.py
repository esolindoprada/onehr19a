"""Pure approval-routing helpers.

Odoo 19 builds registry classes dynamically, therefore reusable implementation
logic stays in pure functions instead of plain-Python classes inserted into Odoo
model base lists.
"""

from odoo import _, SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError


WORKFLOW_ADMIN_GROUP = "onehr_workflow_approval.group_onehr_workflow_admin"
WORKFLOW_MANAGER_GROUP = "onehr_workflow_approval.group_onehr_workflow_manager"
APPROVER_GROUP = "onehr_workflow_approval.group_onehr_approver"


def is_workflow_admin(env):
    return env.uid == SUPERUSER_ID or env.user.has_group(WORKFLOW_ADMIN_GROUP)


def is_workflow_manager(env):
    return is_workflow_admin(env) or env.user.has_group(WORKFLOW_MANAGER_GROUP)


def require_workflow_admin(env):
    if not is_workflow_admin(env):
        raise AccessError(_("Workflow Administrator access is required."))


def require_workflow_manager(env):
    if not is_workflow_manager(env):
        raise AccessError(_("Workflow Manager access is required."))


def require_approver(env):
    if not (is_workflow_manager(env) or env.user.has_group(APPROVER_GROUP)):
        raise AccessError(_("Approval authority is required."))


def clean_ids(values):
    """Return unique positive integer IDs while preserving source order."""
    result = []
    seen = set()
    for value in values or []:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id > 0 and item_id not in seen:
            seen.add(item_id)
            result.append(item_id)
    return result


def validate_structured_match(value):
    """Validate non-executable exact/list routing criteria."""
    if value in (None, False):
        return {}
    if not isinstance(value, dict):
        raise ValidationError(_("Structured approval criteria must be a JSON object."))

    scalar_types = (str, int, float, bool, type(None))
    for key, expected in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(_("Approval criteria keys must be non-empty strings."))
        if isinstance(expected, scalar_types):
            continue
        if isinstance(expected, list) and all(isinstance(item, scalar_types) for item in expected):
            continue
        raise ValidationError(
            _(
                "Approval criteria values may only be scalar values or lists of "
                "scalar values. Executable expressions are forbidden."
            )
        )
    return value


def structured_match(expected_map, actual_map):
    expected_map = validate_structured_match(expected_map)
    actual_map = actual_map or {}
    for key, expected in expected_map.items():
        actual = actual_map.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True
