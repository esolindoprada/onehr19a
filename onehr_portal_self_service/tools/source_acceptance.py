
#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import hashlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODELS = {
    "onehr.portal.request.type",
    "onehr.portal.request.stage",
    "onehr.portal.request",
}
EXPECTED_DEPS = {
    "onehr_corehr", "onehr_security", "portal", "web", "mail",
}
SOFT_DEPENDENCIES = {
    "onehr_timeoff", "onehr_learning", "onehr_appraisal", "onehr_document",
    "onehr_payroll_bridge", "onehr_job_description", "onehr_pnp", "onehr_sop",
    "onehr_career_succession", "onehr_multicompany_branch", "onehr_integrations_api",
    "onehr_analytics", "onehr_discipline",
}
EXPECTED_VERSION = "19.0.1.0.2"
EXPECTED_TEST_METHODS = 34
PG_IDENTIFIER_MAX = 63

passes = []
failures = []
warnings = []


def ok(label):
    passes.append(label)
    print(f"PASS: {label}")


def fail(label, detail=""):
    failures.append((label, detail))
    print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))


def warn(label):
    warnings.append(label)
    print(f"WARN: {label}")


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


# ------------------------------------------------------------------
# HARD GATE 0 — project / manifest identity
# ------------------------------------------------------------------
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR Portal Self-Service":
    ok("HARD GATE 0 exact addon identity")
else:
    fail("HARD GATE 0 exact addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly CoreHR + Security + Portal + Web + Mail")
else:
    fail("Hard dependency topology", f"found={sorted(deps)}")

unexpected_soft = deps & SOFT_DEPENDENCIES
if not unexpected_soft:
    ok("Optional OneHR bridges remain soft dependencies")
else:
    fail("Soft dependency ownership", f"unexpected hard deps={sorted(unexpected_soft)}")

missing_data = [item for item in manifest.get("data", []) if not (ROOT / item).is_file()]
if not missing_data:
    ok("All manifest data files exist")
else:
    fail("Manifest data files", f"missing={missing_data}")

# ------------------------------------------------------------------
# Python syntax / model inventory / style
# ------------------------------------------------------------------
python_files = [p for p in sorted(ROOT.rglob("*.py")) if "__pycache__" not in p.parts]
python_trees = {}
for path in python_files:
    try:
        python_trees[path] = ast.parse(read(path))
    except SyntaxError as exc:
        fail("Python syntax", f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

# HARD GATE 5/12 — duplicate class methods are hidden overrides and make manual
# maintenance unsafe. Reject them before runtime.
duplicate_class_methods = []
for path, tree in python_trees.items():
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        seen = {}
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name in seen:
                    duplicate_class_methods.append(
                        f"{path.relative_to(ROOT)}:{node.name}:{item.name}"
                    )
                seen[item.name] = item.lineno
if duplicate_class_methods:
    fail("HARD GATE 5/12 no duplicate class method definitions", ", ".join(duplicate_class_methods))
else:
    ok("HARD GATE 5/12 no duplicate class method definitions")

model_sources = "\n".join(read(p) for p in sorted((ROOT / "models").glob("*.py")))
declared_models = set()
for path in sorted((ROOT / "models").glob("*.py")):
    tree = python_trees.get(path)
    if not tree:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name) and target.id == "_name"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                    and node.value.value.startswith("onehr.portal.")
                ):
                    declared_models.add(node.value.value)

if declared_models == EXPECTED_MODELS:
    ok("HARD GATE 4 exact three persistent Portal business models")
else:
    fail("HARD GATE 4 model inventory", f"found={sorted(declared_models)}")

for model in sorted(EXPECTED_MODELS):
    if f'_name = "{model}"' in model_sources:
        ok(f"Persistent model implemented: {model}")
    else:
        fail(f"Persistent model implemented: {model}")

if model_sources.count('_inherit = ["onehr.mixin.audit"]') >= 3:
    ok("All Portal business models use approved OneHR audit mixin")
else:
    fail("OneHR audit mixin coverage")

