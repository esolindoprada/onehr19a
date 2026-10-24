from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action
from .authority_helpers import require_recruitment_manager


class HrApplicant(models.Model):
    """Recruitment-native applicant remains the canonical applicant record."""

    _inherit = "hr.applicant"

    onehr_requisition_id = fields.Many2one(
        "onehr.recruitment.requisition",
        string="OneHR Requisition",
        index=True,
        tracking=True,
        ondelete="set null",
        check_company=True,
        help="Approved OneHR requisition that originated this application.",
    )
    onehr_interview_session_ids = fields.One2many(
        "onehr.interview.session", "applicant_id", string="OneHR Interviews"
    )
    onehr_offer_ids = fields.One2many("onehr.offer", "applicant_id", string="OneHR Offers")
    onehr_preboarding_ids = fields.One2many(
        "onehr.preboarding", "applicant_id", string="OneHR Preboarding"
    )
    onehr_interview_count = fields.Integer(compute="_compute_onehr_recruitment_counts")
    onehr_offer_count = fields.Integer(compute="_compute_onehr_recruitment_counts")
    onehr_preboarding_count = fields.Integer(compute="_compute_onehr_recruitment_counts")
    onehr_latest_offer_state = fields.Selection(
        [
            ("none", "No Offer"),
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("withdrawn", "Withdrawn"),
            ("expired", "Expired"),
        ],
        compute="_compute_onehr_recruitment_counts",
        store=True,
        index=True,
        string="Latest Offer",
    )

    @api.depends(
        "onehr_interview_session_ids",
        "onehr_offer_ids",
        "onehr_offer_ids.state",
        "onehr_preboarding_ids",
    )
    def _compute_onehr_recruitment_counts(self):
        for applicant in self:
            applicant.onehr_interview_count = len(applicant.onehr_interview_session_ids)
            applicant.onehr_offer_count = len(applicant.onehr_offer_ids)
            applicant.onehr_preboarding_count = len(applicant.onehr_preboarding_ids)
            latest = applicant.onehr_offer_ids.sorted(lambda rec: (rec.create_date or fields.Datetime.now(), rec.id), reverse=True)[:1]
            applicant.onehr_latest_offer_state = latest.state if latest else "none"

    @api.constrains("onehr_requisition_id", "job_id", "company_id")
    def _check_onehr_requisition_alignment(self):
        for applicant in self.filtered("onehr_requisition_id"):
            requisition = applicant.onehr_requisition_id
            if applicant.company_id and requisition.company_id != applicant.company_id:
                raise ValidationError(_("Applicant and OneHR requisition must belong to the same company."))
            if applicant.job_id and requisition.job_id != applicant.job_id:
                raise ValidationError(_("Applicant job must match the OneHR requisition job."))

    def action_open_onehr_interviews(self):
        self.ensure_one()
        return open_records_action(
            name=_("Interviews — %s", self.partner_name or self.display_name),
            res_model="onehr.interview.session",
            domain=[("applicant_id", "=", self.id)],
            context={"default_applicant_id": self.id, "default_requisition_id": self.onehr_requisition_id.id},
            view_mode="calendar,list,form",
        )

    def action_open_onehr_offers(self):
        self.ensure_one()
        return open_records_action(
            name=_("Offers — %s", self.partner_name or self.display_name),
            res_model="onehr.offer",
            domain=[("applicant_id", "=", self.id)],
            context={"default_applicant_id": self.id, "default_requisition_id": self.onehr_requisition_id.id},
        )

    def action_open_onehr_preboarding(self):
        self.ensure_one()
        return open_records_action(
            name=_("Preboarding — %s", self.partner_name or self.display_name),
            res_model="onehr.preboarding",
            domain=[("applicant_id", "=", self.id)],
            context={"default_applicant_id": self.id, "default_requisition_id": self.onehr_requisition_id.id},
        )

    def action_prepare_onehr_preboarding(self):
        self.ensure_one()
        existing = self.onehr_preboarding_ids.filtered(lambda rec: rec.state != "cancelled")[:1]
        if existing:
            return existing.action_open_self()
        preboarding = self.env["onehr.preboarding"].create(
            {
                "applicant_id": self.id,
                "requisition_id": self.onehr_requisition_id.id,
                "offer_id": self.onehr_offer_ids.filtered(lambda rec: rec.state == "accepted")[:1].id,
                "planned_start_date": fields.Date.today(),
            }
        )
        return preboarding.action_open_self()


