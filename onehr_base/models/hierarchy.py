from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_record_action, open_records_action


class OneHRPositionHierarchy(models.Model):
    _name = "onehr.position.hierarchy"
    _description = "OneHR Position Hierarchy"
    _inherit = ["onehr.mixin.audit"]
    _order = "name"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    purpose = fields.Selection(
        [
            ("reporting", "Reporting"),
            ("career", "Career"),
            ("approval", "Approval"),
            ("other", "Other"),
        ],
        required=True,
        default="reporting",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    version_ids = fields.One2many(
        "onehr.position.hierarchy.version",
        "hierarchy_id",
        string="Versions",
    )
    version_count = fields.Integer(
        string="Versions",
        compute="_compute_version_count",
    )

    @api.constrains("code", "company_id")
    def _check_unique_code(self):
        for record in self:
            if self.with_context(active_test=False).search_count(
                [
                    ("id", "!=", record.id),
                    ("company_id", "=", record.company_id.id),
                    ("code", "=ilike", record.code),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Hierarchy code must be unique within a company.")
                )

    def _compute_version_count(self):
        for record in self:
            record.version_count = len(record.version_ids)

    def action_open_versions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Hierarchy Versions — %s", self.display_name),
            res_model="onehr.position.hierarchy.version",
            domain=[("hierarchy_id", "=", self.id)],
            context={"default_hierarchy_id": self.id},
        )


class OneHRPositionHierarchyVersion(models.Model):
    _name = "onehr.position.hierarchy.version"
    _description = "OneHR Position Hierarchy Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "hierarchy_id, version desc"

    hierarchy_id = fields.Many2one(
        "onehr.position.hierarchy",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    version = fields.Integer(required=True, default=1, tracking=True)
    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        related="hierarchy_id.company_id",
        store=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("retired", "Retired"),
        ],
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )
    node_ids = fields.One2many(
        "onehr.position.hierarchy.node",
        "version_id",
        string="Hierarchy Nodes",
    )
    node_count = fields.Integer(string="Nodes", compute="_compute_node_count")

    @api.depends("hierarchy_id.name", "version")
    def _compute_name(self):
        for record in self:
            record.name = _(
                "%s / Version %s",
                record.hierarchy_id.name,
                record.version,
            )

    @api.constrains("hierarchy_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("hierarchy_id", "=", record.hierarchy_id.id),
                    ("version", "=", record.version),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("Version number must be unique per hierarchy.")
                )

    @api.constrains("hierarchy_id", "valid_from", "valid_to", "state")
    def _check_active_overlap(self):
        for record in self.filtered(lambda item: item.state == "active"):
            record._check_no_effective_overlap(
                ["hierarchy_id"],
                [("state", "=", "active")],
                _("Active hierarchy versions cannot overlap."),
            )

    def _compute_node_count(self):
        for record in self:
            record.node_count = len(record.node_ids)

    # Normal write() is intentional. ACL and record rules stay authoritative
    # even when these methods are called outside the web client.
    def action_activate(self):
        self.write({"state": "active"})
        return True

    def action_retire(self):
        self.write({"state": "retired"})
        return True

    def action_open_nodes(self):
        self.ensure_one()
        return open_records_action(
            name=_("Hierarchy Nodes — %s", self.display_name),
            res_model="onehr.position.hierarchy.node",
            domain=[("version_id", "=", self.id)],
            context={"default_version_id": self.id},
        )


class OneHRPositionHierarchyNode(models.Model):
    _name = "onehr.position.hierarchy.node"
    _description = "OneHR Position Hierarchy Node"
    _inherit = ["onehr.mixin.audit"]
    _order = "version_id, sequence, id"
    _parent_name = "parent_id"
    _parent_store = True

    version_id = fields.Many2one(
        "onehr.position.hierarchy.version",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="version_id.company_id",
        store=True,
        index=True,
    )
    position_id = fields.Many2one(
        "onehr.position",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    parent_id = fields.Many2one(
        "onehr.position.hierarchy.node",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "onehr.position.hierarchy.node",
        "parent_id",
        string="Children",
    )
    sequence = fields.Integer(default=10)

    @api.constrains("version_id", "position_id")
    def _check_unique_position(self):
        for record in self:
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("version_id", "=", record.version_id.id),
                    ("position_id", "=", record.position_id.id),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _("A position may appear only once in a hierarchy version.")
                )
            if record.position_id.company_id != record.company_id:
                raise ValidationError(
                    _("Node position must belong to the hierarchy company.")
                )

    @api.constrains("parent_id", "version_id")
    def _check_parent_version_and_cycle(self):
        if not self._check_recursion():
            raise ValidationError(
                _("A hierarchy node cannot be its own ancestor.")
            )
        for record in self:
            if (
                record.parent_id
                and record.parent_id.version_id != record.version_id
            ):
                raise ValidationError(
                    _(
                        "Parent and child nodes must belong to the same "
                        "hierarchy version."
                    )
                )

    def action_open_position(self):
        self.ensure_one()
        return open_record_action(
            name=self.position_id.display_name,
            res_model="onehr.position",
            res_id=self.position_id.id,
        )
