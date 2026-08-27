#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {"onehr.jd", "onehr.jd.version"}
EXPECTED_TABLES = {
    "onehr.jd": "onehr_jd",
    "onehr.jd.version": "onehr_jd_version",
}
EXPECTED_DEPS = {"onehr_base", "onehr_security"}
EXPECTED_VERSION = "19.0.1.0.0"
EXPECTED_TEST_METHODS = 30
PG_IDENTIFIER_LIMIT = 63

ALLOWED_RELATIONAL_MODELS = {
    "onehr.jd",
    "onehr.jd.version",
    "onehr.position",
    "onehr.grade",
    "onehr.job.family",
    "res.company",
    "res.users",
    "hr.job",
    "hr.department",
    "ir.attachment",
}
SOFT_MODEL_PREFIXES = (
    "onehr.appraisal.",
    "onehr.position.competency",
    "onehr.competency",
    "onehr.recruitment.",
    "onehr.portal.",
)

passes = []
warnings = []
failures = []


def ok(label):
    passes.append(label)
    print(f"PASS: {label}")


def warn(label):
    warnings.append(label)
    print(f"WARN: {label}")


def fail(label, detail=""):
    failures.append((label, detail))
    print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def is_call(node, owner, method):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == owner
        and node.func.attr == method
    )


# ---------------------------------------------------------------------------
# HARD GATE 0 — Project identity and manifest topology
# ---------------------------------------------------------------------------
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR Job Description":
    ok("HARD GATE 0 project/addon identity")
else:
    fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly OneHR Base + OneHR Security")
else:
    fail("Hard dependency topology", f"found={sorted(deps)}")

soft_dep_names = {
    "onehr_recruitment",
    "onehr_appraisal",
    "onehr_career_succession",
    "onehr_portal_self_service",
    "onehr_integrations_api",
    "onehr_analytics",
}
if not deps.intersection(soft_dep_names):
    ok("Soft integrations are not promoted to hard dependencies")
else:
    fail("Soft dependency preservation", f"hard={sorted(deps.intersection(soft_dep_names))}")

missing_data = [
    item for item in manifest.get("data", [])
    if not (ROOT / item).is_file()
]
if missing_data:
    fail("Manifest data file inventory", f"missing={missing_data}")
else:
    ok("All manifest data files exist")


# ---------------------------------------------------------------------------
# Python syntax, exact model inventory, method inventory
# ---------------------------------------------------------------------------
python_files = [
    path for path in sorted(ROOT.rglob("*.py"))
    if "__pycache__" not in path.parts
]
python_trees = {}
method_names = set()
declared_models = set()
class_model_map = {}

for path in python_files:
    try:
        tree = ast.parse(read(path))
    except SyntaxError as exc:
        fail(
            "Python syntax",
            f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}",
        )
        continue

    python_trees[path] = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(node.name)

    if "models" not in path.parts:
        continue
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        model_name = None
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "_name":
                        model_name = const_str(stmt.value)
        if model_name:
            class_model_map[(path, cls.name)] = model_name
            if model_name in EXPECTED_MODELS:
                declared_models.add(model_name)

if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

if declared_models == EXPECTED_MODELS:
    ok("HARD GATE 4 exact two persistent JD model names")
else:
    fail("HARD GATE 4 exact model inventory", f"found={sorted(declared_models)}")

models_source = "\n".join(
    read(path) for path in sorted((ROOT / "models").glob("*.py"))
)

for model in sorted(EXPECTED_MODELS):
    if f'_name = "{model}"' in models_source:
        ok(f"Persistent model implemented: {model}")
    else:
        fail(f"Persistent model implemented: {model}")

if models_source.count('_inherit = ["onehr.mixin.audit"]') >= 2:
    ok("Both JD business models use OneHR audit mixin")
else:
    fail("OneHR audit mixin coverage")

if "mail.thread" not in models_source and "mail.activity.mixin" not in models_source:
    ok("No duplicate direct chatter/audit ownership")
else:
    fail("Audit ownership", "direct mail mixin inheritance found")


# ---------------------------------------------------------------------------
# Odoo 19 compute dependency regression guard
# ---------------------------------------------------------------------------
bad_depends = []
for path, tree in python_trees.items():
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "api"
            and node.func.attr == "depends"
        ):
            continue
        for arg in node.args:
            value = const_str(arg)
            if value and (value == "id" or value.endswith(".id")):
                bad_depends.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}:{value}"
                )

if bad_depends:
    fail("Odoo 19 @api.depends contract", ", ".join(bad_depends))
else:
    ok("Odoo 19 @api.depends contains no explicit id/.id dependency")


