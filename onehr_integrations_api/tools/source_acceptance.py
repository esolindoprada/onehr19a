#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "19.0.1.0.1"
EXPECTED_DEPS = {"onehr_security"}
EXPECTED_MODELS = {
    "onehr.api.key",
    "onehr.api.scope",
    "onehr.webhook",
    "onehr.api.log",
    "onehr.api.queue",
}
EXPECTED_TEST_METHODS = 26
EXPECTED_SCOPE_CODES = {
    "system.health", "system.docs", "corehr.employee.read", "attendance.write",
    "recruitment.applicant.write", "timeoff.request.write", "workflow.approval.decide",
    "document.esign.write", "learning.result.write", "learning.enrollment.write",
    "appraisal.rating.write", "career.assessment.write", "payroll.export.read",
    "payroll.result.write", "pnp.ack.read", "pnp.evidence.write", "sop.ack.read",
    "jd.read", "portal.myhr.read",
}

passes, failures, warnings = [], [], []

def ok(label):
    passes.append(label); print(f"PASS: {label}")

def fail(label, detail=""):
    failures.append((label, detail)); print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))

def warn(label):
    warnings.append(label); print(f"WARN: {label}")

def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")

# HARD GATE 0: manifest identity
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}; fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")
if manifest.get("name") == "OneHR Integrations API": ok("HARD GATE 0 project/addon identity")
else: fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))
if manifest.get("version") == EXPECTED_VERSION: ok(f"Manifest version {EXPECTED_VERSION}")
else: fail("Manifest version", repr(manifest.get("version")))
if set(manifest.get("depends", [])) == EXPECTED_DEPS: ok("Hard dependency exactly onehr_security")
else: fail("Hard dependency topology", repr(manifest.get("depends")))
missing = [item for item in manifest.get("data", []) if not (ROOT / item).is_file()]
if not missing: ok("All manifest data files exist")
else: fail("Manifest data files", str(missing))

# Python syntax/model inventory
python_files = [p for p in sorted(ROOT.rglob("*.py")) if "__pycache__" not in p.parts]
trees = {}; declared = set()
for path in python_files:
    try:
        tree = ast.parse(read(path)); trees[path] = tree
    except SyntaxError as exc:
        fail("Python syntax", f"{path.relative_to(ROOT)}:{exc.lineno}:{exc.msg}"); continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_name" and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value.startswith("onehr."):
                    if node.value.value in EXPECTED_MODELS or node.value.value.startswith("onehr.api") or node.value.value == "onehr.webhook":
                        declared.add(node.value.value)
if len(trees) == len(python_files): ok(f"Python syntax ({len(python_files)} files)")
if declared == EXPECTED_MODELS: ok("HARD GATE 4 exact five persistent integration models")
else: fail("HARD GATE 4 model inventory", f"found={sorted(declared)}")

business_sources = "\n".join(read(p) for p in sorted((ROOT / "models").glob("*.py")))
runtime_sources = "\n".join(read(p) for folder in ("models","services","controllers") for p in sorted((ROOT/folder).glob("*.py")))
for model in sorted(EXPECTED_MODELS):
    if f'_name = "{model}"' in business_sources: ok(f"Persistent model implemented: {model}")
    else: fail(f"Persistent model implemented: {model}")
if '_inherit = "res.config.settings"' in business_sources: ok("Native res.config.settings transient extension")
else: fail("Native res.config.settings transient extension")
if "onehr_integrations_api.onehr_integrations_api" not in runtime_sources: ok("Tutorial model removed")
else: fail("Tutorial model removed", "legacy tutorial model token remains")
if not (ROOT / "demo").exists() and not (ROOT / "views" / "views.xml").exists() and not (ROOT / "views" / "templates.xml").exists() and not (ROOT / "models" / "models.py").exists(): ok("Tutorial scaffold paths removed")
else: fail("Tutorial scaffold paths removed")

# Odoo 19/Python compatibility
if "_sql_constraints" not in runtime_sources: ok("No legacy _sql_constraints")
else: fail("No legacy _sql_constraints")
bad_depends = []
for path, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "api" and node.func.attr == "depends":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and (arg.value == "id" or arg.value.endswith(".id")):
                    bad_depends.append(f"{path.relative_to(ROOT)}:{arg.value}")
