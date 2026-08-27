{
    "name": "OneHR Recruitment",
    "summary": "Enterprise recruitment, interviews, offers, preboarding and recruitment analytics for OneHR",
    "description": """
OneHR Recruitment extends Odoo 19 Community Edition recruitment with governed
requisitions, structured interview scorecards, offer approval, preboarding
orchestration and immutable recruitment snapshots while preserving Odoo-native
applicant, stage, job and talent-pool ownership.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Recruitment",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "license": "LGPL-3",
    "depends": [
        "onehr_corehr",
        "onehr_security",
        "onehr_workflow_approval",
        "hr_recruitment",
    ],
    "data": [
        "security/onehr_recruitment_groups.xml",
        "security/ir.model.access.csv",
        "security/onehr_recruitment_rules.xml",
        "data/recruitment_sequence_data.xml",
        "views/requisition_views.xml",
        "views/interview_views.xml",
        "views/offer_views.xml",
        "views/preboarding_views.xml",
        "views/source_metric_views.xml",
        "views/native_recruitment_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