# ---------------------------------------------------------------------------
# Tutorial scaffold removal and forbidden source shortcuts
# ---------------------------------------------------------------------------
for legacy in (
    ROOT / "controllers",
    ROOT / "demo",
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
):
    if legacy.exists():
        fail("Generic tutorial scaffold removed", str(legacy.relative_to(ROOT)))

if not any(label == "Generic tutorial scaffold removed" for label, _ in failures):
    ok("Generic tutorial scaffold removed completely")

runtime_source_paths = [ROOT / "__manifest__.py", ROOT / "__init__.py"]
for folder in ("models", "security", "data", "views", "report"):
    runtime_source_paths.extend(
        path for path in sorted((ROOT / folder).rglob("*"))
        if path.is_file()
    )
runtime_source = "\n".join(
    read(path) for path in runtime_source_paths
    if path.suffix.lower() in {".py", ".xml", ".csv"}
)

tutorial_tokens = (
    "onehr_job_description.onehr_job_description",
    "class OnehrJobDescription",
    "/onehr_job_description/onehr_job_description",
)
if any(token in runtime_source for token in tutorial_tokens):
    fail("No tutorial model/controller residue")
else:
    ok("No tutorial model/controller residue")

business_source = "\n".join(
    read(path) for path in sorted((ROOT / "models").glob("*.py"))
)

