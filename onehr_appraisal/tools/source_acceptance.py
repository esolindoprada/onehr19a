#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {
    "onehr.appraisal.cycle",
    "onehr.appraisal.form",
    "onehr.appraisal.score",
}
EXPECTED_DEPS = {
    "onehr_corehr",
    "onehr_security",
}
EXPECTED_VERSION = "19.0.1.0.1"
EXPECTED_TEST_METHODS = 24

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
# HARD GATE 0 / manifest identity
# ------------------------------------------------------------------
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR Appraisal":
    ok("HARD GATE 0 project/addon identity")
else:
    fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly CoreHR + Security")
else:
    fail("Hard dependency topology", f"found={sorted(deps)}")

missing_data = [
    item for item in manifest.get("data", [])
    if not (ROOT / item).is_file()
]
if not missing_data:
    ok("All manifest data files exist")
else:
    fail("Manifest data files", f"missing={missing_data}")

# ------------------------------------------------------------------
# HARD GATE 4 / Python model inventory and syntax
# ------------------------------------------------------------------
declared = set()
python_files = [
    path for path in sorted(ROOT.rglob("*.py"))
    if "__pycache__" not in path.parts
]
python_trees = {}
for path in python_files:
    try:
        tree = ast.parse(read(path))
        python_trees[path] = tree
    except SyntaxError as exc:
        fail(
            "Python syntax",
            f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}",
        )
        continue

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "_name"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and node.value.value.startswith("onehr.appraisal.")
            ):
                declared.add(node.value.value)

if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

if declared == EXPECTED_MODELS:
    ok("HARD GATE 4 exact three Appraisal persistent model names")
else:
    fail("HARD GATE 4 exact model inventory", f"found={sorted(declared)}")

business_sources = "\n".join(
    read(path) for path in sorted((ROOT / "models").glob("*.py"))
)
for model_name in sorted(EXPECTED_MODELS):
    model_token = f'_name = "{model_name}"'
    if model_token in business_sources:
        ok(f"Persistent model implemented: {model_name}")
    else:
        fail(f"Persistent model implemented: {model_name}")

if business_sources.count('_inherit = ["onehr.mixin.audit"]') >= 3:
    ok("All three Appraisal business models use approved OneHR audit mixin")
else:
    fail("Approved OneHR audit mixin coverage")

if "mail.thread" not in business_sources and "mail.activity.mixin" not in business_sources:
    ok("No duplicate direct chatter mixin ownership in Appraisal models")
else:
    fail("Audit mixin ownership", "direct mail.thread/activity mixin found")

# Odoo 19 rejects explicit dependency paths ending in ".id".
bad_depends_id = []
for path, tree in python_trees.items():
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_depends = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "api"
            and func.attr == "depends"
        )
        if not is_depends:
            continue
        for arg in node.args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and (arg.value == "id" or arg.value.endswith(".id"))
            ):
                bad_depends_id.append(
                    f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', '?')}:{arg.value}"
                )

if bad_depends_id:
    fail(
        "Odoo 19 @api.depends field-path contract",
        "explicit id dependency found: " + ", ".join(bad_depends_id),
    )
else:
    ok("Odoo 19 @api.depends contains no explicit .id dependency")

# ------------------------------------------------------------------
# Tutorial/scaffold removal and forbidden runtime patterns
# ------------------------------------------------------------------
runtime_paths = [
    ROOT / "__init__.py",
    ROOT / "__manifest__.py",
]
for folder in ("models", "security", "views", "data", "report"):
    runtime_paths.extend(
        path for path in sorted((ROOT / folder).rglob("*"))
        if path.is_file()
    )
runtime_source = "\n".join(
    read(path)
    for path in runtime_paths
    if path.suffix.lower() in {".py", ".xml", ".csv"}
)

for legacy_path in (
    ROOT / "controllers",
    ROOT / "demo",
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
):
    if legacy_path.exists():
        fail("Tutorial scaffold removed", f"legacy path remains: {legacy_path.relative_to(ROOT)}")
if not any(item[0] == "Tutorial scaffold removed" for item in failures):
    ok("Tutorial scaffold removed completely")

for token in (
    "onehr_appraisal.onehr_appraisal",
    "class OnehrAppraisal",
    "/onehr_appraisal/onehr_appraisal",
):
    if token in runtime_source:
        fail("No tutorial model/controller residue", token)
if not any(item[0] == "No tutorial model/controller residue" for item in failures):
    ok("No tutorial model/controller residue")

