
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


try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Core HR":
    passed("PROJECT/ADDON identity")
else:
    failed(f"unexpected addon name: {manifest.get('name')!r}")

if manifest.get("version") == "19.0.1.0.0":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == ["onehr_base", "onehr_security", "hr"]:
    passed("hard dependencies exactly onehr_base, onehr_security, hr")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

for forbidden_dep in ("onehr_document", "onehr_assignment", "onehr_multicompany_branch"):
    if forbidden_dep in manifest.get("depends", []):
        failed(f"forbidden hard dependency: {forbidden_dep}")

if not any("forbidden hard dependency" in item for item in errors):
    passed("soft-integration owners are not hard dependencies")

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

for rel in manifest.get("data", []):
    if not (ROOT / rel).exists():
        failed(f"manifest data file missing: {rel}")

if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

expected_custom = {
    "onehr.employee.dependent",
    "onehr.employee.emergency.contact",
    "onehr.employee.identifier",
    "onehr.employee.education",
    "onehr.employee.employment.history",
    "onehr.engagement.type",
    "onehr.work.incident",
    "onehr.medical.assessment",
    "onehr.disability.record",
}
expected_inherited = {
    "hr.employee",
    "hr.employee.public",
    "hr.version",
    "res.config.settings",
}
found_custom = set()
found_inherited = set()
public_fields = set()

for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = None
        inherit = None
        class_fields = set()
        for node in cls.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id == "_name":
                        try:
                            model_name = ast.literal_eval(node.value)
                        except Exception:
                            pass
                    elif target.id == "_inherit":
                        try:
                            inherit = ast.literal_eval(node.value)
                        except Exception:
                            pass
                    if isinstance(node.value, ast.Call):
                        fn = node.value.func
                        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "fields":
                            class_fields.add(target.id)

        if isinstance(model_name, str) and model_name.startswith("onehr."):
            found_custom.add(model_name)
        if model_name is None and isinstance(inherit, str) and inherit in expected_inherited:
            found_inherited.add(inherit)
            if inherit == "hr.employee.public":
                public_fields |= class_fields

if found_custom == expected_custom:
    passed("exact nine custom Registry models")
else:
    failed(f"custom Registry mismatch: expected={sorted(expected_custom)} found={sorted(found_custom)}")

if found_inherited == expected_inherited:
    passed("exact four inherited Registry rows")
else:
    failed(f"inherited Registry mismatch: expected={sorted(expected_inherited)} found={sorted(found_inherited)}")

all_code = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in ROOT.rglob("*")
    if p.is_file() and p.suffix in {".py", ".xml", ".csv"}
)

for prohibited_model in ("onehr.employee", "onehr.employee.document", "onehr.branch"):
    pattern = rf"""_name\s*=\s*['"]{re.escape(prohibited_model)}['"]"""
    if re.search(pattern, all_code):
        failed(f"prohibited model ownership found: {prohibited_model}")

if not any("prohibited model ownership" in item for item in errors):
    passed("no parallel employee/document/branch ownership")

transient_classes = []
for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        is_transient = any(
            isinstance(base, ast.Attribute) and base.attr == "TransientModel"
            for base in cls.bases
        )
        if not is_transient:
            continue

        inherit = None
        model_name = None
        for node in cls.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"_inherit", "_name"}:
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        value = None
                    if target.id == "_inherit":
                        inherit = value
                    else:
                        model_name = value
        transient_classes.append((cls.name, model_name, inherit))

allowed_transients = [("ResConfigSettings", None, "res.config.settings")]
if transient_classes == allowed_transients:
    passed("only Registry-approved res.config.settings transient extension is present")
else:
    failed(f"unregistered transient business/import wizard introduced: {transient_classes}")

if public_fields == {"onehr_employee_number"}:
    passed("hr.employee.public exposes only approved OneHR employee number")
else:
    failed(f"unexpected OneHR public employee fields: {sorted(public_fields)}")

for rel in ("controllers", "demo", "models/models.py", "views/views.xml", "views/templates.xml"):
    if (ROOT / rel).exists():
        failed(f"legacy generic scaffold remains: {rel}")

if not any("legacy generic scaffold remains" in item for item in errors):
    passed("generic scaffold controllers/demo/models/views removed")

active_description = (
    (ROOT / "__manifest__.py").read_text(encoding="utf-8")
    + (ROOT / "static" / "description" / "index.html").read_text(encoding="utf-8")
)
if re.search(r"\bOdoo\s+18\b", active_description, flags=re.I):
    failed("obsolete Odoo 18 wording remains in active addon description")
else:
    passed("active addon description is Odoo 19 only")

