
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRJobDescriptionCommon


@tagged("post_install", "-at_install", "onehr_job_description")
class TestJDSecurityAndIntegrations(OneHRJobDescriptionCommon):
    def test_19_plain_user_has_no_jd_access(self):
        with self.assertRaises(AccessError):
            self.env["onehr.jd"].with_user(self.plain_user).search([])

    def test_20_reader_sees_only_current_published_version(self):
        jd = self.make_jd()
        first = self.publish_version(self.make_version(jd))
        second = self.make_version(
            jd,
            change_summary="Unpublished revision.",
        )

        visible = self.env["onehr.jd.version"].with_user(self.reader).search(
            [("jd_id", "=", jd.id)]
        )
        self.assertEqual(visible, first)
        self.assertNotIn(second, visible)

    def test_21_job_family_template_generates_position_jd(self):
        template = self.make_template()
        version = self.make_version(template)
        self.publish_version(version)

        template.with_user(self.editor).action_generate_position_jds()
        generated = self.env["onehr.jd"].with_user(self.editor).search(
            [
                ("position_id", "=", self.position.id),
                ("is_template", "=", False),
            ]
        )
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated.latest_version_id.state, "draft")

    def test_22_recruitment_payload_exposes_published_content(self):
        jd = self.make_jd()
        self.publish_version(self.make_version(jd))

        payload = self.env["onehr.jd"].with_user(
            self.editor
        ).onehr_jd_recruitment_payload(position=self.position)
        self.assertEqual(payload["jd_reference"], jd.code)
        self.assertIn("purpose", payload)
        self.assertIn("qualification_requirements", payload)

    def test_23_appraisal_payload_exposes_kpi_and_competency(self):
        jd = self.make_jd()
        self.publish_version(self.make_version(jd))

        payload = self.env["onehr.jd"].with_user(
            self.editor
        ).onehr_jd_appraisal_payload(position=self.position)
        self.assertEqual(payload["jd_reference"], jd.code)
        self.assertIn("kpi_codes", payload)
        self.assertIn("competency_requirements", payload)

    def test_24_kpi_snapshot_reports_position_coverage(self):
        jd = self.make_jd()
        self.publish_version(self.make_version(jd))
        jd._refresh_governance_metrics()

        payload = self.env["onehr.jd"].with_user(
            self.approver
        ).onehr_jd_kpi_snapshot(self.company)
        self.assertIn("coverage_percent", payload)
        self.assertIn("average_version_age_days", payload)
        self.assertIn("overdue_review_count", payload)

    def test_25_external_text_source_is_extracted(self):
        version = self.make_version()
        version.with_user(self.editor).write(
            {
                "source_filename": "external_jd.txt",
                "source_file": base64.b64encode(
                    b"External Job Description source evidence."
                ),
            }
        )
        version.with_user(self.editor).action_import_source_document()
        self.assertIn(
            "External Job Description",
            version.source_document_text,
        )

    def test_26_comparison_action_requires_previous_version(self):
        version = self.make_version()
        with self.assertRaises(UserError):
            version.with_user(self.editor).action_print_comparison()

    def test_27_soft_competency_refresh_never_bypasses_source_security(self):
        version = self.make_version()
        if not self.env.registry.get("onehr.position.competency"):
            action = version.with_user(
                self.editor
            ).action_refresh_competency_snapshot()
            self.assertEqual(action["tag"], "display_notification")
        else:
            # The JD Editor role does not imply Career/Succession HRBP authority.
            # If Career is installed, normal source ACL/rules remain authoritative.
            with self.assertRaises(AccessError):
                version.with_user(
                    self.editor
                ).action_refresh_competency_snapshot()

    def test_28_database_table_names_are_safe_and_canonical(self):
        self.assertEqual(self.env["onehr.jd"]._table, "onehr_jd")
        self.assertEqual(
            self.env["onehr.jd.version"]._table,
            "onehr_jd_version",
        )
        self.assertLessEqual(len(self.env["onehr.jd"]._table.encode()), 63)
        self.assertLessEqual(
            len(self.env["onehr.jd.version"]._table.encode()),
            63,
        )

    def test_29_company_rule_blocks_other_company_template(self):
        other = self.env["onehr.jd"].with_user(
            self.other_editor
        ).create(
            {
                "name": "Other Company Template",
                "company_id": self.other_company.id,
                "is_template": True,
                "job_family_id": self.other_job_family.id,
            }
        )
        visible = self.env["onehr.jd"].with_user(self.editor).search(
            [("code", "=", other.code)]
        )
        self.assertFalse(visible)

    def test_30_portal_contract_returns_only_published_business_content(self):
        jd = self.make_jd()
        self.publish_version(self.make_version(jd))
        payload = self.env["onehr.jd"].with_user(
            self.editor
        ).onehr_jd_portal_payload(position=self.position)

        self.assertEqual(payload["jd_reference"], jd.code)
        self.assertIn("key_responsibilities", payload)
        self.assertNotIn("approval_comments", payload)
        self.assertNotIn("source_document_text", payload)

