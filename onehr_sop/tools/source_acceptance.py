#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {"onehr.sop", "onehr.sop.version", "onehr.sop.ack"}
EXPECTED_TABLES = {
    "onehr.sop": "onehr_sop",
    "onehr.sop.version": "onehr_sop_version",
    "onehr.sop.ack": "onehr_sop_ack",
}
EXPECTED_DEPS = {"onehr_security", "onehr_document"}
EXPECTED_VERSION = "19.0.1.0.0"
EXPECTED_TEST_METHODS = 40
PG_IDENTIFIER_LIMIT = 63

ALLOWED_RELATIONAL_MODELS = {
    "onehr.sop",
    "onehr.sop.version",
    "onehr.sop.ack",
    "onehr.document.category",
    "onehr.document",
    "onehr.document.version",
    "res.company",
    "res.users",
    "mail.template",
    "mail.activity",
    "hr.employee",
    "hr.department",
    "hr.job",
}
SOFT_MODEL_PREFIXES = (
    "onehr.portal.",
    "onehr.analytics.",
    "onehr.integration.",
    "onehr.branch",
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


def field_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "fields"
    )


# HARD GATE 0 — manifest identity / topology
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR SOP":
    ok("HARD GATE 0 project/addon identity")
else:
    fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly OneHR Security + OneHR Document")
else:
    fail("Hard dependency topology", f"found={sorted(deps)}")

forbidden_hard = {
    "onehr_portal_self_service",
    "onehr_analytics",
    "onehr_integrations_api",
    "onehr_multicompany_branch",
}
if not deps.intersection(forbidden_hard):
    ok("Soft/downstream modules were not promoted to hard dependencies")
else:
    fail("Soft dependency preservation", repr(sorted(deps.intersection(forbidden_hard))))

missing_data = [
    item for item in manifest.get("data", [])
    if not (ROOT / item).is_file()
]
if missing_data:
    fail("Manifest data inventory", f"missing={missing_data}")
else:
    ok("All manifest data files exist")


# Python syntax / exact model inventory / object methods
python_files = [
    path for path in sorted(ROOT.rglob("*.py"))
    if "__pycache__" not in path.parts
]
python_trees = {}
method_names = set()
declared_models = set()
model_classes = []

