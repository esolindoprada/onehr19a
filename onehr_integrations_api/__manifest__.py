{
    "name": "OneHR Integrations API",
    "summary": "Secure versioned REST APIs, API keys, webhooks, throttling, retry queue and integration audit",
    "description": """
Enterprise integration boundary for OneHR NEW on Odoo 19 Community Edition.
The addon owns API-key authentication and scopes, versioned REST transport,
inbound/outbound HMAC webhooks, replay-safe request IDs, bounded throttling,
retry/dead-letter delivery, integration audit/KPI evidence, OpenAPI tooling and
security-preserving adapters into installed OneHR domain services.
""",
    "author": "PT Dua Empat Tujuh Open Source",
    "website": "https://odoocamp.net",
    "category": "Human Resources/Technical",
    "version": "19.0.1.0.1",
    "license": "LGPL-3",
    "depends": [
        "onehr_security",
    ],
    "data": [
        "security/onehr_api_security.xml",
        "security/ir.model.access.csv",
        "security/onehr_api_rules.xml",
        "data/api_sequence_data.xml",
        "data/api_scope_data.xml",
        "data/api_cron_data.xml",
        "views/api_key_views.xml",
        "views/api_scope_views.xml",
        "views/webhook_views.xml",
        "views/api_log_views.xml",
        "views/api_queue_views.xml",
        "views/settings_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