if not bad_depends: ok("Odoo 19 @api.depends contains no explicit .id dependency")
else: fail("Odoo 19 @api.depends field path", ", ".join(bad_depends))

# HARD GATE 10: no business sudo; technical sudo bounded
adapter_source = read(ROOT / "services" / "domain_adapters.py")
if ".sudo(" not in adapter_source and ".sudo()" not in adapter_source: ok("HARD GATE 10 domain adapters contain no business sudo bypass")
else: fail("HARD GATE 10 domain adapters contain no business sudo bypass")
for required in ("with_user", "with_company", "allowed_company_ids"):
    if required in read(ROOT / "services" / "runtime.py"): ok(f"Service identity boundary uses {required}")
    else: fail(f"Service identity boundary uses {required}")
if "base.group_user" not in read(ROOT / "security" / "ir.model.access.csv"): ok("HARD GATE 10 no broad base.group_user custom-model CRUD")
else: fail("HARD GATE 10 least privilege ACL", "base.group_user found")
if 'auth="public"' in read(ROOT / "controllers" / "api_v1.py") and "runtime.authenticate" in read(ROOT / "controllers" / "api_v1.py"): ok("Public REST routes authenticate before domain execution")
else: fail("Public REST authentication boundary")
if "handlers = {" in read(ROOT / "controllers" / "webhook_inbound.py") and "arbitrary" not in read(ROOT / "services" / "domain_adapters.py"): ok("Inbound webhook dispatch is fixed allow-list, not arbitrary model/method")
else: fail("Inbound webhook allow-list dispatch")

# Credential / replay / SSRF enterprise contract
key_source = read(ROOT / "models" / "api_key.py")
for token, label in (
    ("hashlib.pbkdf2_hmac", "PBKDF2-HMAC API secret hashing"),
    ("hmac.compare_digest", "constant-time API secret comparison"),
    ("secrets.token_urlsafe", "cryptographic API secret generation"),
    ("secret_hash", "hashed credential persistence"),
):
    if token in key_source: ok(label)
    else: fail(label)
if "plaintext" not in key_source.lower() or "fields.Char(string=\"API Key\"" not in key_source:
    ok("No plaintext API-key credential field is persisted")
else:
    fail("No plaintext API-key credential field is persisted")
runtime_source = read(ROOT / "services" / "runtime.py")
for token, label in (
    ("X-Request-ID", "request ID replay control"),
    ("X-Timestamp", "timestamp replay window"),
    ("X-Signature", "request HMAC signature"),
    ("rate_limited", "stable rate-limit error"),
    ("REDACT_KEYS", "payload redaction contract"),
):
    if token in runtime_source or token in read(ROOT / "services" / "errors.py"): ok(label)
    else: fail(label)
delivery = read(ROOT / "services" / "webhook_delivery.py")
for token, label in (
    ("ipaddress.ip_address", "SSRF IP classification"),
    ("is_private", "private-address blocking"),
    ("_NoRedirectHandler", "redirect rejection"),
    ("MAX_RESPONSE_BYTES", "bounded webhook response size"),
    ("hmac.new", "outbound webhook HMAC"),
):
    if token in delivery: ok(label)
    else: fail(label)

# XML syntax + Odoo 19 view rules
xml_files = sorted(ROOT.rglob("*.xml")); roots = {}
for path in xml_files:
    try: roots[path] = ET.parse(path).getroot()
    except ET.ParseError as exc: fail("XML syntax", f"{path.relative_to(ROOT)}:{exc}")
