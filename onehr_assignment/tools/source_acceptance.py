
﻿from __future__ import annotations

import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

EXPECTED_DEPS = [
    "onehr_base",
    "onehr_corehr",
    "onehr_security",
    "onehr_workflow_approval",
]
EXPECTED_MODELS = {
    "onehr.assignment",
    "onehr.assignment.change.request",
    "onehr.assignment.change.line",
    "onehr.assignment.cost.allocation",
    "onehr.workforce.plan",
    "onehr.workforce.plan.line",
    "onehr.position.budget",
}
EXPECTED_TESTS = 26


def passed(message: str) -> None:
    print(f"PASS: {message}")


def failed(message: str) -> None:
    errors.append(message)
    print(f"FAIL: {message}")


def literal_assign(class_node: ast.ClassDef, name: str):
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


# HARD GATE 0 — manifest identity / dependency ownership.
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Assignment":
    passed("HARD_GATE_0 project/addon identity")
else:
    failed(f"unexpected manifest name: {manifest.get('name')!r}")

if manifest.get("version") == "19.0.1.0.1":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == EXPECTED_DEPS:
    passed("hard dependencies exactly match frozen Assignment architecture")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

for forbidden in (
    "onehr_recruitment",
    "onehr_employment_contract",
    "onehr_multicompany_branch",
    "onehr_payroll_bridge",
    "onehr_integrations_api",
    "account",
    "analytic",
):
    if forbidden in manifest.get("depends", []):
        failed(f"forbidden/non-authoritative hard dependency: {forbidden}")

for relpath in manifest.get("data", []):
    if not (ROOT / relpath).is_file():
        failed(f"manifest data file missing: {relpath}")
if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

# Python and XML source validity.
for path in sorted(ROOT.rglob("*.py")):
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed("all Python sources compile")

xml_ids: dict[str, Path] = {}
view_surface: dict[str, set[str]] = {model: set() for model in EXPECTED_MODELS}
for path in sorted(ROOT.rglob("*.xml")):
    try:
        tree = ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
        continue
    for record in tree.getroot().iter("record"):
        xml_id = record.attrib.get("id")
        if xml_id:
            if xml_id in xml_ids:
                failed(f"duplicate XML id {xml_id!r}: {xml_ids[xml_id].relative_to(ROOT)} and {path.relative_to(ROOT)}")
            else:
                xml_ids[xml_id] = path
        if record.attrib.get("model") != "ir.ui.view":
            continue
        model_name = None
        arch_field = None
        for field in record.findall("field"):
            if field.attrib.get("name") == "model":
                model_name = (field.text or "").strip()
            elif field.attrib.get("name") == "arch":
                arch_field = field
        if model_name not in EXPECTED_MODELS or arch_field is None:
            continue
        children = [child for child in list(arch_field) if isinstance(child.tag, str)]
        if children and children[0].tag in {"list", "form", "search", "calendar", "pivot", "graph", "kanban"}:
            view_surface[model_name].add(children[0].tag)

if not any(item.startswith("XML parse") for item in errors):
    passed("all XML files parse")
if not any(item.startswith("duplicate XML id") for item in errors):
    passed(f"XML external ids unique ({len(xml_ids)})")

# HARD GATE 4 — exact persistent Registry model inventory.
found_models: set[str] = set()
plain_multi_bases: list[str] = []
for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = literal_assign(cls, "_name")
        if isinstance(model_name, str) and model_name.startswith("onehr."):
            found_models.add(model_name)
        # Odoo model classes should not use the old plain-Python mixin multi-base pattern.
        base_labels = []
        for base in cls.bases:
            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                base_labels.append(f"{base.value.id}.{base.attr}")
            elif isinstance(base, ast.Name):
                base_labels.append(base.id)
        if "models.Model" in base_labels and len(base_labels) > 1:
            plain_multi_bases.append(f"{path.name}:{cls.name}:{base_labels}")

if found_models == EXPECTED_MODELS:
    passed("HARD_GATE_4 exact seven Assignment Registry-owned persistent models")
else:
    failed(f"Registry model mismatch expected={sorted(EXPECTED_MODELS)} found={sorted(found_models)}")

if plain_multi_bases:
    failed(f"Odoo model plain-Python multi-base compatibility risk: {plain_multi_bases}")
else:
    passed("no Odoo 19 plain-Python model-base mixin pattern")

# Security / legacy scaffold controls.
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    with acl_path.open(encoding="utf-8", newline="") as handle:
        acl_rows = list(csv.DictReader(handle))
except Exception as exc:
    acl_rows = []
    failed(f"ACL CSV parse: {exc}")

if acl_rows and not any(row.get("group_id:id") == "base.group_user" for row in acl_rows):
    passed(f"least-privilege ACL: {len(acl_rows)} rows, no base.group_user custom CRUD")
else:
    failed("ACL missing or broad base.group_user access detected")

model_source = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted((ROOT / "models").glob("*.py"))
)
if ".sudo(" in model_source:
    failed("business model source contains sudo() bypass")
else:
    passed("no sudo() call in Assignment business model source")

if re.search(r"\bdef\s+unlink\s*\(", model_source):
    failed("unlink override found; use uninstall-safe @api.ondelete instead")
else:
    passed("no unlink override")

