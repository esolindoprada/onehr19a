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
passes = []


def passed(message):
    passes.append(message)
    print(f"PASS: {message}")


def failed(message):
    errors.append(message)
    print(f"FAIL: {message}")


# ---------------------------------------------------------------------------
# HARD GATE 0 — project identity / exact dependencies / complete manifest
# ---------------------------------------------------------------------------
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Time Off":
    passed("HARD_GATE_0 PROJECT/ADDON identity")
else:
    failed(f"unexpected manifest name {manifest.get('name')!r}")

if manifest.get("version") == "19.0.1.0.0":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version {manifest.get('version')!r}")

expected_depends = ["onehr_corehr", "onehr_security", "onehr_workflow_approval"]
if manifest.get("depends") == expected_depends:
    passed("hard dependencies exactly match OneHR Time Off product baseline")
else:
    failed(f"unexpected hard dependencies {manifest.get('depends')!r}")

for forbidden in (
    "onehr_attendance",
    "onehr_payroll_bridge",
    "onehr_multicompany_branch",
    "onehr_analytics",
    "hr_holidays",
):
    if forbidden in manifest.get("depends", []):
        failed(f"forbidden hard/reverse dependency: {forbidden}")

for rel in manifest.get("data", []):
    if not (ROOT / rel).exists():
        failed(f"manifest data file missing: {rel}")
if not any(item.startswith("manifest data file") for item in errors):
    passed("all manifest data files exist")

# ---------------------------------------------------------------------------
# Syntax / external id safety
# ---------------------------------------------------------------------------
for path in sorted(ROOT.rglob("*.py")):
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed("all Python sources compile")

external_ids = []
for path in sorted(ROOT.rglob("*.xml")):
    try:
        tree = ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
        continue
    for node in tree.getroot().iter():
        xml_id = node.attrib.get("id")
        if xml_id and "." not in xml_id:
            external_ids.append((xml_id, path.relative_to(ROOT)))
if not any(item.startswith("XML parse") for item in errors):
    passed("all XML files parse")

seen = {}
for xml_id, path in external_ids:
    if xml_id in seen:
        failed(f"duplicate XML external id {xml_id}: {seen[xml_id]} and {path}")
    else:
        seen[xml_id] = path
if not any(item.startswith("duplicate XML") for item in errors):
    passed(f"XML external ids unique ({len(external_ids)})")

# ---------------------------------------------------------------------------
# HARD GATE 4 — exact product-baseline persistent model inventory
# ---------------------------------------------------------------------------
expected_models = {
    "onehr.leave.type",
    "onehr.leave.request",
    "onehr.leave.allocation",
}
found_models = set()
for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "_name":
                        try:
                            value = ast.literal_eval(stmt.value)
                        except Exception:
                            value = None
                        if isinstance(value, str):
                            found_models.add(value)

if found_models == expected_models:
    passed("HARD_GATE_4 exact three Time Off product-baseline persistent models")
else:
    failed(f"model inventory mismatch expected={sorted(expected_models)} found={sorted(found_models)}")

model_source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "models").glob("*.py")))
if "_sql_constraints" in model_source:
    failed("legacy _sql_constraints pattern found")
else:
    passed("no legacy _sql_constraints pattern")

if ".sudo(" in model_source or ".sudo()" in model_source:
    failed("business sudo() call found in Time Off model source")
else:
    passed("no business sudo() bypass in Time Off model source")

if "models.Constraint(" in model_source:
    passed("Odoo 19 models.Constraint pattern present")
else:
    failed("Odoo 19 models.Constraint pattern missing")

for forbidden_model in (
    "onehr.leave.balance",
    "onehr.leave.accrual.rule",
    "onehr.leave.carryover",
    "onehr.leave.mass.wizard",
):
    if forbidden_model in model_source:
        failed(f"unapproved extra business model marker found: {forbidden_model}")
if not any("unapproved extra business model" in item for item in errors):
    passed("no invented leave balance/accrual/carry-over/wizard business model")

# ---------------------------------------------------------------------------
# HARD GATE 8/9 — explicit enterprise views for every custom model
# ---------------------------------------------------------------------------
view_source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "views").glob("*.xml")))
for model_name in sorted(expected_models):
    if model_name not in view_source:
        failed(f"view model missing: {model_name}")
        continue
    stem = model_name.rsplit(".", 1)[-1]
    relevant = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "views").glob("*.xml"))
        if model_name in path.read_text(encoding="utf-8")
    )
    for tag in ("<list", "<form", "<search"):
        if tag not in relevant:
            failed(f"{model_name} missing explicit {tag[1:]} view")