class HrRecruitmentStage(models.Model):
    """Add governance/SLA semantics to Odoo's canonical recruitment stages."""

    _inherit = "hr.recruitment.stage"

    onehr_phase = fields.Selection(
        [
            ("screening", "Screening"),
            ("interview", "Interview"),
            ("offer", "Offer"),
            ("preboarding", "Preboarding"),
            ("hired", "Hired"),
            ("rejected", "Rejected"),
        ],
        string="OneHR Phase",
        index=True,
        help="Enterprise reporting phase mapped onto this native Odoo stage.",
    )
    onehr_sla_days = fields.Integer(
        string="Stage SLA (Days)",
        default=0,
        help="Target maximum elapsed calendar days in this stage. Zero means no OneHR SLA.",
    )
    onehr_requires_interview = fields.Boolean(
        string="Interview Required",
        help="Signals that a completed structured OneHR interview is expected before leaving this stage.",
    )
    onehr_requires_approved_offer = fields.Boolean(
        string="Approved Offer Required",
        help="Signals that an approved OneHR offer is required for this stage transition.",
    )

    @api.constrains("onehr_sla_days")
    def _check_onehr_sla_days(self):
        if any(stage.onehr_sla_days < 0 for stage in self):
            raise ValidationError(_("Recruitment stage SLA cannot be negative."))


class HrJob(models.Model):
    """Recruitment demand links on the Odoo-native job catalogue."""

    _inherit = "hr.job"

    onehr_requisition_ids = fields.One2many(
        "onehr.recruitment.requisition", "job_id", string="OneHR Requisitions"
    )
    onehr_requisition_count = fields.Integer(compute="_compute_onehr_requisition_count")
    onehr_open_requisition_count = fields.Integer(compute="_compute_onehr_requisition_count")

    @api.depends("onehr_requisition_ids.state")
    def _compute_onehr_requisition_count(self):
        for job in self:
            job.onehr_requisition_count = len(job.onehr_requisition_ids)
            job.onehr_open_requisition_count = len(
                job.onehr_requisition_ids.filtered(lambda rec: rec.state in {"approved", "recruiting"})
            )

    def action_open_onehr_requisitions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Recruitment Requisitions — %s", self.display_name),
            res_model="onehr.recruitment.requisition",
            domain=[("job_id", "=", self.id)],
            context={"default_job_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_build_onehr_source_snapshot(self):
        """Create an idempotent 30-day source/funnel snapshot for this job."""
        self.ensure_one()
        require_recruitment_manager(self)
        period_end = fields.Date.today()
        period_start = period_end - timedelta(days=29)
        metrics = self.env["onehr.recruitment.source.metric"].build_snapshot(
            period_start=period_start,
            period_end=period_end,
            company=self.company_id or self.env.company,
            job=self,
        )
        return open_records_action(
            name=_("30-Day Source Metrics — %s", self.display_name),
            res_model="onehr.recruitment.source.metric",
            domain=[("id", "in", metrics.ids)],
            view_mode="list,pivot,graph,form",
        )


class HrTalentPool(models.Model):
    """Enterprise target/review metadata on Odoo's native talent pool."""

    _inherit = "hr.talent.pool"

    onehr_target_job_id = fields.Many2one(
        "hr.job",
        string="Target Job",
        index=True,
        ondelete="set null",
        check_company=True,
        help="Optional primary job target for this native Odoo talent pool.",
    )
    onehr_review_date = fields.Date(
        string="Next Review Date",
        index=True,
        help="Governance review date for continued relevance of this talent pool.",
    )

    @api.constrains("onehr_target_job_id", "company_id")
    def _check_onehr_target_job_company(self):
        for pool in self.filtered("onehr_target_job_id"):
            if pool.company_id and pool.onehr_target_job_id.company_id and pool.company_id != pool.onehr_target_job_id.company_id:
                raise ValidationError(_("Talent pool target job must belong to the same company."))
