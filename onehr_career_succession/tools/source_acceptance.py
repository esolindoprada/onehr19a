#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {
    "onehr.competency",
    "onehr.position.competency",
    "onehr.talent.pool",
    "onehr.succession.plan",
}
EXPECTED_DEPS = {
    "onehr_base",
    "onehr_corehr",
}
EXPECTED_VERSION = "19.0.1.0.0"
EXPECTED_TEST_METHODS = 24

passes = []
warnings = []
failures = []


def ok(label):
    passes.append(label)
    print(f"PASS: {label}")


def warn(label):
    warnings.append(label)
    print(f"WARN: {label}")


def fail(label, detail=""):
    failures.append((label, detail))
    print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


# HARD GATE 0 — identity / manifest
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR Career & Succession":
    ok("HARD GATE 0 project/addon identity")
else:
    fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly OneHR Base + CoreHR")
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


# HARD GATE 4 / Python syntax and exact model inventory
python_files = [
    path for path in sorted(ROOT.rglob("*.py"))
    if "__pycache__" not in path.parts
]
python_trees = {}
declared = set()
method_names = set()

for path in python_files:
    try:
        tree = ast.parse(read(path))
    except SyntaxError as exc:
        fail(
            "Python syntax",
            f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}",
        )
        continue

    python_trees[path] = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(node.name)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "_name"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                    and node.value.value in EXPECTED_MODELS
                ):
                    declared.add(node.value.value)

if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

if declared == EXPECTED_MODELS:
    ok("HARD GATE 4 exact four Career/Succession persistent model names")
else:
    fail("HARD GATE 4 exact model inventory", f"found={sorted(declared)}")

business_source = "\n".join(
    read(path) for path in sorted((ROOT / "models").glob("*.py"))
)

for model in sorted(EXPECTED_MODELS):
    if f'_name = "{model}"' in business_source:
        ok(f"Persistent model implemented: {model}")
    else:
        fail(f"Persistent model implemented: {model}")

if business_source.count('_inherit = ["onehr.mixin.audit"]') >= 4:
    ok("All four business models use approved OneHR audit mixin")
else:
    fail("OneHR audit mixin coverage")

if "mail.thread" not in business_source and "mail.activity.mixin" not in business_source:
    ok("No duplicate direct chatter mixin ownership")
else:
    fail("Audit/chatter ownership", "direct mail mixin ownership found")


# Odoo 19 regression guard: compute cannot explicitly depend on id.
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
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and (arg.value == "id" or arg.value.endswith(".id"))
            ):
                bad_depends.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}:{arg.value}"
                )
if bad_depends:
    fail(
        "Odoo 19 @api.depends field-path contract",
        ", ".join(bad_depends),
    )
else:
    ok("Odoo 19 @api.depends contains no explicit .id dependency")


# Generic scaffold / forbidden patterns
for legacy in (
    ROOT / "controllers",
    ROOT / "demo",
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
):
    if legacy.exists():
        fail("Generic tutorial scaffold removed", str(legacy.relative_to(ROOT)))
if not any(label == "Generic tutorial scaffold removed" for label, _ in failures):
    ok("Generic tutorial scaffold removed completely")

runtime_paths = [ROOT / "__manifest__.py", ROOT / "__init__.py"]
for folder in ("models", "security", "views", "data", "report"):
    runtime_paths.extend(
        p for p in sorted((ROOT / folder).rglob("*"))
        if p.is_file()
    )
runtime_source = "\n".join(
    read(p) for p in runtime_paths
    if p.suffix.lower() in {".py", ".xml", ".csv"}
)

for token in (
    "onehr_career_succession.onehr_career_succession",
    "class OnehrCareerSuccession",
    "/onehr_career_succession/onehr_career_succession",
):
    if token in runtime_source:
        fail("No tutorial model/controller residue", token)
if not any(label == "No tutorial model/controller residue" for label, _ in failures):
    ok("No tutorial model/controller residue")

