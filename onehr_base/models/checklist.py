

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .action_helpers import open_record_action, open_records_action


class OneHRChecklistTemplate(models.Model):
    _name = "onehr.checklist.template"
    _description = "OneHR Checklist Template Version"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, version desc"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, translate=True, tracking=True)
    version = fields.Integer(required=True, default=1, tracking=True)
    lifecycle_event_type_id = fields.Many2one(
        "onehr.lifecycle.event.type",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    eligibility_profile_id = fields.Many2one(
        "onehr.eligibility.profile",
        ondelete="restrict",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        index=True,
        ondelete="restrict",
        tracking=True,
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
    task_template_ids = fields.One2many(
        "onehr.checklist.task.template",
        "template_id",
        string="Task Definitions",
        copy=True,
    )
    task_template_count = fields.Integer(
        string="Task Definitions",
        compute="_compute_task_template_count",
    )
    instance_count = fields.Integer(
        string="Allocated Checklists",
        compute="_compute_instance_count",
    )

    @api.constrains("code", "company_id", "version")
    def _check_unique_version(self):
        for record in self:
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("code", "=ilike", record.code),
                    (
                        "company_id",
                        "=",
                        record.company_id.id if record.company_id else False,
                    ),
                    ("version", "=", record.version),
                ],
                limit=1,
            ):
                raise ValidationError(
                    _(
                        "Checklist version must be unique for its code and "
                        "company scope."
                    )
                )

    @api.constrains("code", "company_id", "valid_from", "valid_to", "state")
    def _check_active_overlap(self):
        for record in self.filtered(lambda item: item.state == "active"):
            record._check_no_effective_overlap(
                ["code", "company_id"],
                [("state", "=", "active")],
                _("Active checklist-template versions cannot overlap."),
            )

    def _compute_task_template_count(self):
        for record in self:
            record.task_template_count = len(record.task_template_ids)

    def _compute_instance_count(self):
        Instance = self.env["onehr.checklist.instance"]
        for record in self:
            record.instance_count = Instance.search_count(
                [("template_id", "=", record.id)]
            )

    # Workflow actions use normal write(), so model ACL and record rules remain
    # authoritative even if the method is invoked outside the UI.
    def action_activate(self):
        self.write({"state": "active"})
        return True

    def action_retire(self):
        self.write({"state": "retired"})
        return True

    def action_create_new_version(self):
        """Create a draft copy without rewriting an older template version."""
        self.ensure_one()
        latest = self.with_context(active_test=False).search(
            [
                ("code", "=ilike", self.code),
                (
                    "company_id",
                    "=",
                    self.company_id.id if self.company_id else False,
                ),
            ],
            order="version desc",
            limit=1,
        )
        next_version = (latest.version if latest else self.version) + 1
        # Copy the header first without One2many rows. Task dependencies are
        # remapped explicitly so a new version never points back to task rows
        # owned by the prior template version.
        new_template = self.copy(
            {
                "version": next_version,
                "state": "draft",
                "task_template_ids": [],
            }
        )

        task_mapping = {}
        source_tasks = self.task_template_ids.sorted(
            lambda task: (task.sequence, task.id)
        )
        for source_task in source_tasks:
            copied_task = source_task.copy(
                {
                    "template_id": new_template.id,
                    "dependency_ids": [(5, 0, 0)],
                }
            )
            task_mapping[source_task.id] = copied_task

        for source_task in source_tasks:
            task_mapping[source_task.id].dependency_ids = [
                (
                    6,
                    0,
                    [
                        task_mapping[dependency.id].id
                        for dependency in source_task.dependency_ids
                    ],
                )
            ]

        return open_record_action(
            name=_("Checklist Template Version %s", next_version),
            res_model=self._name,
            res_id=new_template.id,
        )

    def action_open_task_templates(self):
        self.ensure_one()
        return open_records_action(
            name=_("Task Definitions — %s", self.display_name),
            res_model="onehr.checklist.task.template",
            domain=[("template_id", "=", self.id)],
            context={"default_template_id": self.id},
        )

    def action_open_instances(self):
        self.ensure_one()
        return open_records_action(
            name=_("Allocated Checklists — %s", self.display_name),
            res_model="onehr.checklist.instance",
            domain=[("template_id", "=", self.id)],
            context={"default_template_id": self.id},
        )


