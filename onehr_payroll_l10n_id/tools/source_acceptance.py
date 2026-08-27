from __future__ import annotations

import ast
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
pass_count = 0

EXPECTED_NAME = "OneHR Payroll Localization Indonesia"
EXPECTED_VERSION = "19.0.1.0.0"
EXPECTED_DEPS = ["onehr_payroll_bridge"]
EXPECTED_MODELS = {"onehr.payroll.l10n.param"}
EXPECTED_TESTS = 36


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


# ------------------------------------------------------------------
# HARD GATE 0 — identity / manifest / exact dependency direction
# ------------------------------------------------------------------
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == EXPECTED_NAME:
    passed("HARD_GATE_0 exact addon identity")
else:
    failed(f"unexpected manifest name: {manifest.get('name')!r}")

if manifest.get("version") == EXPECTED_VERSION:
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == EXPECTED_DEPS:
    passed("hard dependency exactly onehr_payroll_bridge")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

for forbidden in (
    "base", "hr", "mail", "onehr_corehr", "onehr_security", "onehr_timeoff",
    "onehr_attendance", "onehr_integrations_api", "onehr_multicompany_branch",
    "hr_payroll", "account", "analytic",
):
    if forbidden in manifest.get("depends", []):
        failed(f"forbidden/non-authoritative direct hard dependency: {forbidden}")

for relpath in manifest.get("data", []):
    if not (ROOT / relpath).is_file():
        failed(f"manifest data file missing: {relpath}")
if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

# ------------------------------------------------------------------
# Python / XML / external-id integrity
# ------------------------------------------------------------------
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
view_surfaces = {model: set() for model in EXPECTED_MODELS}
search_group_violations = []