if "mail.thread" not in model_sources and "mail.activity.mixin" not in model_sources:
    ok("No duplicate direct chatter mixin ownership")
else:
    fail("Audit mixin ownership", "direct mail mixin found")

runtime_py = "\n".join(
    read(p) for p in python_files
    if "tests" not in p.parts and "tools" not in p.parts
)
for pattern, label in (
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"except\s+Exception", "No broad Exception swallowing in runtime source"),
    (r"while\s+True\s*:", "No unbounded retry loop"),
    (r"_sql_constraints", "No legacy _sql_constraints"),
):
    if re.search(pattern, runtime_py):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

# Odoo 19 rejects explicit @api.depends strings that end in .id.
bad_depends = []
for path, tree in python_trees.items():
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "api"
            and func.attr == "depends"
        ):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value == "id" or arg.value.endswith(".id"):
                    bad_depends.append(f"{path.relative_to(ROOT)}:{arg.value}")
if bad_depends:
    fail("Odoo 19 @api.depends contract", ", ".join(bad_depends))
else:
    ok("Odoo 19 @api.depends contains no explicit .id dependency")

# Tutorial scaffold paths must not survive the full replacement.
legacy_paths = [
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
    ROOT / "controllers" / "controllers.py",
    ROOT / "demo",
]
remaining = [str(p.relative_to(ROOT)) for p in legacy_paths if p.exists()]
if remaining:
    fail("Tutorial scaffold removed", f"remaining={remaining}")
else:
    ok("Tutorial scaffold removed completely")

if "onehr_portal_self_service.onehr_portal_self_service" not in runtime_py:
    ok("No tutorial model residue")
else:
    fail("No tutorial model residue")

# ------------------------------------------------------------------
# XML / Odoo 19 UI compatibility
# ------------------------------------------------------------------
xml_files = sorted(ROOT.rglob("*.xml"))
xml_roots = {}
for path in xml_files:
    try:
        xml_roots[path] = ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail("XML syntax", f"{path.relative_to(ROOT)}: {exc}")
if len(xml_roots) == len(xml_files):
    ok(f"XML syntax ({len(xml_files)} files)")

# Odoo 19 ir.actions.act_window exposes group_ids, not the invalid groups_id.
# This check is intentionally scoped to the runtime defect proven on 2026-08-29.
bad_act_window_group_fields = []
bulk_action_group_ids_ok = False
for path, xml_root in xml_roots.items():
    for record in xml_root.iter("record"):
        if record.attrib.get("model") != "ir.actions.act_window":
            continue
        field_names = {
            field.attrib.get("name")
            for field in record.findall("field")
            if field.attrib.get("name")
        }
        if "groups_id" in field_names:
            bad_act_window_group_fields.append(
                f"{path.relative_to(ROOT)}:{record.attrib.get('id', '<no-id>')}"
            )
        if record.attrib.get("id") == "action_onehr_portal_bulk_approval_wizard":
            bulk_action_group_ids_ok = (
                "group_ids" in field_names and "groups_id" not in field_names
            )

if bad_act_window_group_fields:
    fail(
        "Odoo 19 ir.actions.act_window group field",
        "invalid groups_id found: " + ", ".join(sorted(bad_act_window_group_fields)),
    )
else:
    ok("Odoo 19 ir.actions.act_window uses group_ids, never groups_id")

if bulk_action_group_ids_ok:
    ok("Bulk Request Decision action keeps Manager/HR restriction through group_ids")
else:
    fail(
        "Bulk Request Decision action group restriction",
        "expected Odoo 19 group_ids field on bound window action",
    )

view_paths = sorted((ROOT / "views").glob("*.xml"))
view_text = "\n".join(read(p) for p in view_paths)
if "<tree" not in view_text and "</tree>" not in view_text:
    ok("Odoo 19 list syntax uses <list>")
else:
    fail("Odoo 19 list syntax", "legacy tree tag found")

if "attrs=" not in view_text and not re.search(r"\sstates\s*=", view_text):
    ok("Odoo 19 direct view modifiers")
else:
    fail("Odoo 19 direct view modifiers", "legacy attrs/states found")