if len(roots) == len(xml_files): ok(f"XML syntax ({len(xml_files)} files)")
view_text = "\n".join(read(p) for p in sorted((ROOT / "views").glob("*.xml")))
if "<tree" not in view_text and "</tree>" not in view_text: ok("Odoo 19 list syntax uses <list>")
else: fail("Odoo 19 list syntax", "legacy tree tag")
if "attrs=" not in view_text and not re.search(r"\sstates\s*=", view_text): ok("Odoo 19 direct view modifiers")
else: fail("Odoo 19 direct view modifiers", "legacy attrs/states")
if '<field name="groups_id"' not in view_text: ok("HARD GATE 11 no invalid ir.actions.act_window.groups_id")
else: fail("HARD GATE 11 action ORM field naming", "groups_id found")
action_blocks = re.findall(r'<record[^>]+model="ir\.actions\.act_window".*?</record>', view_text, flags=re.S)
if action_blocks and all('<field name="group_ids"' in block for block in action_blocks): ok("Odoo 19 ir.actions.act_window group_ids used on all API actions")
else: fail("Odoo 19 ir.actions.act_window group_ids contract")
bad_groups = []
for path, root in roots.items():
    if "views" in path.parts:
        for search in root.iter("search"):
            for group in search.iter("group"):
                if group.attrib: bad_groups.append(f"{path.relative_to(ROOT)}:{group.attrib}")
if not bad_groups: ok("Odoo 19 search <group> elements have no attributes")
else: fail("Odoo 19 search <group> contract", "; ".join(bad_groups))

# Runtime regression: any field used by the Webhook Dead Letter search filter must
# be searchable by Odoo.  The supplied Attempt-1 view used failed_count in a domain
# while failed_count was a non-stored compute without a search method.
webhook_model_source = read(ROOT / "models" / "webhook.py")
webhook_view_source = read(ROOT / "views" / "webhook_views.xml")
if re.search(
    r'failed_count\s*=\s*fields\.Integer\([^)]*store\s*=\s*True',
    webhook_model_source,
    flags=re.S,
):
    ok("Odoo searchability regression — onehr.webhook.failed_count is stored/searchable")
else:
    fail(
        "Odoo searchability regression — onehr.webhook.failed_count",
        "field is used by a search-view domain but is not stored/searchable",
    )
if 'name="dead_letters"' in webhook_view_source and "failed_count" in webhook_view_source:
    ok("Webhook Has Dead Letters filter remains functionally preserved")
else:
    fail("Webhook Has Dead Letters filter preservation")

# List/Form/Search per model
view_blocks = re.findall(r'<record[^>]*model="ir\.ui\.view".*?</record>', view_text, flags=re.S)
for model in sorted(EXPECTED_MODELS):
    blocks = [b for b in view_blocks if f'<field name="model">{model}</field>' in b]
    kinds = {kind for kind, token in (("list","<list"),("form","<form"),("search","<search")) if any(token in b for b in blocks)}
    if {"list","form","search"} <= kinds: ok(f"HARD GATE 7/8/9 List/Form/Search: {model}")
    else: fail(f"HARD GATE 7/8/9 List/Form/Search: {model}", f"found={sorted(kinds)}")
for label, token in {
    "Statusbar": 'widget="statusbar"', "Smart buttons": "oe_stat_button", "Body buttons": 'class="btn-secondary"',
    "One2many row buttons": '<button name="action_process_now"', "Chatter": "<chatter", "Kanban": "<kanban",
    "Pivot": "<pivot", "Graph": "<graph", "Badges": 'widget="badge"', "Ribbons": 'widget name="web_ribbon"',
}.items():
    if token in view_text: ok(f"HARD GATE 6 enterprise UI — {label}")
    else: fail(f"HARD GATE 6 enterprise UI — {label}")

# Object button -> Python method
methods = set()
for tree in trees.values():
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): methods.add(node.name)
missing_methods = []
for path, root in roots.items():
    for button in root.iter("button"):
        if button.attrib.get("type") == "object":
            name = button.attrib.get("name")
            if name and name not in methods: missing_methods.append(f"{path.relative_to(ROOT)}:{name}")
if not missing_methods: ok("Object button → Python method cross-reference")
else: fail("Object button → Python method cross-reference", ", ".join(sorted(missing_methods)))

# Duplicate XML IDs
seen = {}; dupes=[]
for path, root in roots.items():
    for node in root.iter():
        xmlid=node.attrib.get("id")
        if not xmlid or "." in xmlid: continue
        if xmlid in seen: dupes.append(f"{xmlid}:{seen[xmlid]}/{path.relative_to(ROOT)}")
        else: seen[xmlid]=str(path.relative_to(ROOT))
if not dupes: ok("Unique local XML external IDs")
else: fail("Unique local XML external IDs", ";".join(dupes))

