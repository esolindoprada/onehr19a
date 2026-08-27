#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {
    "onehr.learning.course",
    "onehr.learning.session",
    "onehr.learning.enrollment",
    "onehr.learning.attendance",
    "onehr.learning.certificate",
    "onehr.learning.vendor",
    "onehr.learning.budget",
    "onehr.learning.cost.line",
}
EXPECTED_DEPS = {
    "onehr_base",
    "onehr_corehr",
    "onehr_security",
    "onehr_workflow_approval",
}

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

# Python syntax + exact model names.
declared = set()
for path in sorted(ROOT.rglob("*.py")):
    if "__pycache__" in path.parts:
        continue
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        fail("Python syntax", f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_name":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if node.value.value.startswith("onehr.learning."):
                            declared.add(node.value.value)

if declared == EXPECTED_MODELS:
    ok("HARD GATE 4 exact eight Learning persistent model names")
else:
    fail("HARD GATE 4 exact model inventory", f"found={sorted(declared)}")

# Manifest is data, not executed import.
manifest_path = ROOT / "__manifest__.py"
try:
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
    deps = set(manifest.get("depends", []))
    if deps == EXPECTED_DEPS:
        ok("Hard dependencies exactly match approved Learning topology")
    else:
        fail("Hard dependency topology", f"found={sorted(deps)}")
    missing_data = [item for item in manifest.get("data", []) if not (ROOT / item).is_file()]
    if not missing_data:
        ok("All manifest data files exist")
    else:
        fail("Manifest data files", f"missing={missing_data}")
except Exception as exc:
    fail("Manifest parse", str(exc))

# XML parse and Odoo 19 legacy syntax.
xml_files = sorted(ROOT.rglob("*.xml"))
for path in xml_files:
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        fail("XML syntax", f"{path.relative_to(ROOT)}: {exc}")
if not any(x[0] == "XML syntax" for x in failures):
    ok(f"XML syntax ({len(xml_files)} files)")

business_sources = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in sorted((ROOT / "models").glob("*.py"))
)
runtime_paths = [
    ROOT / "__init__.py",
    ROOT / "__manifest__.py",
]
for folder in ("models", "security", "views", "data", "reports"):
    runtime_paths.extend(sorted((ROOT / folder).rglob("*")))

all_source = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in runtime_paths
    if p.is_file() and p.suffix.lower() in {".py", ".xml", ".csv"}
)

for pattern, label in [
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"auth\s*=\s*['\"]public['\"]", "No public unauthenticated Learning controller"),
]:
    if re.search(pattern, all_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

if "onehr_learning.onehr_learning" in all_source:
    fail("Tutorial scaffold removed", "legacy tutorial model/reference remains")
else:
    ok("Tutorial scaffold removed")

# ACL must not grant custom Learning CRUD to base.group_user.
acl_path = ROOT / "security" / "ir.model.access.csv"
acl_text = acl_path.read_text(encoding="utf-8")
if "base.group_user" in acl_text:
    fail("Security ACL least privilege", "base.group_user appears in Learning ACL")
else:
    ok("No broad base.group_user ACL on Learning business models")

# Search/list/form views for every model.
view_text = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in sorted((ROOT / "views").glob("*.xml"))
)
for model in sorted(EXPECTED_MODELS):
    escaped = re.escape(model)
    model_blocks = re.findall(
        rf'<record[^>]*model="ir\.ui\.view".*?</record>',
        view_text,
        flags=re.S,
    )
    relevant = [b for b in model_blocks if f"<field name=\"model\">{model}</field>" in b]
    kinds = set()
    for block in relevant:
        if "<list" in block:
            kinds.add("list")
        if "<form" in block:
            kinds.add("form")
        if "<search" in block:
            kinds.add("search")
    if {"list", "form", "search"} <= kinds:
        ok(f"List/Form/Search views: {model}")
    else:
        fail(f"List/Form/Search views: {model}", f"found={sorted(kinds)}")

# Advanced enterprise interaction evidence.
checks = {
    "Statusbar widgets": 'widget="statusbar"',
    "Smart buttons": "oe_stat_button",
    "Chatter": "<chatter",
    "One2many/list row action buttons": "<button ",
    "Kanban": "<kanban",
    "Calendar": "<calendar",
    "Pivot": "<pivot",
    "Graph": "<graph",
}
for label, token in checks.items():
    if token in view_text:
        ok(label)
    else:
        fail(label)

if "<tree" in view_text or "</tree>" in view_text:
    fail("Odoo 19 list syntax", "legacy tree tag found")
else:
    ok("Odoo 19 list syntax uses <list>")

if "attrs=" in view_text or " states=" in view_text:
    fail("Odoo 19 view modifiers", "legacy attrs/states modifier found")
else:
    ok("Odoo 19 direct view modifiers")

if "models.Constraint" in business_sources:
    ok("Odoo 19 models.Constraint used")
else:
    fail("Odoo 19 constraints", "models.Constraint not found")

# Required source contracts / functional depth.
for token, label in [
    ("onehr.mixin.approvable", "Generic workflow approval integration"),
    ("action_request_approval", "Enrollment approval action"),
    ("action_process_waitlist", "Capacity/waitlist processing"),
    ("action_import_participants_csv", "Mass participant CSV import"),
    ("action_export_results_csv", "Learning result CSV export"),
    ("_cron_schedule_upcoming_reminders", "Session reminder cron service"),
    ("_cron_process_certificate_expiry", "Certificate expiry/renewal service"),
    ("onehr_ingest_interval", "Accepted Attendance soft integration boundary"),
    ("onehr_participant_portal_payload", "Portal downstream payload contract"),
    ("onehr_learning_kpi_snapshot", "Analytics KPI payload contract"),
    ("onehr_external_enroll", "External enrollment service contract"),
    ("onehr_payroll_cost_payload", "Payroll/reimbursement hand-off contract"),
]:
    if token in business_sources:
        ok(label)
    else:
        fail(label)

if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE; see UI_UX_MATRIX.md")

print()
print(f"SOURCE_ACCEPTANCE_PASS={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL={len(failures)}")

if failures:
    sys.exit(1)
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_LEARNING_MOVE_FORWARD_READY=NO")