for pattern, label in (
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"auth\s*=\s*['\"]public['\"]", "No public unauthenticated JD controller"),
):
    if re.search(pattern, business_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

if business_source.count("models.Constraint(") >= 3:
    ok("Odoo 19 models.Constraint used for JD uniqueness")
else:
    fail("Odoo 19 models.Constraint coverage")


# ---------------------------------------------------------------------------
# HARD GATE 11 — Database Identifier & ORM Naming Safety
# ---------------------------------------------------------------------------
model_name_pattern = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
identifier_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")

for model, table in EXPECTED_TABLES.items():
    if not model_name_pattern.fullmatch(model):
        fail("HARD GATE 11 model naming", model)
    else:
        ok(f"HARD GATE 11 valid ORM model name: {model}")

    predicted = model.replace(".", "_")
    if predicted != table:
        fail(
            "HARD GATE 11 canonical table mapping",
            f"{model}: predicted={predicted}, expected={table}",
        )
    elif len(table.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
        fail("HARD GATE 11 table length", table)
    else:
        ok(f"HARD GATE 11 safe table identifier: {table}")

model_field_inventory = {}
many2many_relations = {}
constraint_identifiers = []

for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(read(path))
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        model_name = None
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "_name":
                        model_name = const_str(stmt.value)
        if model_name not in EXPECTED_MODELS:
            continue

        table = EXPECTED_TABLES[model_name]
        fields_seen = {}
        for stmt in cls.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            field_name = target.id
            value = stmt.value

            if is_call(value, "fields", "Many2one") or is_call(value, "fields", "One2many") or is_call(value, "fields", "Many2many"):
                comodel = const_str(value.args[0]) if value.args else None
                if comodel and (
                    comodel not in ALLOWED_RELATIONAL_MODELS
                    or any(comodel.startswith(prefix) for prefix in SOFT_MODEL_PREFIXES)
                ):
                    fail(
                        "HARD GATE 11 hard ORM relation boundary",
                        f"{model_name}.{field_name} -> {comodel}",
                    )

            is_field = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == "fields"
            )
            if not is_field:
                if is_call(value, "models", "Constraint"):
                    constraint_identifiers.append((model_name, table, field_name))
                continue

            if field_name in fields_seen:
                fail(
                    "HARD GATE 11 duplicate field declaration",
                    f"{model_name}.{field_name}",
                )
            fields_seen[field_name] = value.func.attr

            if (
                not identifier_pattern.fullmatch(field_name)
                or len(field_name.encode("utf-8")) > PG_IDENTIFIER_LIMIT
            ):
                fail(
                    "HARD GATE 11 field identifier",
                    f"{model_name}.{field_name}",
                )

            index_enabled = False
            for kw in value.keywords:
                if (
                    kw.arg == "index"
                    and isinstance(kw.value, ast.Constant)
                    and bool(kw.value.value)
                ):
                    index_enabled = True
            if index_enabled:
                predicted_index = f"{table}_{field_name}_index"
                if len(predicted_index.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
                    fail(
                        "HARD GATE 11 predicted index identifier length",
                        predicted_index,
                    )

            if value.func.attr == "Many2many":
                if len(value.args) < 4:
                    fail(
                        "HARD GATE 11 explicit Many2many relation naming",
                        f"{model_name}.{field_name} does not define relation/columns",
                    )
                    continue
                relation = const_str(value.args[1])
                column1 = const_str(value.args[2])
                column2 = const_str(value.args[3])
                for label, identifier in (
                    ("relation", relation),
                    ("column1", column1),
                    ("column2", column2),
                ):
                    if (
                        not identifier
                        or not identifier_pattern.fullmatch(identifier)
                        or len(identifier.encode("utf-8")) > PG_IDENTIFIER_LIMIT
                    ):
                        fail(
                            f"HARD GATE 11 Many2many {label}",
                            f"{model_name}.{field_name}: {identifier}",
                        )
                if relation:
                    previous = many2many_relations.get(relation)
                    current = (model_name, field_name, column1, column2)
                    if previous and previous != current:
                        fail(
                            "HARD GATE 11 duplicate Many2many relation table",
                            f"{relation}: {previous} / {current}",
                        )
                    many2many_relations[relation] = current

        model_field_inventory[model_name] = fields_seen

if not any(
    label.startswith("HARD GATE 11 field")
    or label.startswith("HARD GATE 11 predicted index")
    or label.startswith("HARD GATE 11 duplicate field")
    for label, _ in failures
):
    field_count = sum(len(fields_) for fields_ in model_field_inventory.values())
    ok(f"HARD GATE 11 safe ORM field/index identifiers ({field_count} fields)")

if not any(
    label.startswith("HARD GATE 11 Many2many")
    or label == "HARD GATE 11 duplicate Many2many relation table"
    for label, _ in failures
):
    ok(
        "HARD GATE 11 explicit unique Many2many relation identifiers "
        f"({len(many2many_relations)} relations)"
    )

if not any(
    label == "HARD GATE 11 hard ORM relation boundary"
    for label, _ in failures
):
    ok("HARD GATE 11 no static ORM relation to soft-module models")

for model_name, table, attr_name in constraint_identifiers:
    normalized = attr_name.lstrip("_")
    predicted_db_name = f"{table}_{normalized}"
    if (
        not identifier_pattern.fullmatch(normalized)
        or len(normalized.encode("utf-8")) > PG_IDENTIFIER_LIMIT
        or len(predicted_db_name.encode("utf-8")) > PG_IDENTIFIER_LIMIT
    ):
        fail(
            "HARD GATE 11 constraint identifier safety",
            f"{model_name}.{attr_name} -> {predicted_db_name}",
        )

if constraint_identifiers and not any(
    label == "HARD GATE 11 constraint identifier safety"
    for label, _ in failures
):
    ok(
        "HARD GATE 11 safe deterministic constraint identifiers "
        f"({len(constraint_identifiers)} constraints)"
    )


# ---------------------------------------------------------------------------
# XML syntax and Odoo 19 view contract
# ---------------------------------------------------------------------------
xml_files = sorted(ROOT.rglob("*.xml"))
xml_roots = {}
for path in xml_files:
    try:
        xml_roots[path] = ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail("XML syntax", f"{path.relative_to(ROOT)}: {exc}")

if len(xml_roots) == len(xml_files):
    ok(f"XML syntax ({len(xml_files)} files)")

view_text = "\n".join(
    read(path) for path in sorted((ROOT / "views").glob("*.xml"))
)
if "<tree" in view_text or "</tree>" in view_text:
    fail("Odoo 19 list syntax", "legacy tree tag found")
else:
    ok("Odoo 19 operational lists use <list>")

if "attrs=" in view_text or re.search(r"\sstates\s*=", view_text):
    fail("Odoo 19 direct view modifiers", "legacy attrs/states found")
else:
    ok("Odoo 19 direct view modifiers")

bad_search_groups = []
for path, xml_root in xml_roots.items():
    if "views" not in path.parts:
        continue
    for search in xml_root.iter("search"):
        for group in search.iter("group"):
            if group.attrib:
                bad_search_groups.append(
                    f"{path.relative_to(ROOT)}:{group.attrib}"
                )

if bad_search_groups:
    fail("Odoo 19 search <group> contract", "; ".join(bad_search_groups))
else:
    ok("Odoo 19 search <group> elements have no attributes")

view_blocks = re.findall(
    r'<record[^>]*model="ir\.ui\.view".*?</record>',
    view_text,
    flags=re.S,
)
for model in sorted(EXPECTED_MODELS):
    blocks = [
        block for block in view_blocks
        if f'<field name="model">{model}</field>' in block
    ]
    kinds = set()
    for block in blocks:
        if "<list" in block:
            kinds.add("list")
        if "<form" in block:
            kinds.add("form")
        if "<search" in block:
            kinds.add("search")
    if {"list", "form", "search"} <= kinds:
        ok(f"HARD GATE 7/8/9 List/Form/Search: {model}")
    else:
        fail(
            f"HARD GATE 7/8/9 List/Form/Search: {model}",
            f"found={sorted(kinds)}",
        )

for label, token in {
    "Statusbar": 'widget="statusbar"',
    "Smart Button": "oe_stat_button",
    "Body Button": 'class="btn-secondary"',
    "One2many Row Button": 'name="version_ids"',
    "Kanban": "<kanban",
    "Calendar": "<calendar",
    "Pivot": "<pivot",
    "Graph": "<graph",
    "Badges": 'widget="badge"',
    "Ribbons": 'widget name="web_ribbon"',
    "Chatter": "<chatter",
}.items():
    if token in view_text:
        ok(f"HARD GATE 6 enterprise UI — {label}")
    else:
        fail(f"HARD GATE 6 enterprise UI — {label}")

missing_button_methods = set()
for path, xml_root in xml_roots.items():
    for button in xml_root.iter("button"):
        if button.attrib.get("type") == "object":
            method = button.attrib.get("name")
            if method and method not in method_names:
                missing_button_methods.add(
                    f"{path.relative_to(ROOT)}:{method}"
                )

if missing_button_methods:
    fail(
        "Object button → Python method cross-reference",
        ", ".join(sorted(missing_button_methods)),
    )
else:
    ok("Object button → Python method cross-reference")

local_xml_ids = {}
duplicate_xml_ids = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter():
        xml_id = node.attrib.get("id")
        if not xml_id or "." in xml_id:
            continue
        if xml_id in local_xml_ids:
            duplicate_xml_ids.append(
                f"{xml_id}: {local_xml_ids[xml_id]} / {path.relative_to(ROOT)}"
            )
        else:
            local_xml_ids[xml_id] = str(path.relative_to(ROOT))

if duplicate_xml_ids:
    fail("HARD GATE 11 unique local XML external IDs", "; ".join(duplicate_xml_ids))
else:
    ok(
        "HARD GATE 11 unique local XML external IDs "
        f"({len(local_xml_ids)} IDs)"
    )


# ---------------------------------------------------------------------------
# Security hard gate
# ---------------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(csv.DictReader(read(acl_path).splitlines()))
except Exception as exc:
    acl_rows = []
    fail("ACL CSV parse", str(exc))
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" in read(acl_path):
    fail("HARD GATE 10 least privilege", "base.group_user appears in custom ACL")
else:
    ok("HARD GATE 10 no broad base.group_user JD CRUD")

security_text = read(ROOT / "security" / "onehr_job_description_security.xml")
rules_text = read(ROOT / "security" / "onehr_job_description_rules.xml")
for group in (
    "group_onehr_jd_reader",
    "group_onehr_jd_editor",
    "group_onehr_jd_approver",
    "group_onehr_jd_admin",
):
    if group in security_text:
        ok(f"Security role present: {group}")
    else:
        fail(f"Security role present: {group}")

if 'model="res.groups.privilege"' in security_text:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

if rules_text.count('<field name="global" eval="True"/>') >= 2:
    ok("Global company isolation rules on both JD models")
else:
    fail("Global company isolation rule coverage")

if "current published" in rules_text.lower() and "is_current" in rules_text:
    ok("Reader rule limits version visibility to current published evidence")
else:
    fail("Reader published-only rule")

if "_ACTION_CONTEXT" in business_source and "_GOVERNANCE_CONTEXT" in business_source:
    ok("Action-controlled lifecycle/governance write guards present")
else:
    fail("Action-controlled workflow guards")

if business_source.count("@api.ondelete(at_uninstall=False)") >= 2:
    ok("Historical evidence deletion guards on both business models")
else:
    fail("Historical evidence deletion guard coverage")


# ---------------------------------------------------------------------------
# Product / enterprise completeness checks
# ---------------------------------------------------------------------------
functional_tokens = (
    ("is_template", "job-family JD templates"),
    ("position_id", "canonical position mapping"),
    ("version_ids", "version/history"),
    ("purpose", "position purpose"),
    ("key_responsibilities", "responsibilities"),
    ("kpi_expectations", "KPI expectations"),
    ("competency_requirements", "competency requirements"),
    ("hse_risk_level", "HSE/K3 risk"),
    ("hse_controls", "HSE/K3 controls"),
    ("action_submit_review", "Draft → Review"),
    ("action_approve", "Review → Approved"),
    ("action_publish", "Approved → Published"),
    ("action_generate_position_jds", "template → position generation"),
    ("action_sync_from_job_family_template", "template synchronization"),
    ("action_import_source_document", "external JD source import"),
    ("action_refresh_competency_snapshot", "Career soft competency refresh"),
    ("content_fingerprint", "approval/publication SHA-256 evidence"),
    ("coverage_score", "JD position coverage"),
    ("version_age_days", "average version age source metric"),
    ("review_overdue", "review governance"),
    ("_cron_refresh_governance_metrics", "review reminder scheduler"),
    ("onehr_jd_recruitment_payload", "Recruitment service"),
    ("onehr_jd_appraisal_payload", "Appraisal service"),
    ("onehr_jd_portal_payload", "Portal-safe service"),
    ("onehr_jd_api_payload", "Integrations API service"),
    ("onehr_jd_kpi_snapshot", "Analytics KPI snapshot"),
)
for token, label in functional_tokens:
    if token in business_source:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

report_text = read(ROOT / "report" / "job_description_reports.xml")
for token, label in (
    ("action_report_jd_document", "Job Description QWeb PDF"),
    ("action_report_jd_comparison", "Version comparison QWeb PDF"),
    ("action_report_jd_register", "JD register QWeb PDF"),
):
    if token in report_text:
        ok(label)
    else:
        fail(label)

if "onehr_base.menu_onehr_root" in read(ROOT / "views" / "menus.xml"):
    ok("Integrated OneHR Governance navigation without sibling source edit")
else:
    fail("OneHR root navigation integration")


# ---------------------------------------------------------------------------
# Runtime test inventory
# ---------------------------------------------------------------------------
test_methods = []
for path in sorted((ROOT / "tests").glob("test_*.py")):
    tree = ast.parse(read(path))
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ):
            test_methods.append((path.name, node.name))

if len(test_methods) == EXPECTED_TEST_METHODS:
    ok(f"Runtime test inventory exactly {EXPECTED_TEST_METHODS} methods")
else:
    fail(
        "Runtime test inventory",
        f"expected={EXPECTED_TEST_METHODS}, found={len(test_methods)}",
    )

if all(
    "@tagged" in read(path)
    for path in sorted((ROOT / "tests").glob("test_*.py"))
):
    ok("Runtime test suites are post-install tagged")
else:
    fail("Runtime test suite tags")


# ---------------------------------------------------------------------------
# Documentation and all 16 numbered gates including Gate 11
# ---------------------------------------------------------------------------
mandatory_docs = {
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_PRIVACY_MATRIX.md",
    "INTEGRATION_CONTRACT.md",
    "MODEL_REGISTRY_ALIGNMENT.md",
    "DATABASE_IDENTIFIER_ORM_NAMING_SAFETY.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE.md",
    "IMPLEMENTATION_REPORT.md",
    "ROOT_GUARDRAIL_REFERENCE.md",
}
missing_docs = sorted(
    name for name in mandatory_docs
    if not (ROOT / "docs" / name).is_file()
)
if missing_docs:
    fail("Mandatory Enterprise documentation", f"missing={missing_docs}")
else:
    ok("Mandatory Enterprise documentation set")

guardrail = read(ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for gate in range(16):
    if f"HARD GATE {gate}" in guardrail:
        ok(f"Guardrail contains HARD GATE {gate}")
    else:
        fail(f"Guardrail contains HARD GATE {gate}")

if "CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER" in guardrail:
    ok("Codex role locked to bounded implementation worker")
else:
    fail("Codex bounded-worker role")

if "MAX_CODEX_ATTEMPTS_PER_TASK: 2" in guardrail:
    ok("Codex retry limit = 2")
else:
    fail("Codex retry limit")

identifier_doc = read(ROOT / "docs" / "DATABASE_IDENTIFIER_ORM_NAMING_SAFETY.md")
if "63 bytes" in identifier_doc and "onehr_jd_version" in identifier_doc:
    ok("HARD GATE 11 dedicated identifier-safety evidence document")
else:
    fail("HARD GATE 11 identifier-safety evidence document")

registry_doc = read(ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry_doc:
    warn("Exact Master Model Registry ED rows remain pending; ED classifications were not invented")
else:
    fail("Registry ED pending marker")

if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else:
    fail("Odoo CE UI ownership", "unexpected Gantt view found")


# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared_models)}")
print(f"ORM_FIELD_COUNT={sum(len(v) for v in model_field_inventory.values())}")
print(f"M2M_RELATION_COUNT={len(many2many_relations)}")
print(f"LOCAL_XML_ID_COUNT={len(local_xml_ids)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_JOB_DESCRIPTION_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_JOB_DESCRIPTION_MOVE_FORWARD_READY=NO")
