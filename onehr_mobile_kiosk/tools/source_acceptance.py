#!/usr/bin/env python3
"""Static/source hard-gate acceptance for OneHR Mobile Kiosk.

This tool deliberately does NOT claim Windows/Odoo runtime completion.
"""

from __future__ import annotations

import ast
import py_compile
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAILURES = []
PASSES = []


def check(condition, label):
    if condition:
        PASSES.append(label)
        print(f"PASS: {label}")
    else:
        FAILURES.append(label)
        print(f"FAIL: {label}")


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Identity / manifest
# ---------------------------------------------------------------------------

manifest = ast.literal_eval(read("__manifest__.py"))
check(manifest.get("version", "").startswith("19.0."), "Odoo 19 manifest version")
check(manifest.get("depends") == ["onehr_attendance"], "hard dependency exactly onehr_attendance")
check(manifest.get("application") is True, "application addon flag")
check(manifest.get("installable") is True, "installable addon flag")

data_files = manifest.get("data", [])
missing_data = [item for item in data_files if not (ROOT / item).exists()]
check(not missing_data, "all manifest data files exist")

# ---------------------------------------------------------------------------
# Python / XML syntax
# ---------------------------------------------------------------------------

python_files = sorted(
    p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts
)
xml_files = sorted(ROOT.rglob("*.xml"))

compile_errors = []
for path in python_files:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        compile_errors.append(f"{path.relative_to(ROOT)}: {exc}")
check(not compile_errors, "all Python sources compile")

xml_errors = []
external_ids = []
for path in xml_files:
    try:
        tree = ET.parse(path)
        for record in tree.findall(".//*[@id]"):
            external_ids.append((record.attrib["id"], str(path.relative_to(ROOT))))
    except Exception as exc:
        xml_errors.append(f"{path.relative_to(ROOT)}: {exc}")
check(not xml_errors, "all XML files parse")

# Odoo 19 search-view contract:
# <group> only separates filter groups and accepts no attributes.
# Legacy expand/string attributes make the runtime view definition invalid.
search_group_attr_violations = []
for view_path in sorted((ROOT / "views").glob("*.xml")):
    try:
        view_tree = ET.parse(view_path)
    except Exception:
        continue
    for search_node in view_tree.findall(".//search"):
        for group_node in search_node.findall(".//group"):
            if group_node.attrib:
                search_group_attr_violations.append(
                    f"{view_path.relative_to(ROOT)}: {dict(group_node.attrib)}"
                )
check(
    not search_group_attr_violations,
    "Odoo 19 search <group> elements have no attributes",
)

ids_only = [item[0] for item in external_ids]
duplicate_ids = sorted({item for item in ids_only if ids_only.count(item) > 1})
check(not duplicate_ids, "XML external ids unique")

# ---------------------------------------------------------------------------
# Registry / model ownership
# ---------------------------------------------------------------------------

model_sources = "\n".join(read(str(p.relative_to(ROOT))) for p in sorted((ROOT / "models").glob("*.py")))
custom_models = sorted(set(re.findall(r'_name\s*=\s*["\'](onehr\.[^"\']+)["\']', model_sources)))
check(
    custom_models == ["onehr.kiosk.device", "onehr.kiosk.log"],
    "exact two product-approved kiosk persistent models",
)
check("onehr_mobile_kiosk.onehr_mobile_kiosk" not in model_sources, "legacy tutorial model not created")
check('_inherit = "hr.attendance"' in model_sources, "canonical hr.attendance narrow extension")
check("onehr.attendance" not in custom_models, "no parallel OneHR attendance model")
check("_sql_constraints" not in model_sources, "no legacy _sql_constraints pattern")
check("models.Constraint" in model_sources, "Odoo 19 models.Constraint pattern present")

# ---------------------------------------------------------------------------
# Security / integration
# ---------------------------------------------------------------------------

business_python = "\n".join(
    read(str(p.relative_to(ROOT)))
    for folder in ("models", "controllers")
    for p in sorted((ROOT / folder).glob("*.py"))
)
check(".sudo(" not in business_python, "no business sudo() bypass")
check("SUPERUSER_ID" not in business_python, "no SUPERUSER_ID business bypass")
check("hashlib.sha256" in read("models/device.py"), "device token persisted as digest contract")
check("hmac.compare_digest" in read("models/device.py"), "constant-time device token comparison")
check("secrets.token_urlsafe" in read("models/device.py"), "cryptographic token generation")
check("onehr_ingest_interval" in read("models/attendance_bridge.py"), "accepted Attendance ingestion contract used")
check('"onehr.leave.request" not in self.env' in read("models/log.py"), "Time Off soft dependency checked dynamically")
check("with_user(employee_user)" in read("models/log.py"), "quick Time Off runs under employee user authority")
check('auth="user"' in read("controllers/kiosk.py"), "kiosk controllers require authenticated user")
check('auth="public"' not in read("controllers/kiosk.py"), "no public kiosk attendance route")

acl_text = read("security/ir.model.access.csv")
acl_rows = [line for line in acl_text.splitlines()[1:] if line.strip()]
check(len(acl_rows) == 4, "least-privilege kiosk ACL inventory exactly four rows")
check("base.group_user" not in acl_text, "no broad base.group_user kiosk ACL")
rules = read("security/onehr_mobile_kiosk_rules.xml")
check("company_ids" in rules, "global allowed-company record rules")
check("device_id.service_user_id" in rules and "service_user_id" in rules, "assigned-device operator scope")
groups = read("security/onehr_mobile_kiosk_groups.xml")
check("group_onehr_kiosk_operator" in groups and "group_onehr_kiosk_admin" in groups, "operator/admin separation")
check("group_onehr_attendance_officer" in groups, "operator reuses accepted Attendance officer authority")