acl_rows = list(csv.reader(io.StringIO((ROOT / "security" / "ir.model.access.csv").read_text(encoding="utf-8-sig"))))
expected_header = [
    "id", "name", "model_id:id", "group_id:id",
    "perm_read", "perm_write", "perm_create", "perm_unlink",
]
if acl_rows and acl_rows[0] == expected_header:
    passed("ACL CSV header")
else:
    failed("ACL CSV header mismatch")

if len(acl_rows) - 1 == 10:
    passed("ACL inventory exactly 10 rows")
else:
    failed(f"expected 10 ACL rows, found {len(acl_rows)-1}")

if any(row[3] == "base.group_user" for row in acl_rows[1:] if len(row) >= 4):
    failed("base.group_user custom-model ACL found")
else:
    passed("no broad base.group_user custom-model ACL")

groups_xml = (ROOT / "security" / "onehr_corehr_groups.xml").read_text(encoding="utf-8")
for marker in (
    "group_onehr_corehr_officer",
    "group_onehr_corehr_manager",
    "group_onehr_identifier_steward",
    "group_onehr_occupational_health_officer",
    "onehr_security.group_onehr_sensitive_data_reader",
    "onehr_security.group_onehr_restricted_data_reader",
):
    if marker not in groups_xml:
        failed(f"required group/security contract missing: {marker}")

manager_block = re.search(
    r'<record id="group_onehr_corehr_manager".*?</record>',
    groups_xml,
    flags=re.S,
)
if manager_block and (
    "group_onehr_occupational_health_officer" in manager_block.group(0)
    or "group_onehr_restricted_data_reader" in manager_block.group(0)
):
    failed("Core HR Manager improperly implies Occupational Health/restricted access")
else:
    passed("Core HR Manager does not imply Occupational Health access")

if "onehr_security.group_onehr_security_admin" in groups_xml:
    failed("Core HR privilege graph unexpectedly implies Security Admin")
else:
    passed("Core HR privilege graph does not imply Security Admin")

rules_xml = (ROOT / "security" / "onehr_corehr_rules.xml").read_text(encoding="utf-8")
if rules_xml.count('model="ir.rule"') == 9:
    passed("company/global record-rule coverage for all nine custom models")
else:
    failed("expected nine custom-model record rules")

identifier_py = (ROOT / "models" / "identifier.py").read_text(encoding="utf-8")
for marker in ("masked_value", "value_fingerprint", "log_sensitive_read", "raw_value_logged"):
    if marker not in identifier_py:
        failed(f"identifier security marker missing: {marker}")

oh_py = (ROOT / "models" / "occupational_health.py").read_text(encoding="utf-8")
for marker in (
    "log_sensitive_read",
    "action_create_correction",
    "supersedes_id",
    "@api.ondelete(at_uninstall=False)",
    "Closed/cancelled work-incident evidence is immutable",
    "Finalized medical evidence is immutable",
):
    if marker not in oh_py:
        failed(f"occupational-health evidence marker missing: {marker}")

if not any("identifier security marker missing" in item for item in errors):
    passed("identifier masking/fingerprint/audit controls present")

settings_py = (ROOT / "models" / "res_config_settings.py").read_text(encoding="utf-8")
expected_mask_key = 'f"onehr_corehr.{self.company_id.id}.identifier_mask_visible_chars"'
if expected_mask_key in identifier_py and '"identifier_mask_visible_chars"' in settings_py:
    passed("identifier masking company-setting key contract is aligned")
else:
    failed("identifier masking company-setting key contract mismatch")
if not any("occupational-health evidence marker missing" in item for item in errors):
    passed("restricted occupational-health audit/immutability/correction controls present")

for file_name in ("relationship.py", "identifier.py", "qualification.py", "engagement.py", "occupational_health.py"):
    source = (ROOT / "models" / file_name).read_text(encoding="utf-8")
    if "onehr.mixin.effective.dated" not in source:
        failed(f"effective-dating contract missing in {file_name}")

if not any("effective-dating contract missing" in item for item in errors):
    passed("ED1 custom-model effective dating coverage present")

employee_py = (ROOT / "models" / "employee.py").read_text(encoding="utf-8")
for marker in (
    '_inherit = "hr.employee"',
    '_inherit = "hr.employee.public"',
    '_inherit = "hr.version"',
    'related="version_id.onehr_engagement_type_id"',
    'related="version_id.onehr_grade_id"',
    'related="version_id.onehr_primary_position_id"',
):
    if marker not in employee_py:
        failed(f"native employee/version architecture marker missing: {marker}")