ondelete_count = model_source.count("@api.ondelete(at_uninstall=False)")
if ondelete_count >= 7:
    passed(f"uninstall-safe historical deletion guards present ({ondelete_count})")
else:
    failed(f"expected >=7 uninstall-safe ondelete guards, found {ondelete_count}")

if "_sql_constraints" in model_source:
    failed("legacy _sql_constraints pattern found")
else:
    passed("no legacy _sql_constraints pattern")

obsolete_paths = [
    ROOT / "controllers",
    ROOT / "demo",
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
]
if any(path.exists() for path in obsolete_paths):
    failed("generic tutorial scaffold path remains")
else:
    passed("generic tutorial scaffold removed")

# HARD GATES 6-9 — view coverage and enterprise interaction markers.
for model_name, surfaces in sorted(view_surface.items()):
    missing = {"list", "form", "search"} - surfaces
    if missing:
        failed(f"{model_name} missing view surfaces: {sorted(missing)}")
if not any("missing view surfaces" in item for item in errors):
    passed("HARD_GATE_8 List/Form/Search coverage for all seven custom models")

view_source = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted((ROOT / "views").glob("*.xml"))
)
markers = {
    "statusbar": 'widget="statusbar"',
    "smart buttons": "oe_stat_button",
    "body form action": "Schedule Manager Review",
    "One2many/list row actions": '<button name=',
    "chatter": "<chatter/>",
    "calendar": "<calendar",
    "pivot": "<pivot",
    "graph": "<graph",
}
for label, marker in markers.items():
    if marker in view_source:
        passed(f"enterprise UI marker: {label}")
    else:
        failed(f"enterprise UI marker missing: {label}")

# Odoo 19 inherited-view compatibility regression: no xpath selector may use @string.
invalid_string_xpath_selectors = []
for path in sorted((ROOT / "views").glob("*.xml")):
    root = ET.parse(path).getroot()
    for node in root.iter("xpath"):
        expr = node.attrib.get("expr", "")
        if "@string" in expr:
            invalid_string_xpath_selectors.append(
                f"{path.relative_to(ROOT)}: {expr}"
            )

if invalid_string_xpath_selectors:
    for item in invalid_string_xpath_selectors:
        failed(f"Odoo 19 inherited XPath may not use @string selector: {item}")
else:
    passed("Odoo 19 inherited XPath selectors do not use @string")
# Test inventory.
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_methods.append(f"{path.name}:{node.name}")
    source = path.read_text(encoding="utf-8")
    if '@tagged("post_install", "-at_install", "onehr_assignment")' not in source:
        failed(f"post-install onehr_assignment tag missing: {path.name}")

if len(test_methods) == EXPECTED_TESTS:
    passed(f"runtime test source inventory exactly {EXPECTED_TESTS} methods")
else:
    failed(f"expected {EXPECTED_TESTS} test methods, found {len(test_methods)}")

# Governance and documentation evidence.
required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "INTEGRATION_CONTRACTS.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "IMPLEMENTATION_REPORT.md",
    "WINDOWS_RUNTIME_ACCEPTANCE_CHECKLIST.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
]
missing_docs = [name for name in required_docs if not (ROOT / "docs" / name).is_file()]
if missing_docs:
    failed(f"governance docs missing: {missing_docs}")
else:
    passed("all mandatory Guardrail/completeness documentation present")

guardrail_text = (ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").read_text(encoding="utf-8")
required_gate_names = [
    "HARD GATE 0", "HARD GATE 1", "HARD GATE 2", "HARD GATE 3", "HARD GATE 4",
    "HARD GATE 5", "HARD GATE 6", "HARD GATE 7", "HARD GATE 8", "HARD GATE 9",
    "HARD GATE 10", "HARD GATE 11 — INTENTIONALLY UNDEFINED", "HARD GATE 12",
    "HARD GATE 13", "HARD GATE 14", "HARD GATE 15",
]
for gate in required_gate_names:
    if gate not in guardrail_text:
        failed(f"Guardrail gate missing: {gate}")
if not any(item.startswith("Guardrail gate missing") for item in errors):
    passed("all user-defined Hard Gates present; Gate 11 intentionally undefined")

# Critical business contract markers.
critical_markers = {
    "primary native version sync": "create_version({\"date_version\": self.effective_from})",
    "primary position sync": '"onehr_primary_position_id": self.position_id.id',
    "movement successor": '"source_assignment_id": source.id',
    "position capacity": "_check_position_capacity",
    "cost allocation 100%": "Cost allocations must total 100%%",
    "workforce materialization": "_materialize_position_budget",
    "daily effective scheduler": "_cron_apply_effective_assignments",
}
for label, marker in critical_markers.items():
    if marker in model_source:
        passed(f"business contract marker: {label}")
    else:
        failed(f"business contract marker missing: {label}")

print()
print(f"CUSTOM_PERSISTENT_MODELS: {len(found_models)}")
print(f"ACL_ROWS: {len(acl_rows)}")
print(f"XML_EXTERNAL_IDS: {len(xml_ids)}")
print(f"RUNTIME_TEST_METHODS: {len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")

if errors:
    print("ONEHR_ASSIGNMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    for item in errors:
        print(f" - {item}")
    sys.exit(1)

print("ONEHR_ASSIGNMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: NO")