bad_search_groups = []
for path, root in xml_roots.items():
    if "views" not in path.parts:
        continue
    for search in root.iter("search"):
        for group in search.iter("group"):
            if group.attrib:
                bad_search_groups.append(f"{path.relative_to(ROOT)}:{group.attrib}")
if bad_search_groups:
    fail("Odoo 19 search <group> contract", "; ".join(bad_search_groups))
else:
    ok("Odoo 19 search <group> elements have no attributes")

# Dedicated list/form/search per persistent model.
view_blocks = re.findall(r'<record[^>]*model="ir\.ui\.view".*?</record>', view_text, re.S)
for model in sorted(EXPECTED_MODELS):
    blocks = [b for b in view_blocks if f'<field name="model">{model}</field>' in b]
    kinds = set()
    for block in blocks:
        if "<list" in block: kinds.add("list")
        if "<form" in block: kinds.add("form")
        if "<search" in block: kinds.add("search")
    if {"list", "form", "search"} <= kinds:
        ok(f"HARD GATE 7/8/9 List/Form/Search views: {model}")
    else:
        fail(f"HARD GATE 7/8/9 List/Form/Search views: {model}", f"found={sorted(kinds)}")

for label, token in {
    "Statusbar widgets": 'widget="statusbar"',
    "Smart buttons": "oe_stat_button",
    "Body form action buttons": 'class="btn-secondary"',
    "One2many row action buttons": '<button name="action_open_self"',
    "Chatter": "<chatter",
    "Kanban": "<kanban",
    "Calendar": "<calendar",
    "Pivot": "<pivot",
    "Graph": "<graph",
    "Badges": 'widget="badge"',
    "Ribbons": 'widget name="web_ribbon"',
}.items():
    if token in view_text:
        ok(f"HARD GATE 6 enterprise UI — {label}")
    else:
        fail(f"HARD GATE 6 enterprise UI — {label}")

# Object buttons must reference methods defined inside this bounded addon.
method_names = set()
for tree in python_trees.values():
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(node.name)
missing_methods = []
for path, root in xml_roots.items():
    for button in root.iter("button"):
        if button.attrib.get("type") == "object":
            name = button.attrib.get("name")
            if name and name not in method_names:
                missing_methods.append(f"{path.relative_to(ROOT)}:{name}")
if missing_methods:
    fail("Object button → Python method cross-reference", ", ".join(sorted(set(missing_methods))))
else:
    ok("Object button → Python method cross-reference")

# Portal HTTP trust boundary.
controller_text = read(ROOT / "controllers" / "portal.py")
if "auth=\"public\"" in controller_text or "auth='public'" in controller_text:
    fail("No public HR portal endpoint")
else:
    ok("All OneHR HR portal routes require authenticated users")
for route in ("/my/hr", "/my/hr/new", "/my/team"):
    if route in controller_text:
        ok(f"Portal route present: {route}")
    else:
        fail(f"Portal route present: {route}")
if "csrf_token" in read(ROOT / "views" / "portal_templates.xml"):
    ok("Portal POST forms include CSRF tokens")
else:
    fail("Portal POST forms include CSRF tokens")

portal_template_text = read(ROOT / "views" / "portal_templates.xml")
if "hr_request.message_ids" not in portal_template_text and "portal_messages" in portal_template_text:
    ok("HARD GATE 10 portal chatter excludes raw/internal message stream")
else:
    fail("HARD GATE 10 portal chatter privacy", "raw request.message_ids exposed to portal template")

if "message.subtype_id.internal" in controller_text:
    ok("HARD GATE 10 controller filters internal mail subtypes")
else:
    fail("HARD GATE 10 controller internal-message filter")

if 'request.env["ir.attachment"].create' not in controller_text and "attachments=attachment_payloads" in controller_text:
    ok("HARD GATE 10 portal uploads use governed mail.thread attachment path")
else:
    fail("HARD GATE 10 portal attachment trust boundary")

if "_max_total_attachment_bytes" in controller_text:
    ok("HARD GATE 3 portal upload count/per-file/total-size limits")