for path in xml_files:
    try:
        tree = ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
        continue

    xml_root = tree.getroot()
    for record in xml_root.iter("record"):
        xml_id = record.attrib.get("id")
        if xml_id:
            if xml_id in xml_ids:
                failed(
                    f"duplicate XML id {xml_id}: "
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

        children = [child for child in list(arch_field) if isinstance(child.tag, str)]
        if model_name in EXPECTED_MODELS and children:
            root_tag = children[0].tag
            if root_tag in {"list", "form", "search", "calendar", "pivot", "graph", "kanban"}:
                view_surfaces[model_name].add(root_tag)

        for search_node in arch_field.iter("search"):
            for group_node in search_node.iter("group"):
                if group_node.attrib:
                    search_group_violations.append(
                        f"{path.relative_to(ROOT)} attrs={group_node.attrib}"
                    )

if not any(item.startswith("XML parse") for item in errors):
    passed("all XML files parse")
if not any(item.startswith("duplicate XML id") for item in errors):
    passed(f"XML external ids unique ({len(xml_ids)})")

if search_group_violations:
    failed(f"Odoo 19 search <group> attribute violation(s): {search_group_violations}")
else:
    passed("Odoo 19 search <group> elements have no attributes")

# ------------------------------------------------------------------
# HARD GATE 4 — exact one-model Registry/product ownership
# ------------------------------------------------------------------
model_files = sorted((ROOT / "models").glob("*.py"))
model_source = "\n".join(path.read_text(encoding="utf-8") for path in model_files)
found_models = set()
inherit_only_models = set()

for path in model_files:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = literal_assign(cls, "_name")
        inherit_name = literal_assign(cls, "_inherit")
        if isinstance(model_name, str) and model_name.startswith("onehr."):
            found_models.add(model_name)
        if model_name is None and isinstance(inherit_name, str):
            inherit_only_models.add(inherit_name)

if found_models == EXPECTED_MODELS:
    passed("HARD_GATE_4 exact one localization persistent model")
else:
    failed(f"model inventory mismatch: {sorted(found_models)}")

if {"onehr.payroll.export", "onehr.payroll.bridge.config"}.issubset(inherit_only_models):
    passed("Payroll Bridge integration uses inheritance without new model ownership")
else:
    failed(f"expected Payroll Bridge inherited extension models missing: {inherit_only_models}")

for forbidden_model in (
    "onehr.payroll.l10n.ptkp",
    "onehr.payroll.l10n.ter",
    "onehr.payroll.l10n.bpjs",
    "onehr.payroll.l10n.thr",
    "onehr.payroll.l10n.simulation",
    "onehr.payroll.l10n.import",
):
    if forbidden_model in found_models:
        failed(f"unapproved invented localization model: {forbidden_model}")

# ------------------------------------------------------------------
# Odoo 19 ORM / security / ownership guards
# ------------------------------------------------------------------
if "_sql_constraints" in model_source:
    failed("legacy _sql_constraints pattern found")
else:
    passed("no legacy _sql_constraints pattern")

if "models.Constraint(" in model_source:
    passed("Odoo 19 models.Constraint pattern present")
else:
    failed("Odoo 19 models.Constraint pattern missing")

if ".sudo(" in model_source:
    failed("business model source contains sudo() bypass")
else:
    passed("no business sudo() bypass")

if re.search(r"\bdef\s+unlink\s*\(", model_source):
    failed("unlink override found; use uninstall-safe @api.ondelete")
else:
    passed("no unlink override")

if "@api.ondelete(at_uninstall=False)" in model_source:
    passed("uninstall-safe history deletion guard present")
else:
    failed("uninstall-safe @api.ondelete guard missing")

if "@http.route" in model_source or "http.Controller" in model_source:
    failed("public controller ownership detected")
else:
    passed("no public API/controller ownership")

secret_patterns = (
    r"\bpassword\s*=\s*fields\.",
    r"\btoken\s*=\s*fields\.",
    r"\bapi_key\s*=\s*fields\.",
    r"\bclient_secret\s*=\s*fields\.",
    r"\bprivate_key\s*=\s*fields\.",
)
if any(re.search(pattern, model_source) for pattern in secret_patterns):
    failed("API/password/private-key credential field ownership detected")
else:
    passed("no API/password/private-key credential ownership")

acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    with acl_path.open(encoding="utf-8", newline="") as handle:
        acl_rows = list(csv.DictReader(handle))
except Exception as exc:
    acl_rows = []
    failed(f"ACL parse: {exc}")

if len(acl_rows) == 2:
    passed("exact Officer-read / Manager-admin ACL rows")
else:
    failed(f"expected 2 ACL rows, found {len(acl_rows)}")

if acl_rows and not any(row.get("group_id:id") == "base.group_user" for row in acl_rows):
    passed("no broad base.group_user localization ACL")
else:
    failed("broad base.group_user localization ACL detected")

officer_rows = [
    row for row in acl_rows
    if row.get("group_id:id") == "onehr_payroll_bridge.group_onehr_payroll_officer"
]
if (
    len(officer_rows) == 1
    and officer_rows[0].get("perm_read") == "1"
    and all(officer_rows[0].get(key) == "0" for key in ("perm_write", "perm_create", "perm_unlink"))
):
    passed("Payroll Officer is read-only for localization parameters")
else:
    failed("Payroll Officer ACL is not strict read-only")

rules = (ROOT / "security" / "onehr_payroll_l10n_id_rules.xml").read_text(encoding="utf-8")
if "[('company_id', 'in', company_ids)]" in rules:
    passed("explicit allowed-company localization record rule")
else:
    failed("company isolation record rule missing")

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

# ------------------------------------------------------------------
# HARD GATES 6-9 — enterprise UI, Search mandatory, no fake workflow
# ------------------------------------------------------------------
for model_name, surfaces in view_surfaces.items():
    missing = {"list", "form", "search"} - surfaces
    if missing:
        failed(f"{model_name} missing required view surfaces: {sorted(missing)}")
if not any("missing required view surfaces" in item for item in errors):
    passed("HARD_GATE_8 List/Form/Search coverage for localization model")

if "calendar" in view_surfaces["onehr.payroll.l10n.param"]:
    passed("effective-date Calendar view present")
else:
    failed("Calendar view missing")

view_source = "\n".join(
    path.read_text(encoding="utf-8")
    for path in sorted((ROOT / "views").glob("*.xml"))
)

for label, marker in {
    "smart buttons": "oe_stat_button",
    "body action": "Mark Regulatory Review Complete",
    "One2many row action": 'string="Open"',
    "effective-period ribbon": 'widget name="web_ribbon"',
    "chatter": "<chatter/>",
    "TER preview": "Check TER Rate",
    "JSON export": "Export Parameters JSON",
    "CSV export": "Export Parameters CSV",
}.items():
    if marker in view_source:
        passed(f"enterprise UI marker: {label}")
    else:
        failed(f"enterprise UI marker missing: {label}")

parameter_views = (ROOT / "views" / "parameter_views.xml").read_text(encoding="utf-8")
if 'widget="statusbar"' not in parameter_views:
    passed("no fake statusbar; product workflow is explicitly configuration-only")
else:
    failed("fake statusbar workflow detected in configuration-only product")

# ------------------------------------------------------------------
# Report compatibility / bridge contract
# ------------------------------------------------------------------
report_source = (ROOT / "reports" / "localization_parameter_report.xml").read_text(encoding="utf-8")
if 'name="groups_id"' in report_source:
    failed("invalid/legacy ir.actions.report groups_id field found")
else:
    passed("ir.actions.report avoids groups_id compatibility defect")

if '<field name="group_ids"' in report_source:
    passed("QWeb report uses Odoo 19 group_ids restriction")
else:
    failed("QWeb report group_ids restriction missing")

bridge_source = (ROOT / "models" / "payroll_bridge_extension.py").read_text(encoding="utf-8")
for label, marker in {
    "generation localization binding": "def action_generate_export",
    "employee-row localization hook": "def _onehr_extend_employee_export_row",
    "generation reset localization clear": "def action_reset_generation",
    "adapter payload extension": "def onehr_payroll_export_payload",
    "frozen localization snapshot": "onehr_l10n_snapshot_json",
    "frozen localization SHA-256": "onehr_l10n_sha256",
}.items():
    if marker in bridge_source:
        passed(f"Payroll Bridge contract marker: {label}")
    else:
        failed(f"Payroll Bridge contract marker missing: {label}")

# ------------------------------------------------------------------
# Regulatory baseline structural gates
# ------------------------------------------------------------------
defaults_path = ROOT / "models" / "regulatory_defaults.py"
defaults_tree = ast.parse(defaults_path.read_text(encoding="utf-8"))
defaults = {}
for node in defaults_tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            defaults[node.targets[0].id] = ast.literal_eval(node.value)
        except Exception:
            pass

for name, expected_count in (
    ("DEFAULT_TER_A_JSON", 44),
    ("DEFAULT_TER_B_JSON", 40),
    ("DEFAULT_TER_C_JSON", 41),
):
    try:
        rows = json.loads(defaults[name])
    except Exception as exc:
        failed(f"{name} JSON parse: {exc}")
        continue
    if len(rows) == expected_count and rows[-1].get("max_gross") is None:
        passed(f"{name} complete/open-ended ({expected_count} bands)")
    else:
        failed(f"{name} expected {expected_count} bands/open-ended final row")

try:
    article17 = json.loads(defaults["DEFAULT_ARTICLE17_JSON"])
    if len(article17) == 5 and article17[-1]["rate_percent"] == 35.0:
        passed("Article 17 five-band progressive defaults present")
    else:
        failed("Article 17 defaults incomplete")
except Exception as exc:
    failed(f"Article 17 JSON parse: {exc}")

try:
    ptkp = json.loads(defaults["DEFAULT_PTKP_MAP_JSON"])
    if ptkp.get("TK/0") == 54_000_000 and ptkp.get("K/3") == 72_000_000:
        passed("PTKP baseline mapping present")
    else:
        failed("PTKP baseline mapping values unexpected")
except Exception as exc:
    failed(f"PTKP JSON parse: {exc}")

critical_markers = {
    "mandatory regulatory review before payroll": "require_review=True",
    "used-parameter immutability": "payroll_export_count",
    "effective-date overlap protection": "_check_no_effective_overlap",
    "governed successor": "action_create_new_version",
    "governed correction": "action_create_correction",
    "parameter hash material": "_parameter_hash_material",
    "TER monthly lookup": "onehr_ter_monthly_rate",
    "THR prorata utility": "onehr_thr_multiplier",
    "JSON/CSV import": "action_import_as_new_version",
    "temporary PPh21 policy hand-off": "pph21_special_policy_json",
    "2026 JP ceiling baseline": "11_086_300.0",
}
for label, marker in critical_markers.items():
    if marker in model_source:
        passed(f"business contract marker: {label}")
    else:
        failed(f"business contract marker missing: {label}")

# ------------------------------------------------------------------
# Runtime test source inventory
# ------------------------------------------------------------------
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_methods.append(f"{path.name}:{node.name}")
    if '@tagged("post_install", "-at_install", "onehr_payroll_l10n_id")' not in source:
        failed(f"post-install localization test tag missing: {path.name}")

if len(test_methods) == EXPECTED_TESTS:
    passed(f"runtime test source inventory exactly {EXPECTED_TESTS} methods")
else:
    failed(f"expected {EXPECTED_TESTS} runtime tests, found {len(test_methods)}")

# ------------------------------------------------------------------
# Governance documentation / 15 hard gates
# ------------------------------------------------------------------
required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "INTEGRATION_CONTRACTS.md",
    "SECURITY_AND_PRIVACY_MODEL.md",
    "UI_UX_MATRIX.md",
    "REGULATORY_BASELINE_2026.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "IMPLEMENTATION_REPORT.md",
    "WINDOWS_RUNTIME_ACCEPTANCE_CHECKLIST.md",
    "BOUNDED_IMPLEMENTATION_EVIDENCE.md",
    "SCOPE_ISOLATION_REPORT.md",
]
missing_docs = [name for name in required_docs if not (ROOT / "docs" / name).is_file()]
if missing_docs:
    failed(f"mandatory documentation missing: {missing_docs}")