for pattern, label in (
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"auth\s*=\s*['\"]public['\"]", "No public unauthenticated Career controller"),
):
    if re.search(pattern, runtime_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

if "models.Constraint(" in business_source:
    ok("Odoo 19 models.Constraint used")
else:
    fail("Odoo 19 models.Constraint used")


# XML / Odoo 19 UI checks
xml_files = sorted(ROOT.rglob("*.xml"))
xml_roots = {}
for path in xml_files:
    try:
        xml_roots[path] = ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail("XML syntax", f"{path.relative_to(ROOT)}: {exc}")

if len(xml_roots) == len(xml_files):
    ok(f"XML syntax ({len(xml_files)} files)")

view_text = "\n".join(
    read(path) for path in sorted((ROOT / "views").glob("*.xml"))
)

if "<tree" in view_text or "</tree>" in view_text:
    fail("Odoo 19 list syntax", "legacy tree tag found")
else:
    ok("Odoo 19 list syntax uses <list>")

if "attrs=" in view_text or re.search(r"\sstates\s*=", view_text):
    fail("Odoo 19 direct view modifiers", "legacy attrs/states found")
else:
    ok("Odoo 19 direct view modifiers")

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

for label, token in {
    "Statusbar widgets": 'widget="statusbar"',
    "Smart buttons": "oe_stat_button",
    "Body form action buttons": 'class="btn-secondary"',
    "One2many/Many2many row action buttons": "<button ",
    "Chatter": "<chatter",
    "Kanban": "<kanban",
    "Pivot": "<pivot",
    "Graph": "<graph",
    "Badges": 'widget="badge"',
    "Ribbons": 'widget name="web_ribbon"',
}.items():
    if token in view_text:
        ok(f"HARD GATE 6 enterprise UI — {label}")
    else:
        fail(f"HARD GATE 6 enterprise UI — {label}")

missing_button_methods = set()
for path, xml_root in xml_roots.items():
    for button in xml_root.iter("button"):
        if button.attrib.get("type") == "object":
            method = button.attrib.get("name")
            if method and method not in method_names:
                missing_button_methods.add(
                    f"{path.relative_to(ROOT)}:{method}"
                )
if missing_button_methods:
    fail(
        "Object button → Python method cross-reference",
        ", ".join(sorted(missing_button_methods)),
    )
else:
    ok("Object button → Python method cross-reference")

seen_ids = {}
duplicate_ids = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter():
        xml_id = node.attrib.get("id")
        if not xml_id or "." in xml_id:
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


# Security
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(csv.DictReader(read(acl_path).splitlines()))
except Exception as exc:
    acl_rows = []
    fail("ACL CSV parse", str(exc))
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" in read(acl_path):
    fail("HARD GATE 10 least privilege", "base.group_user appears in custom ACL")
else:
    ok("HARD GATE 10 no broad base.group_user Career/Succession CRUD")

security_xml = read(ROOT / "security" / "onehr_career_succession_security.xml")
rules_xml = read(ROOT / "security" / "onehr_career_succession_rules.xml")

for group in (
    "group_onehr_career_hrbp",
    "group_onehr_talent_manager",
):
    if group in security_xml:
        ok(f"Security role present: {group}")
    else:
        fail(f"Security role present: {group}")

if 'model="res.groups.privilege"' in security_xml:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

if rules_xml.count('<field name="global" eval="True"/>') >= 4:
    ok("Global company isolation rules on all four models")
else:
    fail("Global company isolation rules on all four models")

if "_STATE_CONTEXT" in business_source:
    ok("Action-controlled lifecycle state guards present")
else:
    fail("Action-controlled lifecycle state guards present")

if business_source.count("@api.ondelete(at_uninstall=False)") >= 4:
    ok("Historical evidence deletion guards on all four models")
else:
    fail("Historical evidence deletion guard coverage")


# Functional completeness tokens
functional_tokens = (
    ("level_1_behavior", "competency behavioural evidence scale"),
    ("required_level", "position competency requirement"),
    ("high_potential", "high-potential talent"),
    ("readiness_level", "talent readiness level"),
    ("nine_box_position", "9-box talent position"),
    ("target_requirement_ids", "gap-analysis requirement source"),
    ("performance_score", "performance scoring"),
    ("potential_score", "potential scoring"),
    ("learning_score", "learning scoring"),
    ("action_refresh_external_scores", "Appraisal/Learning soft source refresh"),
    ("candidate_talent_ids", "multiple successor candidates"),
    ("primary_successor_id", "primary successor"),
    ("criticality", "critical position planning"),
    ("coverage_percent", "succession coverage"),
    ("bench_strength", "bench strength"),
    ("average_readiness", "average readiness"),
    ("risk_index", "position succession risk index"),
    ("action_propose", "Draft → Proposed workflow"),
    ("action_approve", "Proposed → Approved workflow"),
    ("action_activate", "Approved → Active workflow"),
    ("_cron_succession_review_reminders", "succession review reminders"),
    ("onehr_career_kpi_snapshot", "Analytics KPI service"),
    ("onehr_talent_bi_payload", "Talent BI/API service"),
    ("onehr_competency_bi_payload", "Competency BI/API service"),
    ("onehr_employee_career_payload", "Portal/self-service contract"),
    ("onehr_ingest_talent_assessment", "Integration ingestion service"),
)
for token, label in functional_tokens:
    if token in business_source:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

report_text = read(ROOT / "report" / "career_succession_reports.xml")
for report_id, label in (
    ("action_report_talent_gap", "Competency gap QWeb PDF"),
    ("action_report_succession_plan", "Succession plan QWeb PDF"),
):
    if report_id in report_text:
        ok(label)
    else:
        fail(label)

if "onehr_base.menu_onehr_root" in read(ROOT / "views" / "menus.xml"):
    ok("Integrated OneHR root navigation without sibling source edit")
else:
    fail("Integrated OneHR root navigation")


# Test inventory
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

if all(
    "@tagged" in read(path)
    for path in sorted((ROOT / "tests").glob("test_*.py"))
):
    ok("Runtime test suites are post-install tagged")
else:
    fail("Runtime test suite tags")


# Documentation / hard gates
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
    "ROOT_GUARDRAIL_REFERENCE.md",
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

registry_doc = read(ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry_doc:
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
print(f"CUSTOM_PERSISTENT_MODELS={len(declared)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_CAREER_SUCCESSION_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_CAREER_SUCCESSION_MOVE_FORWARD_READY=NO")