if not any("missing explicit" in item or "view model missing" in item for item in errors):
    passed("HARD_GATE_8 List/Form/Search coverage for all three custom models")

ui_markers = {
    "statusbar": 'widget="statusbar"',
    "smart buttons": 'class="oe_stat_button"',
    "body form actions": 'class="btn-secondary"',
    "One2many row actions": '<field name="generated_allocation_ids"',
    "chatter": "<chatter/>",
    "calendar": "<calendar",
    "pivot": "<pivot",
    "graph": "<graph",
}
for label, marker in ui_markers.items():
    if marker in view_source:
        passed(f"enterprise UI marker: {label}")
    else:
        failed(f"enterprise UI marker missing: {label}")

# ---------------------------------------------------------------------------
# HARD GATE 10 — least privilege and explicit model rules
# ---------------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
with acl_path.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
if any(row.get("group_id:id") == "base.group_user" for row in rows):
    failed("broad base.group_user custom-model ACL found")
else:
    passed(f"least-privilege ACL: {len(rows)} rows, no base.group_user custom CRUD")

rules_source = (ROOT / "security" / "onehr_timeoff_rules.xml").read_text(encoding="utf-8")
for marker in ("employee_user_id", "manager_user_id", "company_ids"):
    if marker not in rules_source:
        failed(f"security rule marker missing: {marker}")
if not any("security rule marker missing" in item for item in errors):
    passed("own/team/company record-rule partition present")

# ---------------------------------------------------------------------------
# Enterprise business contracts
# ---------------------------------------------------------------------------
contract_markers = {
    "accrual scheduler": "_run_accrual_for_types",
    "carry-over scheduler": "_run_carryover",
    "idempotency source key": "source_key",
    "workflow approval hook": "_on_approval_finalized",
    "frozen entitlement reservation": "allocation_usage_json",
    "team conflict governance": "_check_team_conflict_policy",
    "attendance soft hook": "_onehr_timeoff_validate_attendance_hook",
    "payroll soft payload": "onehr_timeoff_payroll_payload",
    "mass allocation persistent batch": "action_generate_mass_allocations",
    "grade/tenure eligibility": "is_employee_eligible",
}
for label, marker in contract_markers.items():
    if marker in model_source:
        passed(f"business contract marker: {label}")
    else:
        failed(f"business contract marker missing: {label}")

# Odoo 19 runtime ORM contract — ir.actions.report security field.
# XML parsing alone cannot detect an ORM field-name mismatch. Target runtime
# evidence proves Odoo 19 uses `group_ids`, not `groups_id`, on report actions.
report_xml = (ROOT / "reports" / "leave_request_report.xml").read_text(encoding="utf-8")
if 'name="groups_id"' in report_xml:
    failed("ir.actions.report uses invalid Odoo 19 field groups_id; use group_ids")
elif 'name="group_ids"' in report_xml:
    passed("ir.actions.report Odoo 19 field contract uses group_ids")
else:
    failed("Leave Request report is missing its group_ids security restriction")

# Runtime test inventory
runtime_tests = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    runtime_tests += len(re.findall(r"^\s*def\s+test_\w+\s*\(", path.read_text(encoding="utf-8"), re.MULTILINE))
if runtime_tests == 20:
    passed("runtime test source inventory exactly 20 methods")
else:
    failed(f"runtime test method inventory expected 20 found {runtime_tests}")

# Mandatory governance documents
mandatory_docs = {
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "INTEGRATION_CONTRACTS.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE_CHECKLIST.md",
    "IMPLEMENTATION_REPORT.md",
}
missing_docs = [name for name in sorted(mandatory_docs) if not (ROOT / "docs" / name).exists()]
if missing_docs:
    failed(f"mandatory governance docs missing: {missing_docs}")
else:
    passed("all mandatory Guardrail/completeness documentation present")

print()
print(f"CUSTOM_PERSISTENT_MODELS: {len(found_models)}")
print(f"ACL_ROWS: {len(rows)}")
print(f"XML_EXTERNAL_IDS: {len(external_ids)}")
print(f"RUNTIME_TEST_METHODS: {runtime_tests}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")
if errors:
    print("ONEHR_TIMEOFF_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    sys.exit(1)
print("ONEHR_TIMEOFF_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_TIMEOFF_MOVE_FORWARD_READY: NO")