for pattern, label in (
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"auth\s*=\s*['\"]public['\"]", "No public unauthenticated Appraisal controller"),
):
    if re.search(pattern, runtime_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

# ------------------------------------------------------------------
# Odoo 19 XML / view compatibility
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

view_text = "\n".join(read(path) for path in sorted((ROOT / "views").glob("*.xml")))

if "<tree" in view_text or "</tree>" in view_text:
    fail("Odoo 19 list syntax", "legacy tree tag found")
else:
    ok("Odoo 19 list syntax uses <list>")

if "attrs=" in view_text or re.search(r"\sstates\s*=", view_text):
    fail("Odoo 19 direct view modifiers", "legacy attrs/states found")
else:
    ok("Odoo 19 direct view modifiers")

# Search <group> must have no attributes in the current Odoo 19 contract.
bad_search_groups = []
for path, xml_root in xml_roots.items():
    if "views" not in path.parts:
        continue
    for search in xml_root.iter("search"):
        for group in search.iter("group"):
            if group.attrib:
                bad_search_groups.append(
                    f"{path.relative_to(ROOT)}:{group.attrib}"
                )
if bad_search_groups:
    fail("Odoo 19 search <group> contract", "; ".join(bad_search_groups))
else:
    ok("Odoo 19 search <group> elements have no attributes")

# If date filters are added later, only valid Odoo 19 internal period IDs are accepted.
valid_default_period = re.compile(
    r"^(month(?:[+-]\d+)?|year(?:[+-]\d+)?|"
    r"first_quarter|second_quarter|third_quarter|fourth_quarter|"
    r"custom_[A-Za-z0-9_]+)$"
)
bad_periods = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter("filter"):
        value = node.attrib.get("default_period")
        if value and not valid_default_period.match(value):
            bad_periods.append(f"{path.relative_to(ROOT)}:{value}")
if bad_periods:
    fail("Odoo 19 date-filter default_period", "; ".join(bad_periods))
else:
    ok("Odoo 19 date-filter default_period contract")

# Dedicated List/Form/Search for every approved persistent model.
view_blocks = re.findall(
    r'<record[^>]*model="ir\.ui\.view".*?</record>',
    view_text,
    flags=re.S,
)
for model in sorted(EXPECTED_MODELS):
    blocks = [
        block for block in view_blocks
        if f'<field name="model">{model}</field>' in block
    ]
    kinds = set()
    for block in blocks:
        if "<list" in block:
            kinds.add("list")
        if "<form" in block:
            kinds.add("form")
        if "<search" in block:
            kinds.add("search")
    if {"list", "form", "search"} <= kinds:
        ok(f"HARD GATE 7/8/9 List/Form/Search views: {model}")
    else:
        fail(
            f"HARD GATE 7/8/9 List/Form/Search views: {model}",
            f"found={sorted(kinds)}",
        )

# Enterprise UI evidence.
for label, token in {
    "Statusbar widgets": 'widget="statusbar"',
    "Smart buttons": "oe_stat_button",
    "Body form action buttons": 'class="btn-secondary"',
    "One2many row action buttons": "<button ",
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

# XML object buttons must have a Python method somewhere in this bounded addon.
method_names = set()
for tree in python_trees.values():
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(node.name)

missing_button_methods = set()
for path, xml_root in xml_roots.items():
    for button in xml_root.iter("button"):
        if button.attrib.get("type") == "object":
            name = button.attrib.get("name")
            if name and name not in method_names:
                missing_button_methods.add(f"{path.relative_to(ROOT)}:{name}")
if missing_button_methods:
    fail("Object button → Python method cross-reference", ", ".join(sorted(missing_button_methods)))
else:
    ok("Object button → Python method cross-reference")

# Duplicate local XML IDs can create loader ambiguity.
seen_ids = {}
duplicate_ids = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter():
        xml_id = node.attrib.get("id")
        if not xml_id:
            continue
        # Fully qualified external IDs deliberately update sibling-owned records.
        if "." in xml_id:
            continue
        if xml_id in seen_ids:
            duplicate_ids.append(
                f"{xml_id}: {seen_ids[xml_id]} / {path.relative_to(ROOT)}"
            )
        else:
            seen_ids[xml_id] = str(path.relative_to(ROOT))
if duplicate_ids:
    fail("Unique local XML external IDs", "; ".join(duplicate_ids))
else:
    ok("Unique local XML external IDs")

# ------------------------------------------------------------------
# Security hard gates
# ------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(csv.DictReader(read(acl_path).splitlines()))
except Exception as exc:
    fail("ACL CSV parse", str(exc))
    acl_rows = []
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" in read(acl_path):
    fail("HARD GATE 10 least privilege", "base.group_user appears in Appraisal ACL")
else:
    ok("HARD GATE 10 no broad base.group_user Appraisal CRUD")

security_xml = read(ROOT / "security" / "onehr_appraisal_security.xml")
rules_xml = read(ROOT / "security" / "onehr_appraisal_rules.xml")

for group_id in (
    "group_onehr_appraisal_participant",
    "group_onehr_appraisal_manager",
    "group_onehr_appraisal_hr",
    "group_onehr_appraisal_admin",
):
    if group_id in security_xml:
        ok(f"Security role present: {group_id}")
    else:
        fail(f"Security role present: {group_id}")

if 'model="res.groups.privilege"' in security_xml:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

if rules_xml.count('<field name="global" eval="True"/>') >= 3:
    ok("Global company isolation rules on all Appraisal models")
else:
    fail("Global company isolation rules")

for token, label in (
    ("employee_user_id", "Participant self-scope uses stored user boundary"),
    ("manager_user_id", "Manager team-scope uses stored user boundary"),
    ("reviewer_user_id", "Peer assignment scope uses stored user boundary"),
):
    if token in rules_xml:
        ok(label)
    else:
        fail(label)

if "_ACTION_CONTEXT" in business_sources and "_STATE_CONTEXT" in business_sources:
    ok("Action-controlled lifecycle state guards present")
else:
    fail("Action-controlled lifecycle state guards")

if "@api.ondelete(at_uninstall=False)" in business_sources:
    ok("Historical evidence deletion guards present")
else:
    fail("Historical evidence deletion guards")

# ------------------------------------------------------------------
# Functional completeness contract
# ------------------------------------------------------------------
functional_tokens = (
    ("annual", "Annual cycle type"),
    ("biannual", "Biannual cycle type"),
    ("quarterly", "Quarterly cycle type"),
    ("custom", "Custom cycle type"),
    ("self_weight", "Self rater weighting"),
    ("manager_weight", "Manager rater weighting"),
    ("peer_weight", "Peer rater weighting"),
    ("action_generate_appraisal_forms", "Employee appraisal generation"),
    ("action_submit_self_review", "Self review submission"),
    ("action_submit_manager_review", "Manager review submission"),
    ("action_request_peer_feedback", "Peer feedback generation"),
    ("action_move_to_consolidation", "Consolidation workflow"),
    ("action_acknowledge", "Employee acknowledgement"),
    ("nine_box_position", "Optional 9-box output"),
    ("development_plan", "Individual Development Plan"),
    ("action_push_to_learning", "Soft Learning hand-off"),
    ("onehr_external_enroll", "Accepted Learning enrollment service contract"),
    ("onehr_appraisal_kpi_snapshot", "Analytics KPI snapshot service"),
    ("onehr_career_feedback_payload", "Career/Succession feedback contract"),
    ("onehr_discipline_feedback_payload", "Discipline evidence contract"),
    ("onehr_employee_appraisal_payload", "Portal/self-service payload"),
    ("onehr_ingest_external_rating", "Integrations API model-service boundary"),
    ("action_import_kpi_targets", "KPI target CSV import"),
    ("action_export_results_csv", "Appraisal result CSV export"),
    ("final_rating_label", "Rating distribution output"),
    ("grade_name", "Grade distribution dimension"),
    ("_cron_appraisal_deadline_reminders", "Review deadline reminder cron"),
)
for token, label in functional_tokens:
    if token in business_sources:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

if "action_report_onehr_appraisal" in read(ROOT / "report" / "appraisal_report.xml"):
    ok("Appraisal QWeb PDF report")
else:
    fail("Appraisal QWeb PDF report")

if "onehr_base.menu_onehr_root" in read(ROOT / "views" / "menus.xml"):
    ok("Integrated OneHR root navigation without sibling source edit")
else:
    fail("Integrated OneHR root navigation")

# ------------------------------------------------------------------
# Test inventory
# ------------------------------------------------------------------
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    try:
        tree = ast.parse(read(path))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_methods.append((path.name, node.name))

if len(test_methods) == EXPECTED_TEST_METHODS:
    ok(f"Runtime test inventory exactly {EXPECTED_TEST_METHODS} methods")
else:
    fail(
        "Runtime test inventory",
        f"expected={EXPECTED_TEST_METHODS}, found={len(test_methods)}",
    )

if all("@tagged" in read(path) for path in sorted((ROOT / "tests").glob("test_*.py"))):
    ok("Runtime test suites are post-install tagged")
else:
    fail("Runtime test suite tags")

# ------------------------------------------------------------------
# Documentation / 15 hard gates
# ------------------------------------------------------------------
mandatory_docs = {
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_PRIVACY_MATRIX.md",
    "INTEGRATION_CONTRACT.md",
    "MODEL_REGISTRY_ALIGNMENT.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE.md",
    "IMPLEMENTATION_REPORT.md",
    "BOUNDED_RUNTIME_REPAIR_ATTEMPT_2.md",
    "SCOPE_ISOLATION_REPORT.md",
}
missing_docs = sorted(
    name for name in mandatory_docs
    if not (ROOT / "docs" / name).is_file()
)
if missing_docs:
    fail("Mandatory Enterprise documentation", f"missing={missing_docs}")
else:
    ok("Mandatory Enterprise documentation set")

guardrail = read(ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for gate in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15):
    if f"HARD GATE {gate}" in guardrail:
        ok(f"Guardrail contains HARD GATE {gate}")
    else:
        fail(f"Guardrail contains HARD GATE {gate}")

if "CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER" in guardrail:
    ok("Codex role locked to bounded implementation worker")
else:
    fail("Codex bounded-worker role")

if "MAX_CODEX_ATTEMPTS_PER_TASK: 2" in guardrail:
    ok("Codex retry limit = 2")
else:
    fail("Codex retry limit")

registry_alignment = read(ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry_alignment:
    warn("Exact Master Model Registry ED rows remain pending; classifications were not invented")
else:
    fail("Registry ED pending marker")

# Native Gantt is not fabricated on CE.
if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else:
    fail("Odoo CE UI ownership", "unexpected Gantt view found")

print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_APPRAISAL_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_APPRAISAL_MOVE_FORWARD_READY=NO")