else:
    fail("HARD GATE 3 portal total attachment limit")

# ------------------------------------------------------------------
# HARD GATE 10 — security
# ------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_lines = [line for line in read(acl_path).splitlines() if line.strip()]
    acl_rows = list(csv.DictReader(acl_lines))
except Exception as exc:
    acl_rows = []
    fail("ACL CSV parse", str(exc))
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" not in read(acl_path):
    ok("HARD GATE 10 no broad base.group_user Portal CRUD")
else:
    fail("HARD GATE 10 least privilege", "base.group_user appears in Portal ACL")

request_source = read(ROOT / "models" / "request.py")
if "def _handle_approved_integration" in request_source and "if is_portal_hr(self.env):" in request_source:
    ok("HARD GATE 10 auto-execution never escalates non-HR approval authority")
else:
    fail("HARD GATE 10 auto-execution authority deferral")

security_xml = read(ROOT / "security" / "onehr_portal_security.xml")
rules_xml = read(ROOT / "security" / "onehr_portal_rules.xml")
for group in (
    "group_onehr_portal_employee",
    "group_onehr_portal_manager",
    "group_onehr_portal_hr",
    "group_onehr_portal_admin",
):
    if group in security_xml:
        ok(f"Security role present: {group}")
    else:
        fail(f"Security role present: {group}")

if 'model="res.groups.privilege"' in security_xml:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

# Odoo 19 user-type ownership: Portal is base.group_portal.
# The older/nonexistent portal.group_portal XML ID must never regress into this addon.
if "portal.group_portal" in security_xml:
    fail(
        "Odoo 19 Portal user-type XML ID",
        "portal.group_portal is invalid; Odoo 19 owns this group as base.group_portal",
    )
elif "base.group_portal" in security_xml:
    ok("Odoo 19 Portal user type uses base.group_portal")
else:
    fail("Odoo 19 Portal user-type XML ID", "base.group_portal is not referenced")

for token, label in (
    ("employee_user_id", "Employee self-scope uses stored user boundary"),
    ("manager_user_id", "Manager direct-team scope uses stored user boundary"),
    ("company_ids", "Company boundary uses allowed companies"),
):
    if token in rules_xml:
        ok(label)
    else:
        fail(label)

if "@api.ondelete(at_uninstall=False)" in model_sources:
    ok("Historical evidence deletion guards present")
else:
    fail("Historical evidence deletion guards")

# ------------------------------------------------------------------
# HARD GATE 11 — database identifiers / ORM naming safety
# ------------------------------------------------------------------
model_tables = [name.replace(".", "_") for name in EXPECTED_MODELS]
long_identifiers = [(name, len(name)) for name in model_tables if len(name) > PG_IDENTIFIER_MAX]

# Collect explicit Many2many relation-table strings from models. We only flag likely relation names.
relation_names = sorted(set(re.findall(r'["\']([a-z0-9_]+_rel)["\']', model_sources)))
long_relations = [(name, len(name)) for name in relation_names if len(name) > PG_IDENTIFIER_MAX]
if not long_identifiers and not long_relations:
    ok("HARD GATE 11 model/relation identifiers stay within PostgreSQL limit")
else:
    fail("HARD GATE 11 PostgreSQL identifier length", f"models={long_identifiers}, relations={long_relations}")

if "onehr_port_req_att_rel" in model_sources:
    ok("HARD GATE 11 explicit short Portal attachment relation name")
else:
    fail("HARD GATE 11 explicit attachment relation name")

if "models.Constraint(" in model_sources and "_sql_constraints" not in model_sources:
    ok("HARD GATE 11 Odoo 19 models.Constraint policy")
else:
    fail("HARD GATE 11 Odoo constraint policy")

