from __future__ import annotations

import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
pass_count = 0

EXPECTED_DEPS = [
    "onehr_corehr",
    "onehr_security",
]
EXPECTED_MODELS = {
    "onehr.payroll.bridge.config",
    "onehr.payroll.export",
    "onehr.payroll.import",
}
EXPECTED_TESTS = 34
EXPECTED_VERSION = "19.0.1.0.0"


def passed(message: str) -> None:
    global pass_count
    pass_count += 1
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


# ---------------------------------------------------------------------
# HARD GATE 0 — identity / dependencies / manifest files
# ---------------------------------------------------------------------
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Payroll Bridge":
    passed("HARD_GATE_0 exact project/addon identity")
else:
    failed(f"unexpected manifest name: {manifest.get('name')!r}")

if manifest.get("version") == EXPECTED_VERSION:
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == EXPECTED_DEPS:
    passed("hard dependencies exactly Core HR + Security")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

for forbidden in (
    "onehr_attendance",
    "onehr_timeoff",
    "onehr_assignment",
    "onehr_discipline",
    "onehr_payroll_l10n_id",
    "onehr_integrations_api",
    "onehr_analytics",
    "onehr_multicompany_branch",
    "account",
    "analytic",
    "hr_payroll",
    "hr_work_entry",
):
    if forbidden in manifest.get("depends", []):
        failed(f"forbidden/non-authoritative hard dependency: {forbidden}")

for relpath in manifest.get("data", []):
    if not (ROOT / relpath).is_file():
        failed(f"manifest data file missing: {relpath}")
if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

# ---------------------------------------------------------------------
# Python / XML source validity
# ---------------------------------------------------------------------
python_files = sorted(ROOT.rglob("*.py"))
xml_files = sorted(ROOT.rglob("*.xml"))

for path in python_files:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed("all Python sources compile")

xml_ids: dict[str, Path] = {}
view_surface: dict[str, set[str]] = {model: set() for model in EXPECTED_MODELS}
search_group_violations: list[str] = []
invalid_default_periods: list[str] = []

base_period_ids = {
    "first_quarter",
    "second_quarter",
    "third_quarter",
    "fourth_quarter",
    "month",
    "year",
}
relative_period_pattern = re.compile(r"^(?:month|year)[+-][1-9]\d*$")

for path in xml_files:
    try:
        tree = ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
        continue

    root = tree.getroot()
    for record in root.iter("record"):
        xml_id = record.attrib.get("id")
        if xml_id:
            if xml_id in xml_ids:
                failed(
                    f"duplicate XML id {xml_id!r}: "
                    f"{xml_ids[xml_id].relative_to(ROOT)} and {path.relative_to(ROOT)}"
                )
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

        if arch_field is None:
            continue

        arch_children = [child for child in list(arch_field) if isinstance(child.tag, str)]
        if model_name in EXPECTED_MODELS and arch_children:
            root_tag = arch_children[0].tag
            if root_tag in {"list", "form", "search", "calendar", "pivot", "graph", "kanban"}:
                view_surface[model_name].add(root_tag)

        for search_node in arch_field.iter("search"):
            for group_node in search_node.iter("group"):
                if group_node.attrib:
                    search_group_violations.append(
                        f"{path.relative_to(ROOT)}: search <group> attrs={group_node.attrib}"
                    )

            custom_names = {
                f"custom_{node.get('name')}"
                for node in search_node.findall(".//filter[@name]")
                if node.get("name")
            }
            for filter_node in search_node.findall(".//filter[@date][@default_period]"):
                for period_id in [
                    item.strip()
                    for item in (filter_node.get("default_period") or "").split(",")
                    if item.strip()
                ]:
                    valid = (
                        period_id in base_period_ids
                        or bool(relative_period_pattern.match(period_id))
                        or period_id in custom_names
                    )
                    if not valid:
                        invalid_default_periods.append(
                            f"{path.relative_to(ROOT)}: {period_id}"
                        )

if not any(item.startswith("XML parse") for item in errors):
    passed("all XML files parse")
if not any(item.startswith("duplicate XML id") for item in errors):
    passed(f"XML external ids unique ({len(xml_ids)})")

if search_group_violations:
    failed(f"Odoo 19 search <group> attribute violations: {search_group_violations}")
else:
    passed("Odoo 19 search <group> elements have no attributes")

if invalid_default_periods:
    failed(f"Odoo 19 invalid date-filter default_period ids: {invalid_default_periods}")
else:
    passed("Odoo 19 date-filter default_period values are valid")

# ---------------------------------------------------------------------
# HARD GATE 4 — exact Registry/product model inventory
# ---------------------------------------------------------------------
found_models: set[str] = set()
model_files = sorted((ROOT / "models").glob("*.py"))
model_source = "\n".join(path.read_text(encoding="utf-8") for path in model_files)

