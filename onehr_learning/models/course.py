from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_records_action
from .authority_helpers import require_learning_manager, require_learning_officer


class OneHRLearningCourse(models.Model):
    """Learning catalog master.

    Curriculum and prerequisite ownership stays here. Competency ownership does not:
    the future Career & Succession addon may consume learning evidence without this
    addon creating duplicate competency masters.
    """

    _name = "onehr.learning.course"
    _description = "OneHR Learning Course"
    _inherit = ["onehr.mixin.audit"]
    _order = "code, name, id"

    _PUBLISH_CONTEXT = "onehr_learning_course_publish_controlled"

    name = fields.Char(required=True, translate=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    published = fields.Boolean(default=False, readonly=True, copy=False, index=True, tracking=True)

    course_type = fields.Selection(
        [
            ("mandatory", "Mandatory / Compliance"),
            ("technical", "Technical"),
            ("professional", "Professional"),
            ("leadership", "Leadership"),
            ("onboarding", "Onboarding"),
            ("safety", "Safety"),
            ("general", "General"),
            ("external", "External Program"),
        ],
        required=True,
        default="general",
        index=True,
        tracking=True,
    )
    level = fields.Selection(
        [
            ("foundation", "Foundation"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
            ("expert", "Expert"),
        ],
        required=True,
        default="foundation",
        index=True,
        tracking=True,
    )
    default_delivery_mode = fields.Selection(
        [
            ("classroom", "Classroom"),
            ("virtual", "Virtual"),
            ("blended", "Blended"),
            ("self_paced", "Self-Paced"),
        ],
        required=True,
        default="classroom",
        tracking=True,
    )
    mandatory = fields.Boolean(
        compute="_compute_mandatory",
        store=True,
        help="Derived from Course Type; stored for fast compliance reporting.",
    )

    description = fields.Text(translate=True)
    learning_objectives = fields.Text(translate=True)
    curriculum = fields.Html(translate=True, sanitize=True)
    target_audience = fields.Text(translate=True)
    duration_hours = fields.Float(default=1.0, tracking=True)
    pass_score = fields.Float(
        default=70.0,
        tracking=True,
        help="Minimum post-test score required when result evaluation is score-driven.",
    )
    certificate_validity_months = fields.Integer(
        default=0,
        tracking=True,
        help="Zero means the certificate does not automatically expire.",
    )
    certificate_reminder_days = fields.Integer(
        default=30,
        tracking=True,
    )
    certificate_title = fields.Char(
        default="Certificate of Completion",
        translate=True,
        tracking=True,
    )
    certificate_statement = fields.Char(
        default="has successfully completed",
        translate=True,
        tracking=True,
    )
    certificate_signatory_name = fields.Char(tracking=True)
    certificate_signatory_title = fields.Char(translate=True, tracking=True)
    certificate_document_category_code = fields.Char(
        default="TRAINING_CERTIFICATE",
        tracking=True,
        help="Soft Document integration category code. No hard dependency on onehr_document is introduced.",
    )
    training_leave_type_code = fields.Char(
        tracking=True,
        help="Optional OneHR Time Off leave-type code used by the governed soft integration.",
    )

    prerequisite_course_ids = fields.Many2many(
        "onehr.learning.course",
        "onehr_learning_course_prerequisite_rel",
        "course_id",
        "prerequisite_id",
        string="Prerequisite Courses",
        tracking=True,
    )

    session_count = fields.Integer(compute="_compute_usage_counts")
    enrollment_count = fields.Integer(compute="_compute_usage_counts")
    certificate_count = fields.Integer(compute="_compute_usage_counts")

    _course_code_company_unique = models.Constraint(
        "unique(company_id, code)",
        "Learning Course code must be unique within a company.",
    )

    @api.depends("course_type")
    def _compute_mandatory(self):
        for record in self:
            record.mandatory = record.course_type == "mandatory"

    def _compute_usage_counts(self):
        Session = self.env["onehr.learning.session"]
        Enrollment = self.env["onehr.learning.enrollment"]
        Certificate = self.env["onehr.learning.certificate"]
        for record in self:
            record.session_count = Session.search_count([("course_id", "=", record.id)])
            record.enrollment_count = Enrollment.search_count([("course_id", "=", record.id)])
            record.certificate_count = Certificate.search_count([("course_id", "=", record.id)])

    @api.model_create_multi
    def create(self, vals_list):
        require_learning_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            vals["code"] = (vals.get("code") or "").strip().upper()
            vals["published"] = False
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_course_integrity()
        return records

    def write(self, values):
        require_learning_officer(self)
        values = dict(values)
        if "published" in values and not self.env.context.get(self._PUBLISH_CONTEXT):
            raise AccessError(_("Course publication can be changed only through Publish/Unpublish actions."))
        if "code" in values:
            values["code"] = (values.get("code") or "").strip().upper()
        result = super().write(values)
        self._validate_course_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_used_course(self):
        require_learning_manager(self)
        for record in self:
            if record.session_count or record.enrollment_count or record.certificate_count:
                raise AccessError(
                    _("A Learning Course with operational history cannot be deleted. Archive it instead.")
                )

    @api.constrains(
        "duration_hours",
        "pass_score",
        "certificate_validity_months",
        "certificate_reminder_days",
        "prerequisite_course_ids",
        "company_id",
    )
    def _check_course_integrity(self):
        self._validate_course_integrity()

    def _validate_course_integrity(self):
        for record in self:
            if record.published and not record.active:
                raise ValidationError(
                    _("A Published Course must remain active; Unpublish it before archiving.")
                )
            if record.duration_hours <= 0:
                raise ValidationError(_("Course Duration must be greater than zero."))
            if not 0 <= record.pass_score <= 100:
                raise ValidationError(_("Pass Score must be between 0 and 100."))
            if record.certificate_validity_months < 0 or record.certificate_reminder_days < 0:
                raise ValidationError(_("Certificate validity/reminder values cannot be negative."))
            if record in record.prerequisite_course_ids:
                raise ValidationError(_("A course cannot be its own prerequisite."))
            if any(item.company_id != record.company_id for item in record.prerequisite_course_ids):
                raise ValidationError(_("Prerequisite courses must belong to the same company."))

            # Detect indirect loops while keeping prerequisites inside the approved
            # course model rather than inventing a curriculum graph model.
            visited = self.env["onehr.learning.course"]
            frontier = record.prerequisite_course_ids
            while frontier:
                if record in frontier:
                    raise ValidationError(_("Course prerequisite relationships cannot contain cycles."))
                current = frontier - visited
                if not current:
                    break
                visited |= current
                frontier = current.mapped("prerequisite_course_ids")
        return True

    def action_publish(self):
        require_learning_manager(self)
        for record in self:
            record._validate_course_integrity()
            record.with_context(**{self._PUBLISH_CONTEXT: True}).write(
                {"published": True, "active": True}
            )
            record.log_business_action(_("Course published to the Learning catalog."))
        return display_notification(_("Selected course(s) published."))

    def action_unpublish(self):
        require_learning_manager(self)
        self.with_context(**{self._PUBLISH_CONTEXT: True}).write({"published": False})
        self.log_business_action(_("Course removed from the published Learning catalog."))
        return display_notification(_("Selected course(s) unpublished."), notification_type="warning")

    def action_validate_prerequisites(self):
        require_learning_officer(self)
        self._validate_course_integrity()
        return display_notification(_("Course prerequisite structure is valid."))

    def action_open_sessions(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Sessions — %s", self.display_name),
            res_model="onehr.learning.session",
            domain=[("course_id", "=", self.id)],
            context={"default_course_id": self.id, "default_company_id": self.company_id.id},
            view_mode="list,calendar,pivot,graph,form",
        )

    def action_open_enrollments(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Enrollments — %s", self.display_name),
            res_model="onehr.learning.enrollment",
            domain=[("course_id", "=", self.id)],
            context={"default_course_id": self.id},
            view_mode="kanban,list,pivot,graph,form",
        )

    def action_open_certificates(self):
        self.ensure_one()
        require_learning_officer(self)
        return open_records_action(
            name=_("Certificates — %s", self.display_name),
            res_model="onehr.learning.certificate",
            domain=[("course_id", "=", self.id)],
            view_mode="list,calendar,pivot,graph,form",
        )
