from __future__ import annotations

import ast
import csv
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []


def passed(message):
    print(f"PASS: {message}")


def failed(message):
    errors.append(message)
    print(f"FAIL: {message}")


# Manifest / Project Identity
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Base":
    passed("PROJECT/ADDON identity")
else:
    failed("manifest name is not OneHR Base")

if manifest.get("version") == "19.0.1.0.0":
    passed("manifest Odoo 19 version")
else:
    failed(f"unexpected manifest version {manifest.get('version')!r}")

if manifest.get("depends") == ["hr", "mail"]:
    passed("hard dependencies exactly ['hr', 'mail']")
else:
    failed(f"unexpected dependencies {manifest.get('depends')!r}")

for rel in manifest.get("data", []):
    if not (ROOT / rel).exists():
        failed(f"manifest data file missing: {rel}")

# Python and XML syntax
for path in sorted(ROOT.rglob("*.py")):
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed("all Python sources compile")

for path in sorted(ROOT.rglob("*.xml")):
    try:
        ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("XML parse") for item in errors):
    passed("all XML files parse")

# Registry alignment and prohibited parallel masters
all_python = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "models").glob("*.py")
)
required_custom_models = [
    "onehr.job.family",
    "onehr.position",
    "onehr.position.hierarchy",
    "onehr.position.hierarchy.version",
    "onehr.position.hierarchy.node",
    "onehr.grade",
    "onehr.grade.step",
    "onehr.sequence.rule",
    "onehr.eligibility.profile",
    "onehr.lifecycle.event.type",
    "onehr.checklist.template",
    "onehr.checklist.task.template",
    "onehr.checklist.instance",
    "onehr.checklist.task",
    "onehr.mixin.audit",
    "onehr.mixin.effective.dated",
]
for model_name in required_custom_models:
    if model_name not in all_python:
        failed(f"required Registry model missing: {model_name}")

for prohibited in ("onehr.org.unit", "onehr.job", "onehr.location", "onehr.employee"):
    if re.search(rf"_name\s*=\s*['\"]{re.escape(prohibited)}['\"]", all_python):
        failed(f"prohibited parallel canonical model introduced: {prohibited}")

native_source = (ROOT / "models" / "native_models.py").read_text(encoding="utf-8")
for class_name in ("HrDepartment", "HrJob", "HrWorkLocation"):
    if not re.search(rf"class\s+{class_name}\s*\(\s*models\.Model\s*\)", native_source):
        failed(f"{class_name} does not use Odoo-only Python model base")
if "OneHRNativeValidity" in native_source or "CompanyScopedCodeMixin" in all_python:
    failed("legacy plain-Python Odoo model-base mixin pattern reintroduced")
else:
    passed("Odoo 19 plain-Python model-base mixin pattern absent")

# No source security bypass
business_model_source = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "models").glob("*.py")
)
if re.search(r"\.sudo\s*\(", business_model_source):
    failed("business model source contains sudo()")
else:
    passed("business actions contain no sudo() authorization bypass")

# ACL structure
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    rows = list(csv.reader(io.StringIO(acl_path.read_text(encoding="utf-8-sig"))))
    if len(rows) - 1 == 28:
        passed("ACL inventory preserved at 28 rows")
    else:
        failed(f"expected 28 ACL rows, found {len(rows)-1}")
    if any(row[3] == "base.group_user" for row in rows[1:] if len(row) >= 4):
        failed("custom-model ACL grants broad base.group_user access")
    else:
        passed("no broad base.group_user custom-model ACL")
except Exception as exc:
    failed(f"ACL parse: {exc}")

# Exactly 12 test methods
method_count = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    method_count += len(re.findall(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", path.read_text(encoding="utf-8"), re.M))
print(f"TEST_METHOD_COUNT: {method_count}")
if method_count == 12:
    passed("test method inventory exactly 12")
else:
    failed(f"expected exactly 12 test methods, found {method_count}")

# Every custom persistent model must have list, form and search views.
persistent_models = {
    "onehr.job.family",
    "onehr.position",
    "onehr.position.hierarchy",
    "onehr.position.hierarchy.version",
    "onehr.position.hierarchy.node",
    "onehr.grade",
    "onehr.grade.step",
    "onehr.sequence.rule",
    "onehr.eligibility.profile",
    "onehr.lifecycle.event.type",
    "onehr.checklist.template",
    "onehr.checklist.task.template",
    "onehr.checklist.instance",
    "onehr.checklist.task",
}
coverage = {model: {"list": 0, "form": 0, "search": 0} for model in persistent_models}
for path in sorted((ROOT / "views").glob("*.xml")):
    tree = ET.parse(path)
    for record in tree.findall(".//record[@model='ir.ui.view']"):
        model_field = record.find("./field[@name='model']")
        arch_field = record.find("./field[@name='arch']")
        if model_field is None or arch_field is None:
            continue
        model_name = (model_field.text or "").strip()
        if model_name not in coverage:
            continue
        children = list(arch_field)
        if not children:
            continue
        root_tag = children[0].tag
        if root_tag in coverage[model_name]:
            coverage[model_name][root_tag] += 1

for model_name, kinds in sorted(coverage.items()):
    for kind in ("list", "form", "search"):
        if kinds[kind] < 1:
            failed(f"{model_name} missing mandatory {kind} view")
if not any("missing mandatory list view" in item for item in errors):
    passed("enterprise list coverage for all custom persistent models")
if not any("missing mandatory form view" in item for item in errors):
    passed("professional form coverage for all custom persistent models")
if not any("missing mandatory search view" in item for item in errors):
    passed("mandatory search coverage for all custom persistent models")

# Enterprise UI markers
all_xml = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "views").glob("*.xml")
)
for marker, label in (
    ('widget="statusbar"', "statusbar widgets"),
    ('class="oe_stat_button"', "smart buttons"),
    ("action_schedule_outstanding_activities", "body-form operational action"),
    ("action_done", "One2many/list row operational buttons"),
    ("<chatter/>", "chatter integration"),
):
    if marker in all_xml:
        passed(label)
    else:
        failed(f"professional UI marker missing: {label}")

# History protection + uninstall-safe ondelete pattern
checklist_source = (ROOT / "models" / "checklist.py").read_text(encoding="utf-8")
if checklist_source.count("@api.ondelete(at_uninstall=False)") >= 2:
    passed("business history deletion protection uses uninstall-safe api.ondelete")
else:
    failed("missing uninstall-safe api.ondelete protections")
if re.search(r"\n\s*def\s+unlink\s*\(", checklist_source):
    failed("checklist source reintroduced unlink() business deletion override")
else:
    passed("no uninstall-blocking checklist unlink() override")

# Required governance artifacts
required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "ONEHR_BASE_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_BASE_IMPLEMENTATION_REPORT.md",
]
for name in required_docs:
    if not (ROOT / "docs" / name).exists():
        failed(f"required governance document missing: {name}")
if not any(item.startswith("required governance document missing") for item in errors):
    passed("governance/completeness documents present")

if errors:
    print()
    print(f"ONEHR_BASE_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL ({len(errors)} issue(s))")
    sys.exit(1)

print()
print("ONEHR_BASE_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_BASE_MOVE_FORWARD_READY: NO")