# ------------------------------------------------------------------
# Functional completeness / integration contract
# ------------------------------------------------------------------
full_business_source = model_sources + "\n" + controller_text
functional_tokens = (
    ("action_submit", "Employee submission"),
    ("action_manager_approve", "Manager approval"),
    ("action_manager_reject", "Manager rejection"),
    ("action_hr_approve", "HR approval"),
    ("action_hr_reject", "HR rejection"),
    ("action_start_processing", "HR processing"),
    ("action_complete", "Completion"),
    ("action_cancel", "Cancellation"),
    ("_cron_sla_monitor", "SLA reminder monitor"),
    ("_search_is_sla_overdue", "Searchable SLA overdue status"),
    ("profile_change_json", "Profile Change payload"),
    ("_dispatch_timeoff", "Time Off soft hand-off"),
    ("onehr_external_enroll", "Learning accepted service contract"),
    ("_dispatch_document", "Document soft hand-off"),
    ("onehr_employee_appraisal_payload", "Appraisal self-service contract"),
    ("onehr_portal_payslip_payload", "Payroll employee-safe contract"),
    ("onehr_jd_portal_payload", "Job Description employee-safe contract"),
    ("onehr_pnp_ack_status", "PnP acknowledgement contract"),
    ("onehr_sop_ack_status", "SOP acknowledgement contract"),
    ("onehr_employee_career_payload", "Career employee-safe contract"),
    ("/my/hr", "My HR portal"),
    ("/my/team", "My Team portal"),
)
for token, label in functional_tokens:
    if token in full_business_source:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

if "onehr.discipline" not in full_business_source:
    ok("Confidential Discipline domain is not exposed to employee portal")
else:
    fail("Discipline confidentiality boundary", "discipline model reference found")

# ------------------------------------------------------------------
# Tests and documentation
# ------------------------------------------------------------------
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    tree = ast.parse(read(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_methods.append((path.name, node.name))
if len(test_methods) == EXPECTED_TEST_METHODS:
    ok(f"Runtime test inventory exactly {EXPECTED_TEST_METHODS} methods")
else:
    fail("Runtime test inventory", f"expected={EXPECTED_TEST_METHODS}, found={len(test_methods)}")

if all("@tagged" in read(p) for p in sorted((ROOT / "tests").glob("test_*.py"))):
    ok("Runtime test suites are post-install tagged")
else:
    fail("Runtime test suite tags")

mandatory_docs = {
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_PRIVACY_MATRIX.md",
    "DATABASE_IDENTIFIER_ORM_NAMING_SAFETY.md",
    "INTEGRATION_CONTRACT.md",
    "UPSTREAM_CONTRACT_AND_SCOPE_AUDIT.md",
    "MODEL_REGISTRY_ALIGNMENT.md",
    "CODEX_BOUNDED_IMPLEMENTATION_CONTRACT.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE.md",
    "IMPLEMENTATION_REPORT.md",
    "SCOPE_ISOLATION_REPORT.md",
    "ROOT_GUARDRAIL_REFERENCE.md",
    "BOUNDED_RUNTIME_REPAIR_ATTEMPT_2.md",
    "BOUNDED_RUNTIME_REPAIR_TASK_20260829_ATTEMPT_1.md",
}
missing_docs = sorted(name for name in mandatory_docs if not (ROOT / "docs" / name).is_file())
if missing_docs:
    fail("Mandatory Enterprise documentation", f"missing={missing_docs}")
else:
    ok("Mandatory Enterprise documentation set")

guardrail = read(ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for gate in range(16):
    if f"HARD GATE {gate}" in guardrail:
        ok(f"Guardrail contains HARD GATE {gate}")
    else:
        fail(f"Guardrail contains HARD GATE {gate}")

for token, label in (
    ("CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER", "Codex bounded-worker role"),
    ("MAX_CODEX_ATTEMPTS_PER_TASK: 2", "Codex retry limit = 2"),
    ("MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1", "Same-root-cause repeat limit = 1"),
):
    if token in guardrail:
        ok(label)
    else:
        fail(label)

registry = read(ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry:
    warn("Exact Master Model Registry ED rows remain pending; classifications were not invented")
else:
    fail("Registry ED pending marker")

if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else:
    fail("Odoo CE UI ownership", "unexpected Gantt view found")

print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared_models)}")
print(f"EXPLICIT_RELATION_NAMES={len(relation_names)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_PORTAL_SELF_SERVICE_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY=NO")

