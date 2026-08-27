from __future__ import annotations

import ast
import csv
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def passed(message: str) -> None:
    print(f"PASS: {message}")


def failed(message: str) -> None:
    errors.append(message)
    print(f"FAIL: {message}")


# ---------------------------------------------------------------------------
# HARD GATE 0 — identity / manifest
# ---------------------------------------------------------------------------

manifest_path = ROOT / "__manifest__.py"
try:
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Security & Access Control":
    passed("PROJECT/ADDON identity")
else:
    failed("manifest name is not OneHR Security & Access Control")

if manifest.get("version") == "19.0.1.0.0":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == ["onehr_base", "mail"]:
    passed("hard dependencies exactly ['onehr_base', 'mail']")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

if "onehr_multicompany_branch" not in manifest.get("depends", []):
    passed("no reverse hard dependency on onehr_multicompany_branch")
else:
    failed("onehr_security must not hard-depend on onehr_multicompany_branch")

if manifest.get("installable") is True:
    passed("manifest installable")
else:
    failed("manifest is not installable")

if manifest.get("uninstall_hook") == "uninstall_hook":
    passed("security-safe uninstall_hook declared")
else:
    failed("security-safe uninstall_hook missing from manifest")


# ---------------------------------------------------------------------------
# Python / XML / manifest-data integrity
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# HARD GATE 2/4 — registry inventory and prohibited ownership
# ---------------------------------------------------------------------------

expected_custom_models = {
    "onehr.role",
    "onehr.user.role",
    "onehr.sod.matrix",
    "onehr.sod.conflict.log",
    "onehr.audit.log",
}
found_custom_models = set()
has_res_users_extension = False

for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        model_name = None
        inherit_value = None

        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue

            for target in item.targets:
                if not isinstance(target, ast.Name):
                    continue

                if target.id == "_name":
                    try:
                        model_name = ast.literal_eval(item.value)
                    except Exception:
                        pass

                if target.id == "_inherit":
                    try:
                        inherit_value = ast.literal_eval(item.value)
                    except Exception:
                        pass

        if isinstance(model_name, str) and model_name.startswith("onehr."):
            found_custom_models.add(model_name)

        if inherit_value == "res.users":
            has_res_users_extension = True

if found_custom_models == expected_custom_models:
    passed("exact five custom security Registry models")
else:
    failed(
        "custom model registry mismatch: "
        f"expected={sorted(expected_custom_models)} "
        f"found={sorted(found_custom_models)}"
    )

if has_res_users_extension:
    passed("canonical res.users extension present")
else:
    failed("res.users Registry extension missing")

all_source = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file() and path.suffix in {".py", ".xml", ".csv"}
)

for prohibited in (
    "onehr.branch",
    "onehr.security.user",
    "onehr.user.identity",
    "onehr.group",
):
    if re.search(
        rf"""_name\s*=\s*['"]{re.escape(prohibited)}['"]""",
        all_source,
    ):
        failed(f"prohibited parallel/foreign-owner model defined: {prohibited}")

if not any("prohibited parallel/foreign-owner model" in item for item in errors):
    passed("no prohibited parallel user/group/branch model ownership")

# No transient/custom provisioning wizard was invented.
if "TransientModel" in "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "models").glob("*.py")
):
    failed("unregistered transient security model/wizard introduced")
else:
    passed("no unregistered transient provisioning model introduced")


# ---------------------------------------------------------------------------
# Uninstall privilege cleanup
# ---------------------------------------------------------------------------

init_source = (ROOT / "__init__.py").read_text(encoding="utf-8")
for marker in (
    "def uninstall_hook(env):",
    'env["onehr.role"]',
    'env["res.users"]',
    "Command.unlink",
):
    if marker not in init_source:
        failed(f"uninstall privilege-cleanup marker missing: {marker}")

if not any("uninstall privilege-cleanup marker missing" in item for item in errors):
    passed("uninstall hook revokes OneHR-managed group memberships")

# ---------------------------------------------------------------------------
# Scaffold cleanup
# ---------------------------------------------------------------------------

for rel in (
    "controllers",
    "demo",
    "models/models.py",
    "views/views.xml",
    "views/templates.xml",
):
    if (ROOT / rel).exists():
        failed(f"legacy generic scaffold remains: {rel}")

if not any(item.startswith("legacy generic scaffold remains") for item in errors):
    passed("generic scaffold controllers/demo/models/views removed")

active_runtime_text = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in [
        ROOT / "__manifest__.py",
        ROOT / "static" / "description" / "index.html",
    ]
    if p.exists()
)
if re.search(r"\bOdoo\s+18\b", active_runtime_text, flags=re.I):
    failed("obsolete Odoo 18 wording remains in active manifest/app description")