# ---------------------------------------------------------------------------
# UI / kiosk capabilities
# ---------------------------------------------------------------------------

device_view = read("views/device_views.xml")
log_view = read("views/log_views.xml")
all_views = device_view + "\n" + log_view
for model_name, view_text in (
    ("onehr.kiosk.device", device_view),
    ("onehr.kiosk.log", log_view),
):
    check("<list" in view_text, f"{model_name} explicit List view")
    check("<form" in view_text, f"{model_name} explicit Form view")
    check("<search" in view_text, f"{model_name} explicit Search view")

check('widget="statusbar"' in all_views, "statusbar widgets present")
check("oe_stat_button" in all_views, "smart buttons present")
check("class=\"btn btn-primary\"" in all_views or "class=\"btn-primary\"" in all_views, "body/header action buttons present")
check("<field name=\"log_ids\"" in device_view and "action_retry_sync" in device_view, "One2many row actions present")
check("<chatter/>" in all_views, "chatter present")
check("<calendar" in log_view and "<pivot" in log_view and "<graph" in log_view, "Calendar/Pivot/Graph analytics present")

kiosk_js = read("static/src/js/kiosk.js")
for marker, label in (
    ("localStorage", "browser offline queue"),
    ("crypto.subtle", "encrypted WebCrypto offline queue"),
    ("BarcodeDetector", "QR/barcode browser capability"),
    ("NDEFReader", "Web NFC capability"),
    ("navigator.geolocation", "browser geolocation capability"),
):
    check(marker in kiosk_js, label)

report_xml = read("reports/kiosk_usage_report.xml")
check('model="ir.actions.report"' in report_xml, "QWeb report action present")
check('name="group_ids"' in report_xml, "Odoo 19 ir.actions.report uses group_ids")
check('name="groups_id"' not in report_xml, "legacy ir.actions.report groups_id absent")

# ---------------------------------------------------------------------------
# Privacy / queue / workflow contracts
# ---------------------------------------------------------------------------

check("raw QR/NFC" in read("models/log.py") or "Raw QR/NFC" in read("models/log.py"), "raw credential persistence prohibition documented in code")
check("dead_letter" in model_sources, "durable dead-letter lifecycle")
check("next_retry_at" in model_sources and "max_sync_attempts" in model_sources, "bounded retry/backoff evidence")
check("geofence_policy" in read("models/device.py") and "_evaluate_geofence" in read("models/device.py"), "device geofence policy")
check("face_ready" in read("models/device.py"), "face-ready capability without biometric model")
check("kiosk_employee_snapshot" in read("models/device.py"), "today schedule/leave balance kiosk summary")
check("kiosk_submit_timeoff" in read("models/device.py"), "quick Time Off kiosk service")
check("kiosk_sync_events" in read("models/device.py"), "online/offline sync service")

# ---------------------------------------------------------------------------
# Tests / docs / guardrail
# ---------------------------------------------------------------------------

test_source = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "tests").glob("test_*.py")))
runtime_test_methods = re.findall(r"^\s+def (test_[A-Za-z0-9_]+)\(", test_source, re.M)
check(len(runtime_test_methods) == 24, "runtime test source inventory exactly 24 methods")

mandatory_docs = [
    "docs/PROJECT_IDENTITY_PREFLIGHT.md",
    "docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "docs/MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "docs/BASELINE_FEATURE_PRESERVATION_MATRIX.md",
    "docs/FULL_STRUCTURAL_INVENTORY.md",
    "docs/UI_UX_MATRIX.md",
    "docs/INTEGRATION_CONTRACTS.md",
    "docs/SECURITY_AND_PRIVACY_MODEL.md",
    "docs/ENTERPRISE_COMPLETENESS_MATRIX.md",
    "docs/WINDOWS_RUNTIME_ACCEPTANCE_CHECKLIST.md",
    "docs/IMPLEMENTATION_REPORT.md",
]
check(all((ROOT / item).exists() for item in mandatory_docs), "mandatory enterprise documentation present")

guardrail = read("docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for gate in list(range(0, 11)) + list(range(12, 16)):
    marker = f"HARD GATE {gate}"
    check(marker in guardrail, marker)
check("HARD GATE 11 — INTENTIONALLY UNDEFINED" in guardrail, "Gate 11 intentionally undefined; not invented")
check("MAX_CODEX_ATTEMPTS_PER_TASK: 2" in guardrail, "Codex maximum two attempts")
check("MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1" in guardrail, "same root cause repeat limit one")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

print()
print(f"SOURCE_FILES_PYTHON: {len(python_files)}")
print(f"SOURCE_FILES_XML: {len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS: {len(custom_models)}")
print("NATIVE_MODELS_EXTENDED: 1")
print(f"ACL_ROWS: {len(acl_rows)}")
print(f"XML_EXTERNAL_IDS: {len(external_ids)}")
print(f"RUNTIME_TEST_METHODS: {len(runtime_test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT: {len(PASSES)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(FAILURES)}")
print("ONEHR_MOBILE_KIOSK_DIRECT_FULL_SOURCE_ACCEPTANCE: " + ("PASS" if not FAILURES else "FAIL"))
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("ONEHR_MOBILE_KIOSK_MOVE_FORWARD_READY: NO")

if FAILURES:
    print("\nFAILURES:")
    for failure in FAILURES:
        print(f"- {failure}")
    sys.exit(1)