class OneHRChecklistTaskTemplate(models.Model):
    _name = "onehr.checklist.task.template"
    _description = "OneHR Checklist Task Template"
    _inherit = ["onehr.mixin.audit"]
    _order = "template_id, sequence, id"

    template_id = fields.Many2one(
        "onehr.checklist.template",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="template_id.company_id",
        store=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True, tracking=True)
    instructions = fields.Html(translate=True)
    due_offset_days = fields.Integer(default=0)
    evidence_required = fields.Boolean()
    performer_policy = fields.Selection(
        [
            ("specific_user", "Specific User"),
            ("employee_manager", "Employee Manager"),
            ("hr_manager", "HR Manager"),
            ("extension", "Downstream Extension"),
        ],
        required=True,
        default="hr_manager",
    )
    performer_user_id = fields.Many2one("res.users", ondelete="restrict")
    dependency_ids = fields.Many2many(
        "onehr.checklist.task.template",
        "onehr_checklist_task_template_dependency_rel",
        "task_id",
        "dependency_id",
        string="Depends On",
    )

    @api.constrains("performer_policy", "performer_user_id")
    def _check_performer(self):
        for record in self:
            if (
                record.performer_policy == "specific_user"
                and not record.performer_user_id
            ):
                raise ValidationError(_("A specific performer user is required."))

    @api.constrains("dependency_ids", "template_id")
    def _check_dependencies(self):
        for record in self:
            if record in record.dependency_ids:
                raise ValidationError(_("A task cannot depend on itself."))
            if any(
                dependency.template_id != record.template_id
                for dependency in record.dependency_ids
            ):
                raise ValidationError(
                    _(
                        "Task dependencies must be in the same checklist-template "
                        "version."
                    )
                )

            visited = set()
            stack = list(record.dependency_ids)
            while stack:
                node = stack.pop()
                if node == record:
                    raise ValidationError(
                        _("Checklist task dependencies cannot contain a cycle.")
                    )
                if node.id not in visited:
                    visited.add(node.id)
                    stack.extend(node.dependency_ids)

    def resolve_performer(self, employee, allocation_context=None):
        """Stable extension hook for downstream governed performer resolution."""
        self.ensure_one()
        allocation_context = allocation_context or {}

        if self.performer_policy == "specific_user":
            return self.performer_user_id
        if self.performer_policy == "employee_manager":
            return employee.parent_id.user_id
        if self.performer_policy == "hr_manager":
            requested_user = allocation_context.get("hr_manager_user")
            if requested_user:
                return requested_user
            hr_manager_group = self.env.ref("hr.group_hr_manager")
            return self.env["res.users"].search(
                [
                    ("active", "=", True),
                    ("group_ids", "in", hr_manager_group.id),
                    ("company_ids", "in", employee.company_id.id),
                ],
                order="id",
                limit=1,
            )

        # "extension" is intentionally unresolved in the foundation. A later
        # registry-approved addon can override this method without source eval.
        return self.env["res.users"]

    def action_open_template(self):
        self.ensure_one()
        return open_record_action(
            name=self.template_id.display_name,
            res_model="onehr.checklist.template",
            res_id=self.template_id.id,
        )