for path in python_files:
    try:
        tree = ast.parse(read(path))
    except SyntaxError as exc:
        fail("Python syntax", f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
        continue
    python_trees[path] = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(node.name)

    if path.parent.name != "models":
        continue
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = None
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "_name":
                        model_name = const_str(stmt.value)
        if model_name:
            model_classes.append((path, cls, model_name))
            declared_models.add(model_name)

if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

if declared_models == EXPECTED_MODELS:
    ok("HARD GATE 4 exact three persistent SOP model names")
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

if models_source.count('_inherit = ["onehr.mixin.audit"]') >= 3:
    ok("All SOP business models use OneHR audit mixin")
else:
    fail("OneHR audit mixin coverage")

if "mail.thread" not in models_source and "mail.activity.mixin" not in models_source:
    ok("No duplicate direct chatter/activity ownership")
else:
    fail("Audit ownership", "direct mail mixin inheritance found")


# Odoo 19 @api.depends regression
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


# Legacy tutorial removal / forbidden shortcuts
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

runtime_paths = [ROOT / "__manifest__.py", ROOT / "__init__.py"]
for folder in ("models", "security", "data", "views", "report"):
    runtime_paths.extend(
        path for path in sorted((ROOT / folder).rglob("*"))
        if path.is_file()
    )
runtime_source = "\n".join(
    read(path) for path in runtime_paths
    if path.suffix.lower() in {".py", ".xml", ".csv"}
)

tutorial_tokens = (
    "onehr_sop.onehr_sop",
    "class OnehrSop",
    "/onehr_sop/onehr_sop",
    "Short (1 phrase/line)",
)
if any(token in runtime_source for token in tutorial_tokens):
    fail("No tutorial model/controller residue")
else:
    ok("No tutorial model/controller residue")

for pattern, label in (
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (r"auth\s*=\s*['\"]public['\"]", "No public unauthenticated SOP controller"),
):
    if re.search(pattern, models_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

if models_source.count("models.Constraint(") >= 3:
    ok("Odoo 19 models.Constraint used for SOP uniqueness")
else:
    fail("Odoo 19 models.Constraint coverage")


# HARD GATE 11 — ORM/database naming safety
model_name_pattern = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
identifier_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")

for model, table in EXPECTED_TABLES.items():
    if model_name_pattern.fullmatch(model):
        ok(f"HARD GATE 11 valid ORM model name: {model}")
    else:
        fail("HARD GATE 11 model naming", model)

    predicted = model.replace(".", "_")
    if predicted != table:
        fail("HARD GATE 11 canonical table mapping", f"{model}: {predicted} != {table}")
    elif len(table.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
        fail("HARD GATE 11 table length", table)
    else:
        ok(f"HARD GATE 11 safe canonical table: {table}")

model_fields = {}
m2m_relations = {}
constraints = []

for path, cls, model_name in model_classes:
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
        name = target.id
        value = stmt.value

        is_constraint = (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id == "models"
            and value.func.attr == "Constraint"
        )
        if is_constraint:
            constraints.append((model_name, table, name))
            continue

        if not field_call(value):
            continue

        if name in fields_seen:
            fail("HARD GATE 11 duplicate field declaration", f"{model_name}.{name}")
        fields_seen[name] = value.func.attr

        if (
            not identifier_pattern.fullmatch(name)
            or len(name.encode("utf-8")) > PG_IDENTIFIER_LIMIT
        ):
            fail("HARD GATE 11 field identifier", f"{model_name}.{name}")

        indexed = any(
            kw.arg == "index"
            and isinstance(kw.value, ast.Constant)
            and bool(kw.value.value)
            for kw in value.keywords
        )
        if indexed:
            projected = f"{table}_{name}_index"
            if len(projected.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
                fail("HARD GATE 11 predicted index identifier length", projected)

        if value.func.attr in ("Many2one", "One2many", "Many2many"):
            comodel = const_str(value.args[0]) if value.args else None
            if comodel and (
                comodel not in ALLOWED_RELATIONAL_MODELS
                or any(comodel.startswith(prefix) for prefix in SOFT_MODEL_PREFIXES)
            ):
                fail(
                    "HARD GATE 11 hard ORM relation boundary",
                    f"{model_name}.{name} -> {comodel}",
                )

        if value.func.attr == "Many2many":
            if len(value.args) < 4:
                fail(
                    "HARD GATE 11 explicit Many2many relation naming",
                    f"{model_name}.{name}",
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
                        f"{model_name}.{name}: {identifier}",
                    )

            if relation:
                current = (model_name, name, column1, column2)
                previous = m2m_relations.get(relation)
                if previous and previous != current:
                    fail(
                        "HARD GATE 11 duplicate Many2many relation table",
                        f"{relation}: {previous} / {current}",
                    )
                m2m_relations[relation] = current

    model_fields[model_name] = fields_seen

if not any(
    label.startswith("HARD GATE 11 field")
    or label.startswith("HARD GATE 11 predicted index")
    or label.startswith("HARD GATE 11 duplicate field")
    for label, _ in failures
):
    ok(
        "HARD GATE 11 safe ORM field/index identifiers "
        f"({sum(len(v) for v in model_fields.values())} fields)"
    )

if not any(
    label.startswith("HARD GATE 11 Many2many")
    or label == "HARD GATE 11 duplicate Many2many relation table"
    for label, _ in failures
):
    ok(
        "HARD GATE 11 explicit unique Many2many identifiers "
        f"({len(m2m_relations)} relations)"
    )

if not any(
    label == "HARD GATE 11 hard ORM relation boundary"
    for label, _ in failures
):
    ok("HARD GATE 11 no static ORM relation to soft-module models")

for model_name, table, attr_name in constraints:
    normalized = attr_name.lstrip("_")
    projected = f"{table}_{normalized}"
    if (
        not identifier_pattern.fullmatch(normalized)
        or len(normalized.encode("utf-8")) > PG_IDENTIFIER_LIMIT
        or len(projected.encode("utf-8")) > PG_IDENTIFIER_LIMIT
    ):
        fail(
            "HARD GATE 11 constraint identifier safety",
            f"{model_name}.{attr_name} -> {projected}",
        )

if constraints and not any(
    label == "HARD GATE 11 constraint identifier safety"
    for label, _ in failures
):
    ok(f"HARD GATE 11 safe constraint identifiers ({len(constraints)} constraints)")


# XML syntax / Odoo 19 view contract / cross-references
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
    if path.parent.name != "views":
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
    "Badge": 'widget="badge"',
    "Ribbon": 'widget name="web_ribbon"',
    "Chatter": "<chatter",
}.items():
    if token in view_text:
        ok(f"HARD GATE 6 enterprise UI — {label}")
    else:
        fail(f"HARD GATE 6 enterprise UI — {label}")

missing_methods = set()
for path, xml_root in xml_roots.items():
    for button in xml_root.iter("button"):
        if button.attrib.get("type") == "object":
            method = button.attrib.get("name")
            if method and method not in method_names:
                missing_methods.add(f"{path.relative_to(ROOT)}:{method}")
if missing_methods:
    fail("Object button → Python method cross-reference", ", ".join(sorted(missing_methods)))
else:
    ok("Object button → Python method cross-reference")

xml_ids = {}
duplicates = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter():
        xml_id = node.attrib.get("id")
        if not xml_id or "." in xml_id:
            continue
        if xml_id in xml_ids:
            duplicates.append(
                f"{xml_id}: {xml_ids[xml_id]} / {path.relative_to(ROOT)}"
            )
        else:
            xml_ids[xml_id] = str(path.relative_to(ROOT))
if duplicates:
    fail("HARD GATE 11 unique local XML external IDs", "; ".join(duplicates))
else:
    ok(f"HARD GATE 11 unique local XML external IDs ({len(xml_ids)} IDs)")


# Security
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(csv.DictReader(read(acl_path).splitlines()))
except Exception as exc:
    acl_rows = []
    fail("ACL CSV parse", str(exc))
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" in read(acl_path):
    fail("HARD GATE 10 least privilege", "base.group_user appears in custom SOP ACL")
else:
    ok("HARD GATE 10 no broad base.group_user SOP CRUD")

security_text = read(ROOT / "security" / "onehr_sop_security.xml")
rules_text = read(ROOT / "security" / "onehr_sop_rules.xml")

for group in (
    "group_onehr_sop_reader",
    "group_onehr_sop_editor",
    "group_onehr_sop_approver",
    "group_onehr_sop_admin",
):
    if group in security_text:
        ok(f"Security role present: {group}")
    else:
        fail(f"Security role present: {group}")

if 'model="res.groups.privilege"' in security_text:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

if rules_text.count('<field name="global" eval="True"/>') >= 3:
    ok("Global company isolation rules on all three SOP models")
else:
    fail("Global company isolation rule coverage")

for token, label in (
    ("current_version_id.ack_ids.employee_user_id", "Reader SOP audience boundary"),
    ("ack_ids.employee_user_id", "Reader Version audience boundary"),
    ("employee_user_id", "Reader own acknowledgement boundary"),
):
    if token in rules_text:
        ok(label)
    else:
        fail(label)

if "_ACTION_CONTEXT" in models_source:
    ok("Server-side lifecycle/evidence action contexts present")
else:
    fail("Server-side workflow guards")

if models_source.count("@api.ondelete(at_uninstall=False)") >= 3:
    ok("Historical deletion guards cover all three SOP models")
else:
    fail("Historical deletion guard coverage")


# Functional contract
functional_tokens = (
    ("target_department_ids", "targeted unit publication"),
    ("target_job_ids", "targeted job/role publication"),
    ("target_employee_ids", "specific employee publication"),
    ("action_acknowledge", "Read & Agree acknowledgement"),
    ("acknowledged_at", "ack timestamp"),
    ("retention_until", "retention"),
    ("review_due_date", "periodic review"),
    ("_cron_sop_governance", "review/ack reminder scheduler"),
    ("action_submit_review", "Draft → Review"),
    ("action_approve", "Review → Approved"),
    ("action_publish", "Approved → Published"),
    ("action_mark_obsolete", "Published → Obsolete"),
    ("content_fingerprint", "approved content/audience SHA-256"),
    ("archive_document_version_id", "OneHR Document archive version"),
    ("action_export_ack_csv", "acknowledgement audit CSV"),
    ("ack_rate", "acknowledgement rate"),
    ("days_to_90_ack", "publish to 90% acknowledgement KPI"),
    ("action_send_publication_notice", "publication notification"),
    ("action_send_ack_reminders", "ack reminder notification"),
    ("onehr_sop_portal_payload", "Portal-safe service"),
    ("onehr_sop_ack_status", "API-ready employee status service"),
    ("onehr_sop_kpi_snapshot", "Analytics KPI service"),
)
for token, label in functional_tokens:
    if token in models_source:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

report_text = read(ROOT / "report" / "sop_reports.xml")
for token, label in (
    ("action_report_sop_document", "SOP QWeb PDF"),
    ("action_report_sop_compliance", "Compliance QWeb PDF"),
    ("action_report_sop_review_register", "Review/expiry register QWeb PDF"),
):
    if token in report_text:
        ok(label)
    else:
        fail(label)

if "onehr_base.menu_onehr_root" in read(ROOT / "views" / "menus.xml"):
    ok("Integrated OneHR root navigation without sibling source edit")
else:
    fail("OneHR root navigation integration")


# Test inventory
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


# Guardrail/doc evidence
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
missing_docs = [
    name for name in sorted(mandatory_docs)
    if not (ROOT / "docs" / name).is_file()
]
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
if "63-byte" in identifier_doc and "onehr_sop_version" in identifier_doc:
    ok("HARD GATE 11 dedicated identifier-safety evidence")
else:
    fail("HARD GATE 11 identifier-safety evidence")

registry_doc = read(ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md")
if "REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION" in registry_doc:
    warn("Exact Master Model Registry ED rows remain pending; classifications were not invented")
else:
    fail("Registry ED pending marker")

if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else:
    fail("Odoo CE UI ownership", "unexpected Gantt view found")


print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared_models)}")
print(f"ORM_FIELD_COUNT={sum(len(v) for v in model_fields.values())}")
print(f"M2M_RELATION_COUNT={len(m2m_relations)}")
print(f"LOCAL_XML_ID_COUNT={len(xml_ids)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_SOP_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_SOP_MOVE_FORWARD_READY=NO")
