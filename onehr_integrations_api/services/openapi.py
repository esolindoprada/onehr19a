OPENAPI_DOCUMENT = {
    "openapi": "3.0.3",
    "info": {
        "title": "OneHR Integrations API",
        "version": "1.0.0",
        "description": "Versioned enterprise integration boundary for OneHR NEW on Odoo 19 CE.",
    },
    "servers": [{"url": "/onehr/api/v1"}],
    "components": {
        "securitySchemes": {
            "ApiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
            "RequestSignature": {"type": "apiKey", "in": "header", "name": "X-Signature"},
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                            "details": {"type": "object"},
                        },
                    },
                },
            }
        },
    },
    "paths": {
        "/health": {"get": {"summary": "Health and installed capability check", "security": [{"ApiKey": []}]}},
        "/employees": {"get": {"summary": "Read company-scoped employee directory", "security": [{"ApiKey": []}]}},
        "/attendance": {"post": {"summary": "Ingest attendance interval", "security": [{"ApiKey": []}, {"RequestSignature": []}]}},
        "/recruitment/applicants": {"post": {"summary": "Create recruitment applicant", "security": [{"ApiKey": []}]}},
        "/timeoff/requests": {"post": {"summary": "Create governed time-off request", "security": [{"ApiKey": []}]}},
        "/approvals/events": {"post": {"summary": "Approve/reject through Workflow Approval authority", "security": [{"ApiKey": []}]}},
        "/documents/esign/status": {"post": {"summary": "Apply provider e-sign status", "security": [{"ApiKey": []}]}},
        "/learning/results": {"post": {"summary": "Ingest external learning result", "security": [{"ApiKey": []}]}},
        "/learning/enrollments": {"post": {"summary": "Create external learning enrollment", "security": [{"ApiKey": []}]}},
        "/appraisals/ratings": {"post": {"summary": "Ingest external appraisal rating", "security": [{"ApiKey": []}]}},
        "/career/assessments": {"post": {"summary": "Ingest talent assessment", "security": [{"ApiKey": []}]}},
        "/payroll/results": {"post": {"summary": "Ingest payroll result", "security": [{"ApiKey": []}]}},
        "/policies/evidence": {"post": {"summary": "Submit policy evidence", "security": [{"ApiKey": []}]}},
    },
}