else:
    passed("active manifest/app description is Odoo 19 only")


# ---------------------------------------------------------------------------
# HARD GATE 10 — security
# ---------------------------------------------------------------------------

acl_path = ROOT / "security" / "ir.model.access.csv"
acl_rows = list(
    csv.reader(
        io.StringIO(acl_path.read_text(encoding="utf-8-sig"))
    )
)

expected_header = [
    "id",
    "name",
    "model_id:id",
    "group_id:id",
    "perm_read",
    "perm_write",
    "perm_create",
    "perm_unlink",
]

if acl_rows and acl_rows[0] == expected_header:
    passed("ACL CSV header")
else:
    failed("ACL CSV header mismatch")

if len(acl_rows) - 1 == 18:
    passed("ACL inventory exactly 18 rows")
else:
    failed(f"expected 18 ACL rows, found {len(acl_rows) - 1}")

if any(row[3] == "base.group_user" for row in acl_rows[1:] if len(row) >= 4):
    failed("custom security ACL grants base.group_user")
else:
    passed("no broad base.group_user custom security ACL")

for row in acl_rows[1:]:
    if len(row) != 8:
        failed(f"ACL row has wrong column count: {row[:2]}")

if not any("ACL row has wrong column count" in item for item in errors):
    passed("all ACL rows have eight columns")

group_xml = (ROOT / "security" / "onehr_security_groups.xml").read_text(encoding="utf-8")
for marker in (
    "res.groups.privilege",
    "group_onehr_security_user",
    "group_onehr_security_manager",
    "group_onehr_security_admin",
    "group_onehr_compliance_officer",
    "group_onehr_sensitive_data_reader",
    "group_onehr_restricted_data_reader",
):
    if marker not in group_xml:
        failed(f"required Odoo 19 security group/privilege marker missing: {marker}")

if not any("required Odoo 19 security group/privilege marker missing" in item for item in errors):
    passed("Odoo 19 privilege/governance/sensitive-access groups present")

rules_xml = (ROOT / "security" / "onehr_security_rules.xml").read_text(encoding="utf-8")
for marker in (
    "rule_res_users_onehr_security_company",
    "rule_onehr_role_company",
    "rule_onehr_user_role_self",
    "rule_onehr_user_role_company_manager",
    "rule_onehr_conflict_self",
    "rule_onehr_conflict_company_management",
    "rule_onehr_audit_company_management",
):
    if marker not in rules_xml:
        failed(f"required record rule missing: {marker}")

if not any("required record rule missing" in item for item in errors):
    passed("company/self record-rule coverage present")

model_sources = {
    p.name: p.read_text(encoding="utf-8")
    for p in (ROOT / "models").glob("*.py")
}
sudo_locations = []
for file_name, source in model_sources.items():
    for line_no, line in enumerate(source.splitlines(), 1):
        if "sudo(" in line and not line.lstrip().startswith("#"):
            sudo_locations.append((file_name, line_no, line.strip()))

allowed_sudo_files = {"audit.py", "sod.py"}
if any(file_name not in allowed_sudo_files for file_name, _, _ in sudo_locations):
    failed(f"business authorization sudo found outside evidence services: {sudo_locations}")
else:
    passed("sudo() confined to private append-only evidence services")

if not any("_log_event" in line for _, _, line in sudo_locations):
    failed("audit evidence sudo marker missing")

if not any("_record_conflict" in model_sources["sod.py"] for _ in [0]):
    failed("SoD private evidence service missing")

if "require_security_manager" not in model_sources["user_role.py"]:
    failed("server-side role assignment manager check missing")
else:
    passed("server-side privileged role-assignment checks present")

if "_check_group_mapping_authority" not in model_sources["role.py"]:
    failed("Admin-only role-to-group mapping guard missing")
else:
    passed("Admin-only role-to-group mapping guard present")

if "onehr_security_reconcile" not in model_sources["res_users.py"]:
    failed("controlled raw-group reconciliation context missing")
else:
    passed("raw Odoo group write is separated from controlled reconciliation")


system_user_locations = []
for file_name, source in model_sources.items():
    for line_no, line in enumerate(source.splitlines(), 1):
        if "with_user(SUPERUSER_ID)" in line and not line.lstrip().startswith("#"):
            system_user_locations.append((file_name, line_no, line.strip()))

if not system_user_locations:
    failed("global entitlement derivation system-user read is missing")
elif any(file_name != "res_users.py" for file_name, _, _ in system_user_locations):
    failed(f"system-user elevation found outside res_users entitlement derivation: {system_user_locations}")