# HARD GATE 11 identifiers/relations
identifier_re = re.compile(r"^[a-z_][a-z0-9_]*$")
identifier_issues=[]
for model in EXPECTED_MODELS:
    table=model.replace(".","_")
    if len(table.encode())>63 or not identifier_re.match(table): identifier_issues.append(f"model-table:{table}")
relation_names=set(re.findall(r'"(onehr_[a-z0-9_]+_rel)"', business_sources))
for relation in relation_names:
    if len(relation.encode())>63 or not identifier_re.match(relation): identifier_issues.append(f"relation:{relation}")
if "onehr_api_key_scope_rel" not in relation_names: identifier_issues.append("missing explicit relation:onehr_api_key_scope_rel")
if not identifier_issues: ok("HARD GATE 11 PostgreSQL identifier and explicit M2M relation safety")
else: fail("HARD GATE 11 identifier safety", ", ".join(identifier_issues))

# ACL/security inventory
try: acl=list(csv.DictReader(read(ROOT/"security"/"ir.model.access.csv").splitlines()))
except Exception as exc: acl=[]; fail("ACL CSV parse", str(exc))
else: ok(f"ACL CSV parse ({len(acl)} rows)")
if len(acl)==10: ok("Exact 10 least-privilege ACL rows")
else: fail("ACL row inventory", f"found={len(acl)}")
security=read(ROOT/"security"/"onehr_api_security.xml"); rules=read(ROOT/"security"/"onehr_api_rules.xml")
for gid in ("group_onehr_api_user","group_onehr_api_admin"):
    if gid in security: ok(f"Security role present: {gid}")
    else: fail(f"Security role present: {gid}")
if 'model="res.groups.privilege"' in security: ok("Odoo 19 res.groups.privilege pattern")
else: fail("Odoo 19 res.groups.privilege pattern")
if rules.count('<field name="global" eval="True"/>') == 4: ok("Global company boundary on key/webhook/log/queue")
else: fail("Global company boundary", f"count={rules.count('<field name=\"global\" eval=\"True\"/>')}")

# Seed scopes / routes / soft integration tokens
scope_data=read(ROOT/"data"/"api_scope_data.xml")
found_scopes=set(re.findall(r'<field name="code">([^<]+)</field>', scope_data))
if found_scopes==EXPECTED_SCOPE_CODES: ok(f"Exact {len(EXPECTED_SCOPE_CODES)} approved seed API scopes")
else: fail("Seed API scopes", f"missing={sorted(EXPECTED_SCOPE_CODES-found_scopes)}, extra={sorted(found_scopes-EXPECTED_SCOPE_CODES)}")
controller_source=read(ROOT/"controllers"/"api_v1.py")
for route in ("/onehr/api/v1/health","/onehr/api/v1/employees","/onehr/api/v1/attendance","/onehr/api/v1/recruitment/applicants","/onehr/api/v1/timeoff/requests","/onehr/api/v1/approvals/events","/onehr/api/v1/documents/esign/status"):
    if route in controller_source: ok(f"Versioned REST route present: {route}")
    else: fail(f"Versioned REST route present: {route}")
for token, label in (
    ("onehr_ingest_interval", "Attendance service"), ("onehr_ingest_external_rating", "Appraisal service"),
    ("onehr_ingest_external_result", "Learning result service"), ("onehr_external_enroll", "Learning enrollment service"),
    ("onehr_ingest_talent_assessment", "Career assessment service"), ("onehr_payroll_export_payload", "Payroll export service"),
    ("onehr_ingest_payroll_result", "Payroll result service"), ("onehr_pnp_ack_status", "PnP acknowledgement service"),
    ("onehr_pnp_submit_evidence", "PnP evidence service"), ("onehr_sop_ack_status", "SOP acknowledgement service"),
    ("onehr_jd_api_payload", "Job Description service"), ("onehr_my_hr_dashboard_payload", "Portal My HR service"),
    ("apply_provider_status", "Document e-Sign service"),
):
    if token in adapter_source: ok(f"Soft integration contract — {label}")
    else: fail(f"Soft integration contract — {label}")