else:
    passed("all mandatory Guardrail/completeness/regulatory documentation present")

guardrail = (ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").read_text(encoding="utf-8")
required_gate_markers = [
    "HARD GATE 0", "HARD GATE 1", "HARD GATE 2", "HARD GATE 3",
    "HARD GATE 4", "HARD GATE 5", "HARD GATE 6", "HARD GATE 7",
    "HARD GATE 8", "HARD GATE 9", "HARD GATE 10",
    "HARD GATE 11 — INTENTIONALLY UNDEFINED",
    "HARD GATE 12", "HARD GATE 13", "HARD GATE 14", "HARD GATE 15",
]
for marker in required_gate_markers:
    if marker not in guardrail:
        failed(f"Guardrail marker missing: {marker}")
if not any(item.startswith("Guardrail marker missing") for item in errors):
    passed("all user-defined Hard Gates present; Gate 11 intentionally undefined")

print()
print(f"SOURCE_FILES_PYTHON: {len(python_files)}")
print(f"SOURCE_FILES_XML: {len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS: {len(found_models)}")
print(f"INHERITED_EXISTING_MODELS: {len(inherit_only_models)}")
print(f"ACL_ROWS: {len(acl_rows)}")
print(f"XML_EXTERNAL_IDS: {len(xml_ids)}")
print(f"RUNTIME_TEST_METHODS: {len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT: {pass_count}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")

if errors:
    print("ONEHR_PAYROLL_L10N_ID_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    for item in errors:
        print(f" - {item}")
    sys.exit(1)

print("ONEHR_PAYROLL_L10N_ID_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("DEPLOYMENT_REGULATORY_REVIEW: PENDING")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: NO")
