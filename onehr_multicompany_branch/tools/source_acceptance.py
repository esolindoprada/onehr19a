
#!/usr/bin/env python3
"""Static source acceptance for OneHR Multicompany & Branch.

This gate deliberately does not connect to PostgreSQL or start Odoo. Runtime
installation, tests, upgrades and uninstall/reinstall remain separate hard gates.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
passes: list[str] = []


def passed(message: str) -> None:
    passes.append(message)
    print(f"PASS: {message}")


def failed(message: str) -> None:
    errors.append(message)
    print(f"FAIL: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


print("SCRIPT_ID: ONEHR_MULTICOMPANY_BRANCH_SOURCE_ACCEPTANCE_V3_20260909")
print(f"TARGET: {ROOT}")

# ---------------------------------------------------------------------------
# HARD GATE 0 / manifest / package identity
# ---------------------------------------------------------------------------
manifest_path = ROOT / "__manifest__.py"
try:
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
except Exception as exc:
    failed(f"manifest is not a literal Odoo manifest: {exc}")
    manifest = {}

if manifest.get("version") == "19.0.1.0.2":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == ["onehr_security"]:
    passed("exact approved hard dependency: onehr_security")
else:
    failed(f"dependency topology mismatch: {manifest.get('depends')!r}")

if manifest.get("installable") is True and manifest.get("application") is False:
    passed("installable foundation-addon contract")
else:
    failed("manifest installable/application contract mismatch")

if not (ROOT / "controllers").exists() and not (ROOT / "demo").exists() and "demo" not in manifest:
    passed("generic controller/demo scaffold removed")
else:
    failed("controller/demo scaffold remains")

# ---------------------------------------------------------------------------
# Python syntax and Master Model Registry structure
# ---------------------------------------------------------------------------
python_files = sorted(ROOT.rglob("*.py"))
model_class_bases: list[tuple[str, str, list[str]]] = []
found_named_models: set[str] = set()

for path in python_files:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        tree = ast.parse(source, filename=str(path))
    except Exception as exc:
        failed(f"Python syntax/AST error in {path.relative_to(ROOT)}: {exc}")
        continue

    if path.parent.name != "models":
        continue

    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        base_names: list[str] = []
        for base in cls.bases:
            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                base_names.append(f"{base.value.id}.{base.attr}")
            elif isinstance(base, ast.Name):
                base_names.append(base.id)
        if any(name in {"models.Model", "models.AbstractModel", "models.TransientModel"} for name in base_names):
            model_class_bases.append((path.name, cls.name, base_names))

        for node in cls.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "_name" for target in node.targets):
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                value = None
            if isinstance(value, str) and value.startswith("onehr."):
                found_named_models.add(value)

if not any(item.startswith("Python syntax/AST error") for item in errors):
    passed(f"Python syntax/AST validation ({len(python_files)} files)")

expected_named_models = {"onehr.branch", "onehr.mixin.branch"}
if found_named_models == expected_named_models:
    passed("HARD GATE 4 exact target Master Model Registry named models")
else:
    failed(f"Registry named-model mismatch expected={sorted(expected_named_models)} found={sorted(found_named_models)}")

bad_bases = [row for row in model_class_bases if len(row[2]) != 1]
if bad_bases:
    failed(f"plain-Python/non-Odoo model-base pattern detected: {bad_bases}")
else:
    passed("Odoo 19 model classes use exactly one Odoo Python base")

all_model_source = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted((ROOT / "models").glob("*.py"))
)

# Relational comodel metadata used by the cross-model read-authority closure gate.
# The parser derives the comodel from field declarations so the gate fails if a
# future repair silently changes a surfaced relation without updating authority.
relational_fields: dict[str, str] = {}
for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        owner_model = None
        for node in cls.body:
            if not isinstance(node, ast.Assign):
                continue
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "_name" in targets or "_inherit" in targets:
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    value = None
                if isinstance(value, str):
                    if "_name" in targets or owner_model is None:
                        owner_model = value
        if not owner_model:
            continue
        for node in cls.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            if not isinstance(node.value, ast.Call) or not isinstance(node.value.func, ast.Attribute):
                continue
            if node.value.func.attr not in {"Many2one", "Many2many", "One2many"} or not node.value.args:
                continue
            try:
                comodel = ast.literal_eval(node.value.args[0])
            except Exception:
                continue
            if isinstance(comodel, str):
                relational_fields[f"{owner_model}.{node.targets[0].id}"] = comodel
for marker, label in (
    ('_name = "onehr.branch"', "onehr.branch NEW ED1"),
    ('_name = "onehr.mixin.branch"', "onehr.mixin.branch NEW abstract ED0"),
    ('_inherit = "res.company"', "res.company native extension"),
    ('_inherit = "res.users"', "res.users native extension"),
    ('_inherit = "onehr.user.role"', "security-owned onehr.user.role branch extension"),
    ('models.Constraint(', "Odoo 19 models.Constraint usage"),
    ('onehr_allowed_branch_ids', "explicit allowed-branch user scope"),
    ('onehr_default_branch_id', "default branch preference"),
    ('_onehr_branch_scope_assignment_domain', "onehr_security branch-domain hook"),
    ('_onehr_desired_group_ids', "branch-aware managed-group derivation"),
    ('_branch_scope_overlap_domain', "branch-aware role overlap hook"),
    ('_branch_scope_label', "branch scope label hook"),
    ('onehr_branch_enabled', "company branch enablement enforcement"),
):
    if marker in all_model_source:
        passed(label)
    else:
        failed(f"required model/integration marker missing: {label}")

if "onehr_multicompany_branch.onehr_multicompany_branch" in all_model_source:
    failed("obsolete scaffold model is still present")
else:
    passed("obsolete generic scaffold model rejected per Registry")

if "_sql_constraints" in all_model_source:
    failed("legacy _sql_constraints pattern found")
else:
    passed("no legacy _sql_constraints usage")

if re.search(r"\b(?:safe_eval|eval|exec)\s*\(", all_model_source):
    failed("unsafe executable-expression primitive found")
else:
    passed("no safe_eval/eval/exec business primitive")

sudo_occurrences = []
system_user_occurrences = []
for path in sorted((ROOT / "models").glob("*.py")):
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if ".sudo(" in line:
            sudo_occurrences.append((path.name, line_no, line.strip()))
        if "with_user(SUPERUSER_ID)" in line:
            system_user_occurrences.append((path.name, line_no, line.strip()))

if sudo_occurrences:
    failed(f"sudo() is not approved in this addon: {sudo_occurrences}")
else:
    passed("no sudo() bypass path")

expected_system_counts = {"branch.py": 5, "res_users.py": 2}
actual_system_counts = {}
for file_name, _line_no, _line in system_user_occurrences:
    actual_system_counts[file_name] = actual_system_counts.get(file_name, 0) + 1
if actual_system_counts == expected_system_counts and len(system_user_occurrences) == 7:
    passed("exact seven reviewed narrow SUPERUSER integrity/derivation/persistence paths")
else:
    failed(
        f"unexpected SUPERUSER usage expected={expected_system_counts} "
        f"actual={actual_system_counts} rows={system_user_occurrences}"
    )

# ---------------------------------------------------------------------------
# Security hard gate
# ---------------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
with acl_path.open(encoding="utf-8", newline="") as handle:
    acl_rows = list(csv.DictReader(handle))

print(f"ACL_ROW_COUNT: {len(acl_rows)}")
if len(acl_rows) == 14:
    passed("exact 14 reviewed ACL rows, including full Users runtime dependency read closure")
else:
    failed(f"expected 14 ACL rows, found {len(acl_rows)}")

if any(row.get("group_id:id") == "base.group_user" for row in acl_rows):
    failed("direct base.group_user ACL detected")
else:
    passed("no direct base.group_user ACL")

# Generic cross-model comodel-read closure contract for branch fields exposed
# on Users and Role Assignment governance surfaces.  The consumer groups below
# are the approved callers of those surfaces; each must have explicit read ACL
# on the derived relational comodel.  Record rules remain authoritative and are
# intentionally not widened by this gate.
read_acl_by_model_group = {
    (row.get("model_id:id"), row.get("group_id:id"))
    for row in acl_rows
    if row.get("perm_read") == "1"
}
comodel_model_id = {"onehr.branch": "model_onehr_branch"}
read_closure_contract = {
    "res.users.onehr_allowed_branch_ids": {
        "base.group_system",
        "onehr_multicompany_branch.group_onehr_branch_admin",
        "onehr_multicompany_branch.group_onehr_central_office",
        "onehr_security.group_onehr_security_manager",
        "onehr_security.group_onehr_security_admin",
    },
    "res.users.onehr_default_branch_id": {
        "base.group_system",
        "onehr_multicompany_branch.group_onehr_branch_admin",
        "onehr_multicompany_branch.group_onehr_central_office",
        "onehr_security.group_onehr_security_manager",
        "onehr_security.group_onehr_security_admin",
    },
    "res.users.onehr_effective_branch_ids": {
        "base.group_system",
        "onehr_multicompany_branch.group_onehr_branch_admin",
        "onehr_multicompany_branch.group_onehr_central_office",
        "onehr_security.group_onehr_security_manager",
        "onehr_security.group_onehr_security_admin",
    },
    "onehr.user.role.branch_id": {
        "onehr_multicompany_branch.group_onehr_branch_admin",
        "onehr_multicompany_branch.group_onehr_central_office",
        "onehr_security.group_onehr_security_manager",
        "onehr_security.group_onehr_security_admin",
    },
}
closure_failures = []
for surface_field, consumer_groups in sorted(read_closure_contract.items()):
    comodel = relational_fields.get(surface_field)
    if not comodel:
        closure_failures.append(f"{surface_field}: relational comodel not derivable from source")
        continue
    model_id = comodel_model_id.get(comodel)
    if not model_id:
        closure_failures.append(f"{surface_field}: no reviewed model-id mapping for comodel {comodel}")
        continue
    for group_xmlid in sorted(consumer_groups):
        if (model_id, group_xmlid) not in read_acl_by_model_group:
            closure_failures.append(f"{surface_field}: {group_xmlid} lacks read ACL on {comodel}")

if closure_failures:
    failed(f"generic cross-model comodel-read closure failed: {closure_failures}")
else:
    passed("generic cross-model comodel-read closure for Users / Role Assignment branch surfaces")

for required_acl_id in (
    "access_onehr_branch_odoo_technical_admin",
    "access_onehr_branch_security_manager",
    "access_onehr_branch_security_admin",
    "access_onehr_user_role_odoo_technical_admin",
    "access_onehr_role_odoo_technical_admin",
    "access_onehr_sod_conflict_odoo_technical_admin",
    "access_onehr_audit_odoo_technical_admin",
):
    rows = [row for row in acl_rows if row.get("id") == required_acl_id]
    if len(rows) == 1 and rows[0].get("perm_read") == "1" and all(
        rows[0].get(permission) == "0" for permission in ("perm_write", "perm_create", "perm_unlink")
    ):
        passed(f"bounded read-only runtime closure ACL: {required_acl_id}")
    else:
        failed(f"missing or non-read-only runtime closure ACL: {required_acl_id}")

# Native Settings > Users is not merely a relational-comodel render. The
# onehr_security summary compute reached by the Users list/search traverses
# four security-owned support models.  Attempt 2 explicitly closes this whole
# deterministic dependency graph for Odoo Technical Administration, while the
# existing branch comodel closure remains mandatory.
users_runtime_dependency_model_ids = {
    "onehr.branch": "model_onehr_branch",
    "onehr.user.role": "onehr_security.model_onehr_user_role",
    "onehr.role": "onehr_security.model_onehr_role",
    "onehr.sod.conflict.log": "onehr_security.model_onehr_sod_conflict_log",
    "onehr.audit.log": "onehr_security.model_onehr_audit_log",
}
runtime_dependency_failures = []
for model_name, model_id in sorted(users_runtime_dependency_model_ids.items()):
    if (model_id, "base.group_system") not in read_acl_by_model_group:
        runtime_dependency_failures.append(
            f"base.group_system lacks read ACL on {model_name} ({model_id})"
        )
if runtime_dependency_failures:
    failed(f"native Users runtime dependency closure failed: {runtime_dependency_failures}")
else:
    passed("native Users runtime dependency closure for Odoo Technical Admin across all current support models")

if all(row.get("perm_unlink") == "0" for row in acl_rows):
    passed("no branch-addon ACL grants unlink")
else:
    failed("an ACL grants unlink")

groups_xml = read("security/onehr_branch_groups.xml")
rules_xml = read("security/onehr_branch_rules.xml")
for marker, label in (
    ("res.groups.privilege", "Odoo 19 privilege classification"),
    ("group_onehr_branch_user", "Branch User group"),
    ("group_onehr_branch_manager", "Branch Manager group"),
    ("group_onehr_branch_admin", "Branch Admin group"),
    ("group_onehr_central_office", "Central Office group"),
):
    if marker in groups_xml:
        passed(label)
    else:
        failed(f"security group marker missing: {label}")

for marker, label in (
    ("rule_onehr_branch_company_global", "global legal-company branch partition"),
    ("user.onehr_allowed_branch_ids.ids", "explicit allowed-branch record-rule scope"),
    ("rule_res_users_onehr_branch_admin_company", "Branch Admin user company rule"),
    ("rule_onehr_user_role_branch_global", "global user-role branch narrowing"),
    ("('user_id', '=', user.id)", "self-history preservation inside role branch rule"),
):
    if marker in rules_xml:
        passed(label)
    else:
        failed(f"record-rule marker missing: {label}")

if "require_branch_admin(self.env)" in read("models/branch.py"):
    passed("server-side Branch Admin authorization")
else:
    failed("branch master relies on UI without server authorization")

if "OneHR Branch Admin may change only branch-scope fields on other users" in read("models/res_users.py"):
    passed("Branch Admin res.users write is server-side field-bounded")
else:
    failed("Branch Admin res.users ACL lacks a server-side field boundary")

if "_assert_branch_admin_change_within_actor_scope" in read("models/res_users.py"):
    passed("Branch Admin branch IDs are server-validated against caller legal-company scope")
else:
    failed("Branch Admin branch ID scope validation is missing")

# ---------------------------------------------------------------------------
# XML / professional UI gates
# ---------------------------------------------------------------------------
xml_files = sorted(
    path for path in ROOT.rglob("*.xml")
    if "static" not in path.parts
)
for path in xml_files:
    try:
        ET.parse(path)
    except Exception as exc:
        failed(f"XML parse error in {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("XML parse error") for item in errors):
    passed(f"XML well-formedness ({len(xml_files)} files)")

branch_views = read("views/branch_views.xml")
all_views = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "views").glob("*.xml")))
for marker, label in (
    ('model">onehr.branch</field>', "onehr.branch dedicated views"),
    ('<list', "enterprise list view"),
    ('<form', "professional form view"),
    ('<search', "mandatory search view"),
    ('widget="statusbar"', "statusbar widget"),
    ('class="oe_stat_button"', "smart buttons"),
    ('action_set_as_my_default', "controlled body/quick-selector action"),
    ('action_archive', "controlled lifecycle action"),
    ('<field name="child_ids"', "hierarchy One2many"),
    ('<button name="action_open_branch"', "One2many/list row action"),
    ('<chatter/>', "chatter integration"),
    ('decoration-success=', "semantic list decoration"),
):
    if marker in branch_views:
        passed(label)
    else:
        failed(f"professional branch UI marker missing: {label}")

for marker, label in (
    ('inherit_id" ref="base.view_company_form"', "native res.company form extension"),
    ('inherit_id" ref="base.view_company_tree"', "native res.company list extension"),
    ('res.company.search.onehr.branch.enterprise', "res.company dedicated branch search view"),
    ('inherit_id" ref="base.view_users_form"', "native res.users form extension"),
    ('<field name="role" position="after">', "Odoo 19 base user-list role anchor"),
    ('onehr_security.view_users_form_onehr_security', "onehr_security user form integration"),
    ('onehr_security.view_onehr_user_role_list', "security role list integration"),
    ('onehr_security.view_onehr_user_role_form', "security role form integration"),
    ('onehr_security.view_onehr_user_role_search', "security role search integration"),
    ('<pivot string="Branch Role Coverage">', "central-office pivot coverage"),
    ('<graph string="Branch Role Coverage"', "central-office graph coverage"),
    ('name="onehr_allowed_branch_ids"', "Users allowed-branch relational surface"),
    ('name="onehr_default_branch_id"', "Users default-branch relational surface"),
    ('name="onehr_effective_branch_ids"', "Users effective-branch relational surface"),
    ('name="branch_id"', "Role Assignment branch relational surface"),
):
    if marker in all_views:
        passed(label)
    else:
        failed(f"cross-addon/UI integration marker missing: {label}")

if "user_has_groups(" in all_views:
    failed("unsupported function-style user_has_groups expression present in XML")
else:
    passed("views avoid function-style authorization expressions")

# ---------------------------------------------------------------------------
# Tests and governance artifacts
# ---------------------------------------------------------------------------
test_count = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    source = path.read_text(encoding="utf-8")
    test_count += len(re.findall(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", source, flags=re.M))
    if '@tagged("post_install", "-at_install", "onehr_multicompany_branch")' not in source:
        failed(f"runtime test tag missing: {path.name}")

print(f"TEST_METHOD_COUNT: {test_count}")
if test_count == 28:
    passed("exact 28 enterprise runtime test methods, including full Users runtime dependency regressions")
else:
    failed(f"expected 28 runtime test methods, found {test_count}")

required_docs = (
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL_MULTICOMPANY_BRANCH.md",
    "ONEHR_MULTICOMPANY_BRANCH_MODEL_REGISTRY_ALIGNMENT.md",
    "BASELINE_FEATURE_PRESERVATION_MATRIX.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_BRANCH_MATRIX.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_MULTICOMPANY_BRANCH_IMPLEMENTATION_REPORT.md",
    "BOUNDED_PRODUCTION_REPAIR_19_0_1_0_1.md",
    "CROSS_MODEL_COMODEL_READ_CLOSURE.md",
    "SCOPE_ISOLATION_REPAIR_19_0_1_0_1.md",
    "BOUNDED_PRODUCTION_REPAIR_19_0_1_0_2.md",
    "USERS_RUNTIME_DEPENDENCY_CLOSURE.md",
    "SCOPE_ISOLATION_REPAIR_19_0_1_0_2.md",
    "PRESERVATION_DIFF_19_0_1_0_1_TO_19_0_1_0_2.txt",
)
missing_docs = [name for name in required_docs if not (ROOT / "docs" / name).exists()]
if missing_docs:
    failed(f"required governance documents missing: {missing_docs}")
else:
    passed("all required governance/preservation/UI/security/completeness documents present")

all_text_files = [
    path for path in ROOT.rglob("*")
    if path.is_file() and path.suffix.lower() in {".py", ".xml", ".csv", ".md", ".html", ".txt"}
]
legacy_hits = []
for path in all_text_files:
    if path == Path(__file__).resolve() or path.name == "SOURCE_ACCEPTANCE_REPORT.txt":
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "Odoo 18" in text and path.name != "BASELINE_FEATURE_PRESERVATION_MATRIX.md":
        legacy_hits.append(str(path.relative_to(ROOT)))
if legacy_hits:
    failed(f"legacy Odoo 18 labels remain outside preservation documentation: {legacy_hits}")
else:
    passed("no active Odoo 18 metadata/description remains")

# ---------------------------------------------------------------------------
# Source fingerprint and report
# ---------------------------------------------------------------------------
hasher = hashlib.sha256()
for path in sorted(
    p for p in ROOT.rglob("*")
    if p.is_file() and p.name != "SOURCE_ACCEPTANCE_REPORT.txt"
):
    relative = path.relative_to(ROOT).as_posix()
    hasher.update(relative.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(path.read_bytes())
    hasher.update(b"\0")
fingerprint = hasher.hexdigest().upper()
print(f"SOURCE_FINGERPRINT_SHA256: {fingerprint}")

report_lines = [
    "ONEHR_MULTICOMPANY_BRANCH_SOURCE_ACCEPTANCE_V3",
    f"TARGET: {ROOT}",
    f"SOURCE_FINGERPRINT_SHA256: {fingerprint}",
    f"PASS_COUNT: {len(passes)}",
    f"FAIL_COUNT: {len(errors)}",
    "",
]
report_lines += [f"PASS: {item}" for item in passes]
report_lines += [f"FAIL: {item}" for item in errors]
report_lines += [
    "",
    f"ONEHR_MULTICOMPANY_BRANCH_DIRECT_FULL_SOURCE_ACCEPTANCE: {'PASS' if not errors else 'FAIL'}",
    "WINDOWS_RUNTIME_ACCEPTANCE: PENDING",
    "ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: NO",
]
(ROOT / "docs" / "SOURCE_ACCEPTANCE_REPORT.txt").write_text(
    "\n".join(report_lines) + "\n", encoding="utf-8"
)

print("")
print("============================================================")
print(f"ONEHR_MULTICOMPANY_BRANCH_DIRECT_FULL_SOURCE_ACCEPTANCE: {'PASS' if not errors else 'FAIL'}")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_MULTICOMPANY_BRANCH_MOVE_FORWARD_READY: NO")
print("============================================================")

sys.exit(1 if errors else 0)