class OneHRChecklistInstance(models.Model):
    _name = "onehr.checklist.instance"
    _description = "OneHR Checklist Instance"
    _inherit = ["onehr.mixin.audit"]
    _order = "event_date desc, id desc"

    name = fields.Char(
        required=True,
        readonly=True,
        default=lambda self: _("New Checklist"),
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        ondelete="restrict",
    )
    lifecycle_event_type_id = fields.Many2one(
        "onehr.lifecycle.event.type",
        required=True,
        ondelete="restrict",
    )
    template_id = fields.Many2one(
        "onehr.checklist.template",
        required=True,
        ondelete="restrict",
    )

    # Frozen execution facts are intentionally copied to the transaction so
    # later template edits cannot rewrite historical evidence.
    template_code = fields.Char(required=True, readonly=True)
    template_name = fields.Char(required=True, readonly=True)
    template_version = fields.Integer(required=True, readonly=True)

    event_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    source_model = fields.Char(index=True)
    source_res_id = fields.Integer()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )
    task_ids = fields.One2many(
        "onehr.checklist.task",
        "instance_id",
        string="Checklist Tasks",
    )
    completed_at = fields.Datetime(readonly=True)
    completed_by_id = fields.Many2one("res.users", readonly=True)
    task_count = fields.Integer(string="Tasks", compute="_compute_task_counts")
    pending_task_count = fields.Integer(
        string="Pending",
        compute="_compute_task_counts",
    )
    completed_task_count = fields.Integer(
        string="Done",
        compute="_compute_task_counts",
    )

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id:
            self.lifecycle_event_type_id = self.template_id.lifecycle_event_type_id
            self.template_code = self.template_id.code
            self.template_name = self.template_id.name
            self.template_version = self.template_id.version

    @api.constrains("source_model", "source_res_id")
    def _check_source_reference_pair(self):
        for record in self:
            if bool(record.source_model) != bool(record.source_res_id):
                raise ValidationError(
                    _(
                        "Source Model and Source Record ID must either both be set "
                        "or both be empty."
                    )
                )
            if record.source_res_id and record.source_res_id < 1:
                raise ValidationError(
                    _("Source Record ID must be a positive integer.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            template_id = values.get("template_id")
            employee_id = values.get("employee_id")
            if not template_id or not employee_id:
                raise ValidationError(
                    _("Employee and Checklist Template are required.")
                )

            template = self.env["onehr.checklist.template"].browse(
                template_id
            ).exists()
            employee = self.env["hr.employee"].browse(employee_id).exists()
            if not template or not employee:
                raise ValidationError(
                    _("Employee and Checklist Template must exist.")
                )

            company = self.env["res.company"].browse(
                values.get("company_id") or employee.company_id.id
            )
            if employee.company_id != company:
                raise ValidationError(
                    _("Checklist employee and company must match.")
                )
            if template.company_id and template.company_id != company:
                raise ValidationError(
                    _(
                        "Checklist template is not available to the employee "
                        "company."
                    )
                )

            event_date = fields.Date.to_date(
                values.get("event_date") or fields.Date.context_today(self)
            )
            if template.state != "active" or not template.is_effective_on(event_date):
                raise ValidationError(
                    _(
                        "The checklist template must be active and effective on "
                        "the event date."
                    )
                )

            if template.eligibility_profile_id:
                eligibility_values = self.build_eligibility_context(
                    employee,
                    event_date,
                    self.env.context.get("onehr_eligibility_context"),
                )
                if not template.eligibility_profile_id.matches(eligibility_values):
                    raise ValidationError(
                        _(
                            "The employee does not match the checklist eligibility "
                            "profile."
                        )
                    )

            values.update(
                {
                    "company_id": company.id,
                    "lifecycle_event_type_id": template.lifecycle_event_type_id.id,
                    "template_code": template.code,
                    "template_name": template.name,
                    "template_version": template.version,
                    "name": values.get("name")
                    or _("%s - %s", template.name, employee.name),
                }
            )

        records = super().create(vals_list)
        for record in records:
            record._allocate_frozen_tasks()
        return records

    @api.model
    def build_eligibility_context(self, employee, event_date, extra_values=None):
        """Extension hook for assignment/core-HR structured eligibility keys."""
        values = {
            "as_of_date": event_date,
            "company_id": employee.company_id.id,
            "department_id": employee.department_id.id,
            "job_id": employee.job_id.id,
            "work_location_id": employee.work_location_id.id,
        }
        values.update(extra_values or {})
        return values

    def _allocation_context(self):
        self.ensure_one()
        return {
            "instance": self,
            "employee": self.employee_id,
            "event_date": self.event_date,
        }

    def _allocate_frozen_tasks(self):
        """Copy operational facts once; later template edits stay non-retroactive."""
        Task = self.env["onehr.checklist.task"]
        for instance in self:
            if instance.task_ids:
                continue

            source_to_task = {}
            for source in instance.template_id.task_template_ids.sorted(
                lambda task: (task.sequence, task.id)
            ):
                performer = source.resolve_performer(
                    instance.employee_id,
                    instance._allocation_context(),
                )
                task = Task.create(
                    {
                        "instance_id": instance.id,
                        "source_task_template_id": source.id,
                        "sequence": source.sequence,
                        "name": source.name,
                        "instructions": source.instructions,
                        "due_date": instance.event_date
                        + relativedelta(days=source.due_offset_days),
                        "evidence_required": source.evidence_required,
                        "performer_policy": source.performer_policy,
                        "assigned_user_id": performer.id,
                    }
                )
                source_to_task[source.id] = task

            # Link dependencies only after every target task has been created.
            for source_id, task in source_to_task.items():
                dependencies = self.env[
                    "onehr.checklist.task.template"
                ].browse(source_id).dependency_ids
                task.dependency_ids = [
                    (
                        6,
                        0,
                        [source_to_task[dependency.id].id for dependency in dependencies],
                    )
                ]

            instance.state = "in_progress"
        return True

    def _compute_task_counts(self):
        for record in self:
            record.task_count = len(record.task_ids)
            record.pending_task_count = len(
                record.task_ids.filtered(lambda task: task.state == "pending")
            )
            record.completed_task_count = len(
                record.task_ids.filtered(lambda task: task.state == "done")
            )

    def action_complete(self):
        for record in self:
            if record.state == "completed":
                continue
            if any(task.state == "pending" for task in record.task_ids):
                raise UserError(
                    _(
                        "All checklist tasks must be done or cancelled before "
                        "the checklist can be completed."
                    )
                )
            record.write(
                {
                    "state": "completed",
                    "completed_at": fields.Datetime.now(),
                    "completed_by_id": self.env.user.id,
                }
            )
        return True

    def action_cancel(self):
        for record in self.filtered(
            lambda item: item.state in ("draft", "in_progress")
        ):
            record.task_ids.filtered(
                lambda task: task.state == "pending"
            ).action_cancel()
            record.write({"state": "cancelled"})
        return True

    def action_schedule_outstanding_activities(self):
        for record in self:
            record.task_ids.filtered(
                lambda task: (
                    task.state == "pending"
                    and task.assigned_user_id
                    and not task.activity_id
                )
            ).action_schedule_activity()
        return True

    def action_open_tasks(self):
        self.ensure_one()
        return open_records_action(
            name=_("Checklist Tasks — %s", self.display_name),
            res_model="onehr.checklist.task",
            domain=[("instance_id", "=", self.id)],
            context={"default_instance_id": self.id},
        )

    def write(self, vals):
        protected_fields = {
            "employee_id",
            "company_id",
            "lifecycle_event_type_id",
            "template_id",
            "template_code",
            "template_name",
            "template_version",
            "event_date",
            "source_model",
            "source_res_id",
            "task_ids",
            "state",
            "completed_at",
            "completed_by_id",
        }
        if protected_fields.intersection(vals) and any(
            record.state == "completed" for record in self
        ):
            raise UserError(_("Completed checklist history cannot be rewritten."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_completed_history(self):
        """Protect business history without deliberately blocking module uninstall."""
        if any(record.state == "completed" for record in self):
            raise UserError(_("Completed checklist history cannot be deleted."))


class OneHRChecklistTask(models.Model):
    _name = "onehr.checklist.task"
    _description = "OneHR Checklist Task"
    _inherit = ["onehr.mixin.audit"]
    _order = "due_date, sequence, id"

    instance_id = fields.Many2one(
        "onehr.checklist.instance",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="instance_id.company_id",
        store=True,
        index=True,
    )
    employee_id = fields.Many2one(
        related="instance_id.employee_id",
        store=True,
        index=True,
    )
    source_task_template_id = fields.Many2one(
        "onehr.checklist.task.template",
        required=True,
        ondelete="restrict",
    )
    sequence = fields.Integer(default=10, readonly=True)
    name = fields.Char(required=True, readonly=True)
    instructions = fields.Html(readonly=True)
    due_date = fields.Date(readonly=True, index=True)
    evidence_required = fields.Boolean(readonly=True)
    performer_policy = fields.Selection(
        [
            ("specific_user", "Specific User"),
            ("employee_manager", "Employee Manager"),
            ("hr_manager", "HR Manager"),
            ("extension", "Downstream Extension"),
        ],
        required=True,
        readonly=True,
    )
    assigned_user_id = fields.Many2one(
        "res.users",
        ondelete="restrict",
        tracking=True,
    )
    dependency_ids = fields.Many2many(
        "onehr.checklist.task",
        "onehr_checklist_task_dependency_rel",
        "task_id",
        "dependency_id",
        string="Depends On",
        readonly=True,
    )
    activity_id = fields.Many2one(
        "mail.activity",
        ondelete="set null",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="pending",
        tracking=True,
        index=True,
    )
    completed_at = fields.Datetime(readonly=True)
    completed_by_id = fields.Many2one("res.users", readonly=True)
    completion_note = fields.Text()
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Evidence",
    )

    def action_done(self, note=None, attachment_ids=None):
        for record in self:
            if record.state == "done":
                continue
            if record.state == "cancelled":
                raise UserError(_("A cancelled checklist task cannot be completed."))
            if any(
                dependency.state != "done" for dependency in record.dependency_ids
            ):
                raise UserError(_("Complete prerequisite tasks first."))

            attachment_ids = attachment_ids or record.evidence_attachment_ids.ids
            if record.evidence_required and not attachment_ids:
                raise UserError(_("Evidence is required to complete this task."))

            record.write(
                {
                    "state": "done",
                    "completed_at": fields.Datetime.now(),
                    "completed_by_id": self.env.user.id,
                    "completion_note": note
                    if note is not None
                    else record.completion_note,
                    "evidence_attachment_ids": [(6, 0, attachment_ids)],
                }
            )
            if record.activity_id:
                record.activity_id.action_done()
        return True

    def action_cancel(self):
        self.filtered(lambda task: task.state == "pending").write(
            {"state": "cancelled"}
        )
        return True

    def action_schedule_activity(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for record in self.filtered(
            lambda task: (
                task.state == "pending"
                and task.assigned_user_id
                and not task.activity_id
            )
        ):
            activity = self.env["mail.activity"].create(
                {
                    "activity_type_id": activity_type.id,
                    "summary": record.name,
                    "date_deadline": record.due_date,
                    "user_id": record.assigned_user_id.id,
                    "res_model_id": self.env["ir.model"]._get_id(self._name),
                    "res_id": record.id,
                }
            )
            record.activity_id = activity
        return True

    def action_open_instance(self):
        self.ensure_one()
        return open_record_action(
            name=self.instance_id.display_name,
            res_model="onehr.checklist.instance",
            res_id=self.instance_id.id,
        )

    def write(self, vals):
        evidence_fields = {
            "state",
            "assigned_user_id",
            "completed_at",
            "completed_by_id",
            "completion_note",
            "evidence_attachment_ids",
            "activity_id",
        }
        if evidence_fields.intersection(vals) and any(
            record.state == "done" for record in self
        ):
            allowed_idempotent = vals.get("state") == "done" and set(vals) == {"state"}
            if not allowed_idempotent:
                raise UserError(
                    _("Completed task evidence cannot be reset or rewritten.")
                )

        frozen_fields = {
            "source_task_template_id",
            "sequence",
            "name",
            "instructions",
            "due_date",
            "evidence_required",
            "performer_policy",
            "dependency_ids",
        }
        if frozen_fields.intersection(vals) and any(
            record.instance_id.state == "completed" for record in self
        ):
            raise UserError(
                _(
                    "Frozen facts in completed checklist history cannot be "
                    "rewritten."
                )
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_completed_evidence(self):
        """Protect completed evidence while preserving module uninstall safety."""
        if any(
            record.state == "done" or record.instance_id.state == "completed"
            for record in self
        ):
            raise UserError(_("Completed checklist tasks cannot be deleted."))
