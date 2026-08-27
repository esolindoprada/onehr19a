from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OneHRRecruitmentCommon


@tagged("post_install", "-at_install", "onehr_recruitment")
class TestSecurityRegistry(OneHRRecruitmentCommon):
    def test_16_native_registry_ownership_is_preserved(self):
        self.assertIn("onehr_requisition_id", self.env["hr.applicant"]._fields)
        self.assertIn("onehr_phase", self.env["hr.recruitment.stage"]._fields)
        self.assertIn("onehr_requisition_ids", self.env["hr.job"]._fields)
        self.assertIn("onehr_target_job_id", self.env["hr.talent.pool"]._fields)
        self.assertIsNone(self.env.registry.get("onehr.applicant"))
        self.assertIsNone(self.env.registry.get("onehr.recruit.stage"))
        self.assertIsNone(self.env.registry.get("onehr.job.opening"))
        self.assertIsNone(self.env.registry.get("onehr.onboard.template"))

    def test_17_hiring_manager_reads_only_assigned_requisition(self):
        assigned = self.requisition.with_user(self.hiring_manager)
        self.assertEqual(assigned.name, self.requisition.name)
        other = self.env["onehr.recruitment.requisition"].with_user(self.manager).create({
            "title": "Unassigned Requisition",
            "company_id": self.company.id,
            "job_id": self.job.id,
            "requested_headcount": 1,
            "reason": "Security test",
        })
        self.assertFalse(self.env["onehr.recruitment.requisition"].with_user(self.hiring_manager).search([("id", "=", other.id)]))

    def test_18_hiring_manager_cannot_create_requisition(self):
        with self.assertRaises(AccessError):
            self.env["onehr.recruitment.requisition"].with_user(self.hiring_manager).create({
                "title": "Unauthorized",
                "company_id": self.company.id,
                "job_id": self.job.id,
                "requested_headcount": 1,
                "reason": "Must fail",
            })

    def test_19_company_rule_isolation(self):
        other = self.env["onehr.recruitment.requisition"].with_user(self.manager).create({
            "title": "Other Company Requisition",
            "company_id": self.other_company.id,
            "job_id": self.other_job.id,
            "requested_headcount": 1,
            "reason": "Company isolation test",
        })
        self.assertFalse(self.env["onehr.recruitment.requisition"].with_user(self.recruiter).search([("id", "=", other.id)]))

    def test_20_source_snapshot_is_idempotent_and_immutable(self):
        metrics1 = self.env["onehr.recruitment.source.metric"].with_user(self.manager).build_snapshot(
            period_start=self.applicant.create_date.date(),
            period_end=self.applicant.create_date.date(),
            company=self.company,
            job=self.job,
        )
        metrics2 = self.env["onehr.recruitment.source.metric"].with_user(self.manager).build_snapshot(
            period_start=self.applicant.create_date.date(),
            period_end=self.applicant.create_date.date(),
            company=self.company,
            job=self.job,
        )
        self.assertEqual(metrics1.ids, metrics2.ids)
        with self.assertRaises(AccessError):
            metrics1.with_user(self.manager).write({"application_count": 999})
