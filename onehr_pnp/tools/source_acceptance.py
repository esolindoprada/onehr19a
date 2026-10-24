
#!/usr/bin/env python3
from pathlib import Path
import ast
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODELS = {
    "onehr.policy",
    "onehr.policy.ack",
    "onehr.policy.evidence",
}
EXPECTED_TABLES = {
    "onehr.policy": "onehr_policy",
    "onehr.policy.ack": "onehr_policy_ack",
    "onehr.policy.evidence": "onehr_policy_evidence",
}
EXPECTED_DEPS = {
    "onehr_security",
    "onehr_document",
    "onehr_workflow_approval",
}
EXPECTED_VERSION = "19.0.1.0.1"
EXPECTED_TEST_METHODS = 49
PG_IDENTIFIER_LIMIT = 63

SOFT_MODULE_MODELS = {
    "onehr.sop",
}
SOFT_MODEL_PREFIXES = (
    "onehr.portal.",
    "onehr.analytics.",
    "onehr.branch",
    "onehr.integration.",
)
ALLOWED_RELATIONAL_MODELS = {
    *EXPECTED_MODELS,
    "res.company",
    "res.users",
    "ir.attachment",
    "ir.model",
    "hr.employee",
    "hr.department",
    "hr.job",
    "mail.template",
    "onehr.approval.request",
    "onehr.document.category",
    "onehr.document",
    "onehr.document.version",
}
INHERITED_OBJECT_METHODS = {
    "action_open_approval_requests",
}

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