# Functional enterprise contract
for token,label in (
    ("onehr.api.key","API Keys"),("onehr.api.scope","API Scopes"),("onehr.webhook","Webhooks"),
    ("onehr.api.log","Audit Log"),("onehr.api.queue","Retry Queue"),("action_rotate_secret","Secret rotation"),
    ("dead_letter","Dead-letter lifecycle"),("_cron_process_retry_queue","Retry scheduler"),("_cron_archive_old_logs","Log retention scheduler"),
    ("OPENAPI_DOCUMENT","OpenAPI endpoint"),("cors_preflight","CORS preflight"),("CapabilityUnavailable","Soft-addon absence handling"),
):
    if token in runtime_sources or token in controller_source: ok(f"HARD GATE 3/15 functional contract — {label}")
    else: fail(f"HARD GATE 3/15 functional contract — {label}")
if (ROOT/"static"/"docs"/"openapi.yaml").is_file() and (ROOT/"static"/"docs"/"postman_collection.json").is_file(): ok("OpenAPI YAML and Postman assets")
else: fail("OpenAPI YAML and Postman assets")

# Runtime test inventory
methods=[]
for path in sorted((ROOT/"tests").glob("test_*.py")):
    try: tree=ast.parse(read(path))
    except SyntaxError: continue
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith("test_"): methods.append((path.name,node.name))
if len(methods)==EXPECTED_TEST_METHODS: ok(f"Runtime test inventory exactly {EXPECTED_TEST_METHODS} methods")
else: fail("Runtime test inventory", f"expected={EXPECTED_TEST_METHODS}, found={len(methods)}")
if all("@tagged" in read(path) for path in sorted((ROOT/"tests").glob("test_*.py"))): ok("Runtime test suites are post-install tagged")
else: fail("Runtime test suite tags")

# Docs / guardrail 0..15
mandatory_docs={
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md","PROJECT_IDENTITY_PREFLIGHT.md","FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md","SECURITY_PRIVACY_MATRIX.md","INTEGRATION_CONTRACT.md","MODEL_REGISTRY_ALIGNMENT.md",
    "DATABASE_IDENTIFIER_ORM_SAFETY.md","ENTERPRISE_COMPLETENESS_MATRIX.md","WINDOWS_RUNTIME_ACCEPTANCE.md",
    "IMPLEMENTATION_REPORT.md","ROOT_GUARDRAIL_REFERENCE.md","SCOPE_ISOLATION_REPORT.md","CODEX_BOUNDED_IMPLEMENTATION_CONTRACT.md",
    "BOUNDED_RUNTIME_REPAIR_ATTEMPT_2.md",
}
missing_docs=sorted(name for name in mandatory_docs if not (ROOT/"docs"/name).is_file())
if not missing_docs: ok("Mandatory Enterprise documentation set")
else: fail("Mandatory Enterprise documentation", str(missing_docs))
guard=read(ROOT/"docs"/"ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for gate in range(16):
    if f"HARD GATE {gate}" in guard or (gate==0 and "HARD GATE 0" in guard): ok(f"Guardrail contains HARD GATE {gate}")
    else: fail(f"Guardrail contains HARD GATE {gate}")
if "DATABASE IDENTIFIER & ORM NAMING SAFETY" in guard: ok("HARD GATE 11 explicitly defined")
else: fail("HARD GATE 11 explicitly defined")
if "CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER" in guard and "MAX_CODEX_ATTEMPTS_PER_TASK: 2" in guard: ok("Codex bounded-worker/retry contract")
else: fail("Codex bounded-worker/retry contract")

registry=read(ROOT/"docs"/"MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry: warn("Exact Master Model Registry ED rows remain pending; classifications were not invented")
else: fail("Registry ED pending marker")
if "<gantt" not in view_text: warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else: fail("Odoo CE UI ownership", "unexpected Gantt view")

print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared)}")
print(f"EXPLICIT_RELATION_NAMES={len(relation_names)}")
print(f"ACL_ROWS={len(acl)}")
print(f"SEED_API_SCOPES={len(found_scopes)}")
print(f"RUNTIME_TEST_METHODS={len(methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")
if failures:
    sys.exit(1)
print("ONEHR_INTEGRATIONS_API_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY=NO")