if not any("native employee/version architecture marker missing" in item for item in errors):
    passed("native employee/version architecture contract present")

coverage = {model: {"list": 0, "form": 0, "search": 0} for model in expected_custom}
for path in sorted((ROOT / "views").glob("*.xml")):
    tree = ET.parse(path)
    for record in tree.findall(".//record[@model='ir.ui.view']"):
        model_field = record.find("./field[@name='model']")
        arch_field = record.find("./field[@name='arch']")
        if model_field is None or arch_field is None:
            continue
        model = (model_field.text or "").strip()
        if model not in coverage:
            continue
        children = list(arch_field)
        if not children:
            continue
        tag = children[0].tag
        if tag in coverage[model]:
            coverage[model][tag] += 1

for model, kinds in sorted(coverage.items()):
    for kind in ("list", "form", "search"):
        if kinds[kind] < 1:
            failed(f"{model} missing {kind} view")

if not any("missing list view" in item for item in errors):
    passed("enterprise list coverage for all custom persistent models")
if not any("missing form view" in item for item in errors):
    passed("professional form coverage for all custom persistent models")
if not any("missing search view" in item for item in errors):
    passed("mandatory search coverage for all custom persistent models")

views_text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "views").glob("*.xml"))
for marker, label in (
    ('widget="statusbar"', "statusbar widgets"),
    ('class="oe_stat_button"', "smart buttons"),
    ("action_create_medical_assessment", "body-form Create Medical Assessment"),
    ("action_create_correction", "medical correction action"),
    ("action_set_primary", "One2many/list emergency primary action"),
    ("action_expire", "One2many/list effective-history expiry actions"),
    ("<chatter/>", "chatter integration"),
    ("hr.view_employee_form", "native employee form inheritance"),
    ("hr.view_employee_tree", "native employee list inheritance"),
    ("hr.view_employee_filter", "native employee search inheritance"),
):
    if marker in views_text:
        passed(label)
    else:
        failed(f"professional UI marker missing: {label}")

report_xml = (ROOT / "report" / "employee_profile_report.xml").read_text(encoding="utf-8")

# Odoo 19 ir.actions.report defines `group_ids`. Reject the invalid `groups_id`
# spelling because XML syntax validation alone cannot detect unknown ORM fields.
if 'name="groups_id"' in report_xml:
    failed("ir.actions.report uses invalid Odoo 19 field groups_id; use group_ids")
elif 'name="group_ids"' in report_xml:
    passed("ir.actions.report Odoo 19 field contract uses group_ids")
else:
    failed("employee profile report is missing its group_ids security restriction")
if (
    "ir.actions.report" in report_xml
    and "hr.employee" in report_xml
    and "onehr_employee_number" in report_xml
    and "identifier_value" not in report_xml
    and "confidential_notes" not in report_xml
):
    passed("safe native-employee PDF report present without restricted payload")
else:
    failed("safe employee-profile report contract failed")

test_count = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    source = path.read_text(encoding="utf-8")
    test_count += len(re.findall(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", source, flags=re.M))
    if '@tagged("post_install", "-at_install", "onehr_corehr")' not in source:
        failed(f"runtime test tag missing: {path.name}")

print(f"TEST_METHOD_COUNT: {test_count}")
if test_count == 16:
    passed("exactly 16 enterprise runtime test methods")
else:
    failed(f"expected 16 test methods, found {test_count}")

required_docs = (
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "ONEHR_COREHR_MODEL_REGISTRY_ALIGNMENT.md",
    "BASELINE_FEATURE_PRESERVATION_MATRIX.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_PRIVACY_MATRIX.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_COREHR_IMPLEMENTATION_REPORT.md",
)
for name in required_docs:
    if not (ROOT / "docs" / name).exists():
        failed(f"required governance document missing: {name}")

if not any("required governance document missing" in item for item in errors):
    passed("governance/preservation/registry/UI/security/completeness docs present")

for path in ROOT.rglob("*"):
    if path.is_dir() and path.name == "__pycache__":
        failed(f"cache directory inside addon: {path.relative_to(ROOT)}")
    if path.is_file() and path.suffix.lower() in {".pyc", ".pyo", ".log", ".sqlite", ".db"}:
        failed(f"runtime/cache artifact inside addon: {path.relative_to(ROOT)}")

if not any("inside addon" in item for item in errors):
    passed("no generated cache/log/database artifacts inside addon")

if errors:
    print()
    print(f"ONEHR_COREHR_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL ({len(errors)} issue(s))")
    sys.exit(1)

print()
print("ONEHR_COREHR_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_COREHR_MOVE_FORWARD_READY: NO")