for path in model_files:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = literal_assign(cls, "_name")
        if isinstance(model_name, str) and model_name.startswith("onehr."):
            found_models.add(model_name)

if found_models == EXPECTED_MODELS:
    passed("HARD_GATE_4 exact three Payroll Bridge persistent models")
else:
    failed(
        f"model inventory mismatch expected={sorted(EXPECTED_MODELS)} "
        f"found={sorted(found_models)}"
    )

for forbidden_model in (
    "onehr.payroll.line",
    "onehr.payroll.payslip",
    "onehr.payroll.work.entry",
    "onehr.payroll.reconciliation",
    "onehr.payroll.costing",
):
    if forbidden_model in found_models:
        failed(f"unapproved invented payroll model: {forbidden_model}")

# ---------------------------------------------------------------------
# Security / ownership / legacy pattern controls
# ---------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    with acl_path.open(encoding="utf-8", newline="") as handle:
        acl_rows = list(csv.DictReader(handle))
except Exception as exc:
    acl_rows = []
    failed(f"ACL CSV parse: {exc}")

if len(acl_rows) == 6:
    passed("exact six role/model ACL rows")
else:
    failed(f"expected 6 ACL rows, found {len(acl_rows)}")

if acl_rows and not any(row.get("group_id:id") == "base.group_user" for row in acl_rows):
    passed("no broad base.group_user custom-model ACL")
else:
    failed("broad base.group_user access detected or ACL missing")

if ".sudo(" in model_source:
    failed("business model source contains sudo() bypass")
else:
    passed("no sudo() call in Payroll Bridge business model source")

if re.search(r"\.users\.(?:filtered|mapped|ids)", model_source):
    failed("Odoo 19 res.groups legacy .users accessor detected; use user_ids/all_user_ids")
else:
    passed("Odoo 19 res.groups user accessors are compatible")

if re.search(r"\bdef\s+unlink\s*\(", model_source):
    failed("unlink override found; use uninstall-safe @api.ondelete")
else:
    passed("no unlink override")

ondelete_count = model_source.count("@api.ondelete(at_uninstall=False)")
if ondelete_count >= 3:
    passed(f"uninstall-safe deletion guards present ({ondelete_count})")
else:
    failed(f"expected >=3 uninstall-safe deletion guards, found {ondelete_count}")

if "_sql_constraints" in model_source:
    failed("legacy _sql_constraints pattern found")
else:
    passed("no legacy _sql_constraints pattern")

secret_field_patterns = (
    r"\bpassword\s*=\s*fields\.",
    r"\btoken\s*=\s*fields\.",
    r"\bapi_key\s*=\s*fields\.",
    r"\bclient_secret\s*=\s*fields\.",
    r"\bprivate_key\s*=\s*fields\.",
)
if any(re.search(pattern, model_source) for pattern in secret_field_patterns):
    failed("integration secret credential field ownership detected")
else:
    passed("no API/password/private-key credential ownership")

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

if "http.Controller" in model_source or "@http.route" in model_source:
    failed("public controller ownership detected in Payroll Bridge")
else:
    passed("no public API/controller ownership")

# ---------------------------------------------------------------------
# HARD GATES 6-9 — view coverage and enterprise interaction
# ---------------------------------------------------------------------
for model_name, surfaces in sorted(view_surface.items()):
    missing = {"list", "form", "search"} - surfaces
    if missing:
        failed(f"{model_name} missing required view surfaces: {sorted(missing)}")

if not any("missing required view surfaces" in item for item in errors):
    passed("HARD_GATE_8 List/Form/Search coverage for all three custom models")

view_source = "\n".join(
    path.read_text(encoding="utf-8")
    for path in sorted((ROOT / "views").glob("*.xml"))
)
enterprise_markers = {
    "statusbar": 'widget="statusbar"',
    "smart buttons": "oe_stat_button",
    "body form action": "Schedule Payroll Review",
    "One2many/list row action": '<button name="action_validate"',
    "chatter": "<chatter/>",
    "calendar": "<calendar",
    "pivot": "<pivot",
    "graph": "<graph",
}
for label, marker in enterprise_markers.items():
    if marker in view_source:
        passed(f"enterprise UI marker: {label}")
    else:
        failed(f"enterprise UI marker missing: {label}")

if 'date="period_end"' in view_source:
    passed("enterprise date-search filter present")
else:
    failed("date-search filter missing")

stored_kpi_markers = (
    'reconciliation_accuracy = fields.Float(',
    'time_to_close_hours = fields.Float(',
)
export_source = (ROOT / "models" / "export.py").read_text(encoding="utf-8")
for marker in stored_kpi_markers:
    start = export_source.find(marker)
    block = export_source[start:start + 240] if start >= 0 else ""
    if start >= 0 and "store=True" in block:
        passed(f"Pivot/Graph KPI is stored: {marker.split(' = ')[0]}")
    else:
        failed(f"Pivot/Graph KPI must be stored: {marker.split(' = ')[0]}")