# ---------------------------------------------------------------------------
# HARD GATE 0 — identity / manifest / exact dependency topology
# ---------------------------------------------------------------------------
try:
    manifest = ast.literal_eval(read(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    fail("HARD GATE 0 manifest parse", str(exc))
else:
    ok("HARD GATE 0 manifest parse")

if manifest.get("name") == "OneHR Policies & Procedures":
    ok("HARD GATE 0 project/addon identity")
else:
    fail("HARD GATE 0 project/addon identity", repr(manifest.get("name")))

if manifest.get("version") == EXPECTED_VERSION:
    ok(f"Manifest version {EXPECTED_VERSION}")
else:
    fail("Manifest version", repr(manifest.get("version")))

deps = set(manifest.get("depends", []))
if deps == EXPECTED_DEPS:
    ok("Hard dependencies exactly Security + Document + Workflow Approval")
else:
    fail("Hard dependency topology", f"found={sorted(deps)}")

forbidden_hard = {
    "onehr_sop",
    "onehr_portal_self_service",
    "onehr_analytics",
    "onehr_multicompany_branch",
    "onehr_integrations_api",
}
if not deps.intersection(forbidden_hard):
    ok("Soft/downstream modules were not promoted to hard dependencies")
else:
    fail(
        "Soft dependency preservation",
        repr(sorted(deps.intersection(forbidden_hard))),
    )

missing_data = [
    item
    for item in manifest.get("data", [])
    if not (ROOT / item).is_file()
]
if missing_data:
    fail("Manifest data inventory", f"missing={missing_data}")
else:
    ok("All manifest data files exist")


# ---------------------------------------------------------------------------
# Python syntax, persistent model inventory, transient extension inventory
# ---------------------------------------------------------------------------
python_files = [
    path
    for path in sorted(ROOT.rglob("*.py"))
    if "__pycache__" not in path.parts
]
python_trees = {}
method_names = set()
declared_models = set()
model_classes = []
extension_classes = []

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

    if path.parent.name != "models":
        continue

    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = None
        inherited_model = None
        for stmt in cls.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "_name":
                    model_name = const_str(stmt.value)
                elif target.id == "_inherit":
                    inherited_model = const_str(stmt.value)

        if model_name:
            declared_models.add(model_name)
            model_classes.append((path, cls, model_name))
        elif inherited_model:
            extension_classes.append((path, cls, inherited_model))

if len(python_trees) == len(python_files):
    ok(f"Python syntax ({len(python_files)} files)")

if declared_models == EXPECTED_MODELS:
    ok("HARD GATE 4 exact three persistent PnP model names")
else:
    fail(
        "HARD GATE 4 exact model inventory",
        f"found={sorted(declared_models)}",
    )

if any(
    inherited == "res.config.settings"
    for _, _, inherited in extension_classes
):
    ok("Approved res.config.settings transient extension present")
else:
    fail("Approved res.config.settings transient extension")

models_source = "\n".join(
    read(path)
    for path in sorted((ROOT / "models").glob("*.py"))
)

for model in sorted(EXPECTED_MODELS):
    if f'_name = "{model}"' in models_source:
        ok(f"Persistent model implemented: {model}")
    else:
        fail(f"Persistent model implemented: {model}")

if '_inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]' in models_source:
    ok("Policy integrates OneHR audit + approved Workflow source mixin")
else:
    fail("Policy Workflow/Audit mixin ownership")

if models_source.count('_inherit = ["onehr.mixin.audit"]') >= 2:
    ok("Acknowledgement/Evidence use OneHR audit mixin")
else:
    fail("OneHR audit mixin coverage")

if "mail.thread" not in models_source and "mail.activity.mixin" not in models_source:
    ok("No duplicate direct chatter/activity ownership")
else:
    fail("Audit ownership", "direct mail mixin inheritance found")


# ---------------------------------------------------------------------------
# Odoo 19 compatibility
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
    fail(
        "Odoo 19 @api.depends contract",
        ", ".join(bad_depends),
    )
else:
    ok("Odoo 19 @api.depends contains no explicit id/.id dependency")

for legacy in (
    ROOT / "controllers",
    ROOT / "demo",
    ROOT / "models" / "models.py",
    ROOT / "views" / "views.xml",
    ROOT / "views" / "templates.xml",
):
    if legacy.exists():
        fail(
            "Generic tutorial scaffold removed",
            str(legacy.relative_to(ROOT)),
        )

if not any(
    label == "Generic tutorial scaffold removed"
    for label, _ in failures
):
    ok("Generic tutorial scaffold removed completely")

tutorial_tokens = (
    "onehr_pnp.onehr_pnp",
    "class OnehrPnp",
    "/onehr_pnp/onehr_pnp",
    "Short (1 phrase/line)",
)
runtime_source = "\n".join(
    read(path)
    for folder in (
        "models",
        "security",
        "data",
        "views",
        "report",
    )
    for path in sorted((ROOT / folder).rglob("*"))
    if path.is_file()
    and path.suffix.lower() in {".py", ".xml", ".csv"}
)
if any(token in runtime_source for token in tutorial_tokens):
    fail("No tutorial model/controller residue")
else:
    ok("No tutorial model/controller residue")

for pattern, label in (
    (r"_sql_constraints", "No legacy _sql_constraints"),
    (r"\.sudo\s*\(", "No business sudo() bypass"),
    (
        r"auth\s*=\s*['\"]public['\"]",
        "No public unauthenticated PnP controller",
    ),
):
    if re.search(pattern, models_source):
        fail(label, "forbidden pattern found")
    else:
        ok(label)

if models_source.count("models.Constraint(") >= 2:
    ok("Odoo 19 models.Constraint used for governed uniqueness")
else:
    fail("Odoo 19 models.Constraint coverage")


# ---------------------------------------------------------------------------
# HARD GATE 11 — database identifier / ORM naming safety
# ---------------------------------------------------------------------------
identifier_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")
model_name_pattern = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"
)

for model, table in EXPECTED_TABLES.items():
    if model_name_pattern.fullmatch(model):
        ok(f"HARD GATE 11 valid ORM model name: {model}")
    else:
        fail("HARD GATE 11 model naming", model)

    predicted = model.replace(".", "_")
    if predicted != table:
        fail(
            "HARD GATE 11 canonical table mapping",
            f"{model}: {predicted} != {table}",
        )
    elif len(table.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
        fail("HARD GATE 11 table length", table)
    else:
        ok(f"HARD GATE 11 safe canonical table: {table}")

model_fields = {}
extension_field_names = []
m2m_relations = {}
constraints = []

for path, cls, model_name in model_classes:
    if model_name not in EXPECTED_MODELS:
        continue
    table = EXPECTED_TABLES[model_name]
    fields_seen = {}

    for stmt in cls.body:
        if (
            not isinstance(stmt, ast.Assign)
            or len(stmt.targets) != 1
            or not isinstance(stmt.targets[0], ast.Name)
        ):
            continue

        name = stmt.targets[0].id
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
            fail(
                "HARD GATE 11 duplicate field declaration",
                f"{model_name}.{name}",
            )
        fields_seen[name] = value.func.attr

        if (
            not identifier_pattern.fullmatch(name)
            or len(name.encode("utf-8")) > PG_IDENTIFIER_LIMIT
        ):
            fail(
                "HARD GATE 11 field identifier",
                f"{model_name}.{name}",
            )

        indexed = any(
            kw.arg == "index"
            and isinstance(kw.value, ast.Constant)
            and bool(kw.value.value)
            for kw in value.keywords
        )
        if indexed:
            projected = f"{table}_{name}_index"
            if len(projected.encode("utf-8")) > PG_IDENTIFIER_LIMIT:
                fail(
                    "HARD GATE 11 predicted index identifier length",
                    projected,
                )

        if value.func.attr in ("Many2one", "One2many", "Many2many"):
            comodel = const_str(value.args[0]) if value.args else None
            if comodel and (
                comodel in SOFT_MODULE_MODELS
                or any(
                    comodel.startswith(prefix)
                    for prefix in SOFT_MODEL_PREFIXES
                )
                or comodel not in ALLOWED_RELATIONAL_MODELS
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
                    or len(identifier.encode("utf-8"))
                    > PG_IDENTIFIER_LIMIT
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

for path, cls, inherited_model in extension_classes:
    for stmt in cls.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and field_call(stmt.value)
        ):
            name = stmt.targets[0].id
            extension_field_names.append(
                (inherited_model, name)
            )
            if (
                not identifier_pattern.fullmatch(name)
                or len(name.encode("utf-8")) > PG_IDENTIFIER_LIMIT
            ):
                fail(
                    "HARD GATE 11 extension field identifier",
                    f"{inherited_model}.{name}",
                )

if not any(
    label.startswith("HARD GATE 11 field")
    or label.startswith("HARD GATE 11 predicted index")
    or label.startswith("HARD GATE 11 duplicate field")
    or label.startswith("HARD GATE 11 extension field")
    for label, _ in failures
):
    ok(
        "HARD GATE 11 safe ORM field/index identifiers "
        f"({sum(len(v) for v in model_fields.values())} persistent fields; "
        f"{len(extension_field_names)} extension fields)"
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
    ok(
        f"HARD GATE 11 safe constraint identifiers "
        f"({len(constraints)} constraints)"
    )


# ---------------------------------------------------------------------------
# XML / Odoo 19 views / object method cross-reference / XML IDs
# ---------------------------------------------------------------------------
xml_files = sorted(ROOT.rglob("*.xml"))
xml_roots = {}
for path in xml_files:
    try:
        xml_roots[path] = ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail(
            "XML syntax",
            f"{path.relative_to(ROOT)}: {exc}",
        )

if len(xml_roots) == len(xml_files):
    ok(f"XML syntax ({len(xml_files)} files)")

view_text = "\n".join(
    read(path)
    for path in sorted((ROOT / "views").glob("*.xml"))
)

if "<tree" in view_text or "</tree>" in view_text:
    fail("Odoo 19 list syntax", "legacy tree tag found")
else:
    ok("Odoo 19 operational lists use <list>")

if "attrs=" in view_text or re.search(r"\sstates\s*=", view_text):
    fail(
        "Odoo 19 direct view modifiers",
        "legacy attrs/states found",
    )
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
    fail(
        "Odoo 19 search <group> contract",
        "; ".join(bad_search_groups),
    )
else:
    ok("Odoo 19 search <group> elements have no attributes")

view_blocks = re.findall(
    r'<record[^>]*model="ir\.ui\.view".*?</record>',
    view_text,
    flags=re.S,
)
for model in sorted(EXPECTED_MODELS):
    blocks = [
        block
        for block in view_blocks
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
    "One2many Row Button": 'name="evidence_ids"',
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

available_methods = method_names | INHERITED_OBJECT_METHODS
missing_methods = set()
for path, xml_root in xml_roots.items():
    for button in xml_root.iter("button"):
        if button.attrib.get("type") != "object":
            continue
        method = button.attrib.get("name")
        if method and method not in available_methods:
            missing_methods.add(
                f"{path.relative_to(ROOT)}:{method}"
            )

if missing_methods:
    fail(
        "Object button → Python method cross-reference",
        ", ".join(sorted(missing_methods)),
    )
else:
    ok("Object button → Python/inherited method cross-reference")

xml_ids = {}
duplicates = []
for path, xml_root in xml_roots.items():
    for node in xml_root.iter():
        xml_id = node.attrib.get("id")
        if not xml_id or "." in xml_id:
            continue
        if xml_id in xml_ids:
            duplicates.append(
                f"{xml_id}: {xml_ids[xml_id]} / "
                f"{path.relative_to(ROOT)}"
            )
        else:
            xml_ids[xml_id] = str(path.relative_to(ROOT))

if duplicates:
    fail(
        "HARD GATE 11 unique local XML external IDs",
        "; ".join(duplicates),
    )
else:
    ok(
        "HARD GATE 11 unique local XML external IDs "
        f"({len(xml_ids)} IDs)"
    )


# ---------------------------------------------------------------------------
# Security / least privilege
# ---------------------------------------------------------------------------
acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(
        csv.DictReader(read(acl_path).splitlines())
    )
except Exception as exc:
    acl_rows = []
    fail("ACL CSV parse", str(exc))
else:
    ok(f"ACL CSV parse ({len(acl_rows)} rows)")

if "base.group_user" in read(acl_path):
    fail(
        "HARD GATE 10 least privilege",
        "base.group_user appears in custom PnP ACL",
    )
else:
    ok("HARD GATE 10 no broad base.group_user PnP CRUD")

security_text = read(
    ROOT / "security" / "onehr_pnp_security.xml"
)
rules_text = read(
    ROOT / "security" / "onehr_pnp_rules.xml"
)

for group in (
    "group_onehr_pnp_reader",
    "group_onehr_pnp_owner",
    "group_onehr_pnp_compliance",
    "group_onehr_pnp_admin",
):
    if group in security_text:
        ok(f"Security role present: {group}")
    else:
        fail(f"Security role present: {group}")

if 'model="res.groups.privilege"' in security_text:
    ok("Odoo 19 res.groups.privilege pattern used")
else:
    fail("Odoo 19 res.groups.privilege pattern")

if rules_text.count(
    '<field name="global" eval="True"/>'
) >= 3:
    ok("Global company isolation rules on all three PnP models")
else:
    fail("Global company isolation rule coverage")

for token, label in (
    (
        "ack_ids.employee_user_id",
        "Reader Policy assignment boundary",
    ),
    (
        "[('owner_user_id', '=', user.id)]",
        "Policy Owner own-policy boundary",
    ),
    (
        "[('employee_user_id', '=', user.id)]",
        "Reader own ack/evidence boundary",
    ),
):
    if token in rules_text:
        ok(label)
    else:
        fail(label)

if "_ACTION_CONTEXT" in models_source:
    ok("Server-side lifecycle/evidence action guards present")
else:
    fail("Server-side workflow guards")

if models_source.count(
    "@api.ondelete(at_uninstall=False)"
) >= 3:
    ok("Historical deletion guards cover all three PnP models")
else:
    fail("Historical deletion guard coverage")


# ---------------------------------------------------------------------------
# Product / integration contract preservation
# ---------------------------------------------------------------------------
functional_tokens = (
    ("onehr.mixin.approvable", "Workflow Approval source ownership"),
    (
        "action_submit_policy_approval",
        "Draft/Rejected → Approval",
    ),
    ("_on_approval_finalized", "Approval callback"),
    ("action_publish", "Approved → Published"),
    ("onehr_mark_approval_executed", "approved execution evidence"),
    ("action_start_review", "Published → Review"),
    (
        "action_complete_review_no_change",
        "Review renewal without content rewrite",
    ),
    ("action_create_revision", "controlled version successor"),
    ("action_archive", "Published/Review → Archived"),
    ("target_department_ids", "target department/unit audience"),
    ("target_job_ids", "target job/role audience"),
    ("target_employee_ids", "specific employee audience"),
    ("branch_scope_key", "soft branch/site extension key"),
    ("action_acknowledge", "employee acknowledgement"),
    ("evidence_scope", "employee/unit/policy evidence scope"),
    ("attachment_ids", "file/photo evidence"),
    ("reference_url", "URL evidence"),
    ("document_version_id", "controlled Document evidence"),
    ("action_verify", "Compliance evidence verification"),
    ("_cron_policy_governance", "review/reminder scheduler"),
    ("archive_document_version_id", "Document archive snapshot"),
    ("onehr_policy_portal_payload", "Portal policy service"),
    ("onehr_pnp_submit_evidence", "Portal/API evidence service"),
    ("onehr_pnp_ack_status", "API acknowledgement status"),
    (
        "onehr_pnp_compliance_snapshot",
        "Analytics compliance service",
    ),
    ("related_sop_references", "soft SOP reference"),
)
for token, label in functional_tokens:
    if token in models_source:
        ok(f"HARD GATE 3/15 functional contract — {label}")
    else:
        fail(f"HARD GATE 3/15 functional contract — {label}")

if 'self.env["onehr.sop"]' in models_source and (
    'fields.Many2one("onehr.sop"' not in models_source
    and 'fields.One2many("onehr.sop"' not in models_source
    and 'fields.Many2many("onehr.sop"' not in models_source
):
    ok("OneHR SOP integration is runtime-soft, not static ORM ownership")
else:
    fail("OneHR SOP soft ownership boundary")

report_text = read(ROOT / "report" / "pnp_reports.xml")
for token, label in (
    ("action_report_onehr_policy", "Policy QWeb PDF"),
    (
        "action_report_onehr_policy_compliance",
        "Policy Compliance Summary QWeb PDF",
    ),
    (
        "action_report_onehr_policy_review_register",
        "Review/Expiry Register QWeb PDF",
    ),
    (
        "action_report_onehr_policy_evidence_register",
        "Evidence Coverage Register QWeb PDF",
    ),
):
    if token in report_text:
        ok(label)
    else:
        fail(label)

if (
    "onehr_base.menu_onehr_root"
    in read(ROOT / "views" / "menus.xml")
):
    ok("Integrated OneHR root navigation without sibling source edit")
else:
    fail("OneHR root navigation integration")



# ---------------------------------------------------------------------------
# Odoo 19 native Users / Access Rights dynamic-category XML safety
# ---------------------------------------------------------------------------
def _scan_onehr_privilege_categories(project_root):
    """Inspect OneHR privilege-bearing categories exactly as Odoo stores their names.

    ElementTree decodes XML entities (for example &amp; -> &). Odoo 19's native
    res_user_group_ids widget later interpolates category.name into generated XML,
    so decoded XML-sensitive characters in a category label are a browser-render
    compatibility defect even when the source XML file itself is well formed.
    """
    categories = {}
    privilege_refs = set()
    parse_errors = []
    for addon_dir in sorted(project_root.glob("onehr_*")):
        if not addon_dir.is_dir():
            continue
        module = addon_dir.name
        security_dir = addon_dir / "security"
        if not security_dir.is_dir():
            continue
        for xml_path in sorted(security_dir.glob("*.xml")):
            try:
                root = ET.parse(xml_path).getroot()
            except ET.ParseError as exc:
                parse_errors.append((xml_path, str(exc)))
                continue
            for record in root.findall(".//record"):
                model = record.attrib.get("model")
                record_id = record.attrib.get("id")
                if model == "ir.module.category" and record_id:
                    name_node = next(
                        (field for field in record.findall("field") if field.attrib.get("name") == "name"),
                        None,
                    )
                    categories[(module, record_id)] = (
                        (name_node.text or "") if name_node is not None else "",
                        xml_path,
                    )
                elif model == "res.groups.privilege":
                    category_node = next(
                        (field for field in record.findall("field") if field.attrib.get("name") == "category_id"),
                        None,
                    )
                    if category_node is None:
                        continue
                    ref = category_node.attrib.get("ref")
                    if not ref:
                        continue
                    if "." in ref:
                        ref_module, ref_id = ref.split(".", 1)
                    else:
                        ref_module, ref_id = module, ref
                    privilege_refs.add((ref_module, ref_id))
    referenced = {
        key: categories[key]
        for key in sorted(privilege_refs)
        if key in categories
    }
    unsafe = []
    for key, (name, xml_path) in referenced.items():
        bad = sorted({char for char in name if char in '&<>"\''})
        if bad:
            unsafe.append((key, name, ''.join(bad), xml_path))
    return referenced, unsafe, parse_errors

_suite_categories, _suite_unsafe_categories, _suite_parse_errors = _scan_onehr_privilege_categories(ROOT.parent)
if _suite_parse_errors:
    fail(
        "Odoo 19 User Access Rights privilege-category XML source scan",
        str([(str(path), err) for path, err in _suite_parse_errors[:5]]),
    )
else:
    ok("Odoo 19 User Access Rights privilege-category XML source scan")

if _suite_unsafe_categories:
    fail(
        "Odoo 19 dynamic User Access Rights category-name safety",
        str([
            (f"{module}.{record_id}", name, chars, str(path))
            for ((module, record_id), name, chars, path) in _suite_unsafe_categories
        ]),
    )
else:
    ok(
        "Odoo 19 dynamic User Access Rights category-name safety "
        f"({len(_suite_categories)} privilege-bearing OneHR categories scanned)"
    )


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
    ok(
        f"Runtime test inventory exactly "
        f"{EXPECTED_TEST_METHODS} methods"
    )
else:
    fail(
        "Runtime test inventory",
        f"expected={EXPECTED_TEST_METHODS}, "
        f"found={len(test_methods)}",
    )

if all(
    "@tagged" in read(path)
    for path in sorted((ROOT / "tests").glob("test_*.py"))
):
    ok("Runtime test suites are post-install tagged")
else:
    fail("Runtime test suite tags")


# ---------------------------------------------------------------------------
# Documentation / Guardrail evidence
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
    "ODOO19_USER_ACCESS_RIGHTS_COMPATIBILITY_REPAIR.md",
    "CROSS_SUITE_PRIVILEGE_CATEGORY_AUDIT.md",
    "PRESERVATION_DIFF_19_0_1_0_0_TO_19_0_1_0_1.txt",
    "UPSTREAM_CONTRACT_AND_SCOPE_AUDIT.md",
}
missing_docs = [
    name
    for name in sorted(mandatory_docs)
    if not (ROOT / "docs" / name).is_file()
]
if missing_docs:
    fail(
        "Mandatory Enterprise documentation",
        f"missing={missing_docs}",
    )
else:
    ok("Mandatory Enterprise documentation set")

guardrail = read(
    ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md"
)
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

identifier_doc = read(
    ROOT / "docs" / "DATABASE_IDENTIFIER_ORM_NAMING_SAFETY.md"
)
if (
    "63 UTF-8 bytes" in identifier_doc
    and "onehr_policy_evidence" in identifier_doc
):
    ok("HARD GATE 11 dedicated identifier-safety evidence")
else:
    fail("HARD GATE 11 identifier-safety evidence")

registry_doc = read(
    ROOT / "docs" / "MODEL_REGISTRY_ALIGNMENT.md"
)
if (
    "REGISTRY_ED_CLASSIFICATION: "
    "PENDING_EXACT_REGISTRY_ROW_VERIFICATION"
    in registry_doc
):
    warn(
        "Exact Master Model Registry ED rows remain pending; "
        "classifications were not invented"
    )
else:
    fail("Registry ED pending marker")

if "<gantt" not in view_text:
    warn("Native Gantt intentionally not fabricated on Odoo 19 CE")
else:
    fail("Odoo CE UI ownership", "unexpected Gantt view found")


# ---------------------------------------------------------------------------
# Final source-stage status
# ---------------------------------------------------------------------------
print()
print(f"SOURCE_FILES_PYTHON={len(python_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print(f"CUSTOM_PERSISTENT_MODELS={len(declared_models)}")
print(
    "ORM_FIELD_COUNT="
    f"{sum(len(v) for v in model_fields.values())}"
)
print(f"SETTINGS_EXTENSION_FIELDS={len(extension_field_names)}")
print(f"M2M_RELATION_COUNT={len(m2m_relations)}")
print(f"LOCAL_XML_ID_COUNT={len(xml_ids)}")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={len(test_methods)}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")

if failures:
    sys.exit(1)

print("ONEHR_PNP_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print(
    "REGISTRY_ED_CLASSIFICATION="
    "PENDING_EXACT_REGISTRY_ROW_VERIFICATION"
)
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_PNP_MOVE_FORWARD_READY=NO")