else:
    passed("system-user elevation confined to read-only global entitlement derivation")


# ---------------------------------------------------------------------------
# HARD GATE 8/9 — list/form/search coverage
# ---------------------------------------------------------------------------

persistent_models = {
    "onehr.role",
    "onehr.user.role",
    "onehr.sod.matrix",
    "onehr.sod.conflict.log",
    "onehr.audit.log",
}
coverage = {
    model: {"list": 0, "form": 0, "search": 0}
    for model in persistent_models
}

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

        roots = list(arch_field)
        if not roots:
            continue

        root_tag = roots[0].tag
        if root_tag in coverage[model_name]:
            coverage[model_name][root_tag] += 1

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

all_views = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "views").glob("*.xml")
)

for marker, label in (
    ('widget="statusbar"', "statusbar widgets"),
    ('class="oe_stat_button"', "smart buttons"),
    ("action_reconcile_onehr_access", "body-form access reconciliation"),
    ("action_recheck_sod", "body-form SoD recheck"),
    ("action_scan_effective_assignments", "body-form SoD scan"),
    ("action_activate", "One2many/list activation actions"),
    ("action_revoke", "One2many/list revocation actions"),
    ("<chatter/>", "chatter integration"),
):
    if marker in all_views:
        passed(label)
    else:
        failed(f"professional UI marker missing: {label}")

if "base.view_users_form" in all_views and "base.view_users_tree" in all_views and "base.view_users_search" in all_views:
    passed("native res.users list/form/search extensions present")
else:
    failed("native res.users UI extension coverage incomplete")


# ---------------------------------------------------------------------------
# Effective dating / immutable evidence / branch hooks
# ---------------------------------------------------------------------------

for model_file, marker in (
    ("role.py", "onehr.mixin.effective.dated"),
    ("user_role.py", "onehr.mixin.effective.dated"),
    ("sod.py", "onehr.mixin.effective.dated"),
):
    if marker not in model_sources[model_file]:
        failed(f"effective dating missing in {model_file}")

if not any("effective dating missing" in item for item in errors):
    passed("ED1 role/user-role/SoD policy coverage present")

for marker in (
    "@api.ondelete(at_uninstall=False)",
    "_unlink_except_module_uninstall",
):
    if marker not in model_sources["audit.py"] + model_sources["sod.py"]:
        failed(f"immutable evidence/uninstall-safe marker missing: {marker}")

if "_unlink_only_draft_assignments" not in model_sources["user_role.py"]:
    failed("activated role-assignment history deletion protection missing")
else:
    passed("role-assignment history deletion protection present")

for marker in (
    "_branch_scope_overlap_domain",
    "_branch_scope_label",
    "_onehr_branch_scope_assignment_domain",
):
    if marker not in all_source:
        failed(f"future branch extension hook missing: {marker}")

if not any("future branch extension hook missing" in item for item in errors):
    passed("branch extension hooks present without reverse dependency")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test_count = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    source = path.read_text(encoding="utf-8")
    test_count += len(
        re.findall(
            r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(",
            source,
            flags=re.M,
        )
    )
    if '@tagged("post_install", "-at_install", "onehr_security")' not in source:
        failed(f"post-install onehr_security tag missing: {path.name}")

print(f"TEST_METHOD_COUNT: {test_count}")
if test_count == 12:
    passed("exactly 12 enterprise runtime test methods")
else:
    failed(f"expected 12 test methods, found {test_count}")


# ---------------------------------------------------------------------------
# Governance documents / filesystem hygiene
# ---------------------------------------------------------------------------

required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "ONEHR_SECURITY_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_CONTROL_MATRIX.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_SECURITY_IMPLEMENTATION_REPORT.md",
]
for name in required_docs:
    if not (ROOT / "docs" / name).exists():
        failed(f"required governance document missing: {name}")

if not any("required governance document missing" in item for item in errors):
    passed("governance/registry/UI/security/completeness documents present")

for path in ROOT.rglob("*"):
    if (
        path.is_dir()
        and path.name == "__pycache__"
    ) or (
        path.is_file()
        and path.suffix.lower() in {".pyc", ".pyo", ".log", ".sqlite", ".db"}
    ):
        failed(f"generated runtime/cache artifact inside addon: {path.relative_to(ROOT)}")

if not any("generated runtime/cache artifact inside addon" in item for item in errors):
    passed("no generated cache/log/database artifact inside addon")


# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------

if errors:
    print()
    print(f"ONEHR_SECURITY_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL ({len(errors)} issue(s))")
    sys.exit(1)

print()
print("ONEHR_SECURITY_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_SECURITY_MOVE_FORWARD_READY: NO")