# ---------------------------------------------------------------------
# Odoo 19 report/security compatibility
# ---------------------------------------------------------------------
report_source = (ROOT / "reports" / "payroll_reconciliation_report.xml").read_text(encoding="utf-8")
if "groups_id" in report_source:
    failed("legacy/invalid ir.actions.report groups_id field found")
else:
    passed("ir.actions.report avoids groups_id compatibility defect")

if "<field name=\"group_ids\"" in report_source:
    passed("report access uses group_ids")
else:
    failed("report group_ids restriction missing")

# ---------------------------------------------------------------------
# Runtime test source inventory
# ---------------------------------------------------------------------
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_methods.append(f"{path.name}:{node.name}")
    source = path.read_text(encoding="utf-8")
    if '@tagged("post_install", "-at_install", "onehr_payroll_bridge")' not in source:
        failed(f"post-install onehr_payroll_bridge tag missing: {path.name}")

if len(test_methods) == EXPECTED_TESTS:
    passed(f"runtime test source inventory exactly {EXPECTED_TESTS} methods")
else:
    failed(f"expected {EXPECTED_TESTS} test methods, found {len(test_methods)}")

# ---------------------------------------------------------------------
# Documentation / Guardrail
# ---------------------------------------------------------------------
required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "INTEGRATION_CONTRACTS.md",
    "UI_UX_MATRIX.md",
    "SECURITY_AND_PRIVACY_MODEL.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "IMPLEMENTATION_REPORT.md",
    "WINDOWS_RUNTIME_ACCEPTANCE_CHECKLIST.md",
]
missing_docs = [name for name in required_docs if not (ROOT / "docs" / name).is_file()]
if missing_docs:
    failed(f"governance docs missing: {missing_docs}")
else:
    passed("all mandatory Guardrail/completeness documentation present")

guardrail = (ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").read_text(encoding="utf-8")
required_gates = [
    "HARD GATE 0",
    "HARD GATE 1",
    "HARD GATE 2",
    "HARD GATE 3",
    "HARD GATE 4",
    "HARD GATE 5",
    "HARD GATE 6",
    "HARD GATE 7",
    "HARD GATE 8",
    "HARD GATE 9",
    "HARD GATE 10",
    "HARD GATE 11 — INTENTIONALLY UNDEFINED",
    "HARD GATE 12",
    "HARD GATE 13",
    "HARD GATE 14",
    "HARD GATE 15",
]
for gate in required_gates:
    if gate not in guardrail:
        failed(f"Guardrail gate missing: {gate}")
if not any(item.startswith("Guardrail gate missing") for item in errors):
    passed("all user-defined Hard Gates present; Gate 11 intentionally undefined")

# ---------------------------------------------------------------------
# Critical business/ownership markers
# ---------------------------------------------------------------------
critical_markers = {
    "Draft → Posted → Reconciled": '("posted", "Posted to Payroll")',
    "frozen source SHA-256": "hashlib.sha256",
    "CSV export": "csv.DictWriter",
    "vendor CSV import": "csv.DictReader",
    "vendor file SHA-256 evidence": "vendor_import_sha256",
    "frozen reconciliation policy": "_frozen_reconciliation_policy",
    "reconciliation coverage KPI": "reconciliation_accuracy",
    "department costing payload": "_build_costing_payload",
    "import correction revision": "action_create_correction",
    "native work-entry soft integration": '"hr.work.entry" not in self.env',
    "attendance soft integration": '"hr.attendance" not in self.env',
    "overtime soft integration": '"hr.attendance.overtime.line" not in self.env',
    "Time Off soft integration": '"onehr.leave.request" not in self.env',
    "Assignment costing soft integration": '"onehr.assignment.cost.allocation" not in self.env',
    "integration export service": "onehr_payroll_export_payload",
    "integration import service": "onehr_ingest_payroll_result",
    "monthly Draft scheduler": "_cron_prepare_scheduled_exports",
    "no automatic non-CSV transport": "_onehr_dispatch_export",
}
for label, marker in critical_markers.items():
    if marker in model_source:
        passed(f"business contract marker: {label}")
    else:
        failed(f"business contract marker missing: {label}")

print()
print(f"SOURCE_FILES_PYTHON: {len(python_files)}")
print(f"SOURCE_FILES_XML: {len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS: {len(found_models)}")
print(f"ACL_ROWS: {len(acl_rows)}")
print(f"XML_EXTERNAL_IDS: {len(xml_ids)}")
print(f"RUNTIME_TEST_METHODS: {len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT: {pass_count}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")

if errors:
    print("ONEHR_PAYROLL_BRIDGE_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    for item in errors:
        print(f" - {item}")
    sys.exit(1)

print("ONEHR_PAYROLL_BRIDGE_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: NO")
