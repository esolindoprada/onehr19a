from __future__ import annotations

import ast
import csv
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT.parent
errors: list[str] = []

EXPECTED_DEPS = [
    "onehr_corehr",
    "onehr_security",
    "onehr_workflow_approval",
    "hr_recruitment",
]
EXPECTED_CUSTOM_MODELS = {
    "onehr.recruitment.requisition",
    "onehr.interview.template",
    "onehr.interview.session",
    "onehr.interview.score",
    "onehr.offer",
    "onehr.preboarding",
    "onehr.recruitment.source.metric",
}
EXPECTED_NATIVE_INHERITS = {
    "hr.applicant",
    "hr.recruitment.stage",
    "hr.job",
    "hr.talent.pool",
}
FORBIDDEN_PARALLEL_MODELS = {
    "onehr.job.opening",
    "onehr.applicant",
    "onehr.recruit.stage",
    "onehr.onboard.template",
    "onehr.talent.pool",
    "onehr_recruitment.onehr_recruitment",
}


def passed(message: str) -> None:
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


# HARD GATE 0 — identity / manifest / dependency contract.
try:
    manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Recruitment":
    passed("HARD_GATE_0 project/addon identity")
else:
    failed(f"unexpected manifest name: {manifest.get('name')!r}")

if manifest.get("version") == "19.0.1.0.3":
    passed("Odoo 19 manifest version")
else:
    failed(f"unexpected manifest version: {manifest.get('version')!r}")

if manifest.get("depends") == EXPECTED_DEPS:
    passed("hard dependencies exactly match Architecture v2")
else:
    failed(f"hard dependencies differ: {manifest.get('depends')!r}")

for forbidden_dep in (
    "onehr_document",
    "onehr_integrations_api",
    "onehr_multicompany_branch",
    "onehr_assignment",
    "onehr_employment_contract",
    "onehr_attendance",
    "onehr_timeoff",
):
    if forbidden_dep in manifest.get("depends", []):
        failed(f"forbidden/non-authoritative hard dependency: {forbidden_dep}")

for relpath in manifest.get("data", []):
    if not (ROOT / relpath).exists():
        failed(f"manifest data file missing: {relpath}")
if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

# Guardrail integrity.  Validate the actual guardrail/checksum pair present in
# the containing workspace/package.  This deliberately avoids hard-coding a
# checksum from a text export because newline normalization can change bytes.
guardrail = PACKAGE_ROOT / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md"
guardrail_sha_file = PACKAGE_ROOT / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.sha256"
if not guardrail.exists():
    failed("authoritative root Guardrail missing from containing workspace/package")
elif not guardrail_sha_file.exists():
    failed("authoritative root Guardrail checksum file missing")
else:
    declared_match = re.search(
        r"(?i)\b([0-9a-f]{64})\b",
        guardrail_sha_file.read_text(encoding="utf-8", errors="replace"),
    )
    if not declared_match:
        failed("root Guardrail checksum file contains no SHA-256 value")
    else:
        declared_sha = declared_match.group(1).upper()
        actual_sha = hashlib.sha256(guardrail.read_bytes()).hexdigest().upper()
        if actual_sha == declared_sha:
            passed("authoritative root Guardrail/checksum pair integrity")
        else:
            failed(
                "root Guardrail/checksum pair mismatch: "
                f"declared={declared_sha} actual={actual_sha}"
            )

# Python / XML syntax and Odoo 17+ view syntax guard.
python_paths = sorted(ROOT.rglob("*.py"))
for path in python_paths:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed("all Python sources compile")

xml_paths = sorted(ROOT.rglob("*.xml"))
for path in xml_paths:
    try:
        ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
    text = path.read_text(encoding="utf-8")
    if re.search(r"\battrs\s*=", text):
        failed(f"deprecated attrs= view syntax: {path.relative_to(ROOT)}")
    if re.search(r"\bstates\s*=", text):
        failed(f"deprecated states= view syntax: {path.relative_to(ROOT)}")
if not any(item.startswith("XML parse") or "deprecated attrs=" in item or "deprecated states=" in item for item in errors):
    passed("all XML parses and avoids deprecated attrs/states syntax")


# Odoo 19 fields.Properties definition contract.
# `definition` must be exactly "<many2one_field>.<properties_definition_field>".
# Odoo 19 rejects longer traversal paths at model-class setup time.
properties_definition_calls = 0
for path in sorted((ROOT / "models").glob("*.py")):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Properties"
        ):
            continue

        properties_definition_calls += 1
        definition_kw = next(
            (kw for kw in node.keywords if kw.arg == "definition"),
            None,
        )
        if not definition_kw:
            failed(
                f"Odoo 19 fields.Properties missing definition= in "
                f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', '?')}"
            )
            continue

        try:
            definition_value = ast.literal_eval(definition_kw.value)
        except Exception:
            definition_value = None

        if not isinstance(definition_value, str) or definition_value.count(".") != 1:
            failed(
                f"Odoo 19 fields.Properties definition must contain exactly one dot "
                f"in {path.relative_to(ROOT)}:{getattr(node, 'lineno', '?')}: "
                f"{definition_value!r}"
            )

if properties_definition_calls == 1 and not any(
    "fields.Properties" in item for item in errors
):
    passed("Odoo 19 fields.Properties definitions use exactly one relation hop")
elif properties_definition_calls != 1:
    failed(
        f"expected exactly one Recruitment fields.Properties field, "
        f"found {properties_definition_calls}"
    )

interview_source = (ROOT / "models/interview.py").read_text(encoding="utf-8")
if 'definition="template_id.scorecard_definition"' in interview_source:
    passed("Interview scorecard uses template_id.scorecard_definition container contract")
else:
    failed("Interview scorecard Properties definition contract is not Odoo 19 compatible")


# Odoo 19 Preboarding search-domain regression.
# The display-only related counter `checklist_pending_task_count` is intentionally
# non-stored/non-searchable. Search must follow the authoritative checklist task
# relation and stored task state instead of filtering the computed counter.
preboarding_view_path = ROOT / "views/preboarding_views.xml"
try:
    preboarding_tree = ET.parse(preboarding_view_path)
except Exception as exc:
    preboarding_tree = None
    failed(f"Preboarding search-domain regression XML parse: {exc}")

if preboarding_tree is not None:
    pending_filters = [
        node
        for node in preboarding_tree.getroot().iter("filter")
        if node.attrib.get("name") == "pending_tasks"
    ]
    expected_pending_domain = "[('checklist_instance_id.task_ids.state', '=', 'pending')]"
    if len(pending_filters) != 1:
        failed(
            f"expected exactly one Preboarding pending_tasks filter, found {len(pending_filters)}"
        )
    elif pending_filters[0].attrib.get("domain") == expected_pending_domain:
        passed("Preboarding pending-task search uses searchable checklist task-state relation")
    else:
        failed(
            "Preboarding pending_tasks filter must use searchable relation domain "
            f"{expected_pending_domain!r}; found {pending_filters[0].attrib.get('domain')!r}"
        )

    bad_counter_domains = []
    for node in preboarding_tree.getroot().iter():
        domain = node.attrib.get("domain", "")
        if "checklist_pending_task_count" in domain:
            bad_counter_domains.append(
                f"{node.tag}:{node.attrib.get('name', '<unnamed>')}={domain}"
            )
    if bad_counter_domains:
        for item in bad_counter_domains:
            failed(
                "Preboarding search/domain may not filter non-searchable "
                f"checklist_pending_task_count: {item}"
            )
    else:
        passed("Preboarding domains do not filter non-searchable checklist_pending_task_count")


# Odoo 19 generic Recruitment search-domain compatibility audit.
#
# Odoo validates search-view domains at module load. A target-local computed or
# related field may participate as a domain leaf only when it is stored or has
# an explicit search method. The audit below inspects every domain attribute in
# Recruitment view XML and resolves every locally-owned field path that can be
# proven from this addon source. This catches the defect class globally instead
# of hard-coding one filter at a time.
SEARCH_DOMAIN_OPERATORS = {
    "=", "!=", ">", ">=", "<", "<=", "in", "not in",
    "like", "not like", "ilike", "not ilike", "=like", "=ilike",
    "child_of", "parent_of", "any", "not any",
}


def _keyword_literal(call_node: ast.Call, keyword: str, default=None):
    value_node = next(
        (kw.value for kw in call_node.keywords if kw.arg == keyword),
        None,
    )
    if value_node is None:
        return default
    try:
        return ast.literal_eval(value_node)
    except Exception:
        return "<dynamic>"


def _field_call_metadata(call_node: ast.Call):
    if not (
        isinstance(call_node.func, ast.Attribute)
        and isinstance(call_node.func.value, ast.Name)
        and call_node.func.value.id == "fields"
    ):
        return None

    field_type = call_node.func.attr
    comodel = None
    if field_type in {"Many2one", "One2many", "Many2many"} and call_node.args:
        try:
            comodel = ast.literal_eval(call_node.args[0])
        except Exception:
            comodel = None

    return {
        "type": field_type,
        "compute": _keyword_literal(call_node, "compute"),
        "related": _keyword_literal(call_node, "related"),
        "store": _keyword_literal(call_node, "store", False),
        "search": _keyword_literal(call_node, "search"),
        "comodel": comodel,
    }


def _domain_field_paths(domain_text: str):
    """Return field paths from domain tuple leaves without evaluating the domain."""
    try:
        expr = ast.parse(domain_text, mode="eval")
    except SyntaxError:
        return []

    field_paths = []
    for node in ast.walk(expr):
        if not isinstance(node, (ast.Tuple, ast.List)) or len(node.elts) < 2:
            continue
        first, second = node.elts[0], node.elts[1]
        if not (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and isinstance(second, ast.Constant)
            and isinstance(second.value, str)
            and second.value in SEARCH_DOMAIN_OPERATORS
        ):
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", first.value):
            field_paths.append(first.value)
    return field_paths


def _source_field_is_searchable(metadata: dict) -> bool:
    if metadata.get("compute") or metadata.get("related"):
        return metadata.get("store") is True or bool(metadata.get("search"))
    return True


source_field_registry: dict[str, dict[str, dict]] = {}
for model_path in sorted((ROOT / "models").glob("*.py")):
    try:
        model_tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
    except SyntaxError:
        continue

    for class_node in [node for node in model_tree.body if isinstance(node, ast.ClassDef)]:
        model_name = literal_assign(class_node, "_name")
        inherit_name = literal_assign(class_node, "_inherit")
        if not isinstance(model_name, str):
            model_name = inherit_name if isinstance(inherit_name, str) else None
        if not model_name:
            continue

        fields_for_model = source_field_registry.setdefault(model_name, {})
        for statement in class_node.body:
            if not (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, ast.Call)
            ):
                continue
            metadata = _field_call_metadata(statement.value)
            if metadata:
                fields_for_model[statement.targets[0].id] = metadata


def _resolve_local_domain_path(view_model: str, field_path: str):
    current_model = view_model
    segments = field_path.split(".")
    for index, segment in enumerate(segments):
        metadata = source_field_registry.get(current_model, {}).get(segment)
        if metadata is None:
            return "external", current_model, segment

        if index == len(segments) - 1:
            return (
                "searchable" if _source_field_is_searchable(metadata) else "unsearchable",
                current_model,
                segment,
            )

        comodel = metadata.get("comodel")
        if not comodel:
            return "invalid_path", current_model, segment
        current_model = comodel

    return "external", current_model, ""


search_domain_attribute_count = 0
search_domain_leaf_count = 0
resolved_local_leaf_count = 0
external_domain_paths = []

for view_path in sorted((ROOT / "views").glob("*.xml")):
    try:
        view_tree = ET.parse(view_path)
    except Exception:
        continue

    for record in view_tree.getroot().findall(".//record[@model='ir.ui.view']"):
        view_model_node = record.find("./field[@name='model']")
        arch_node = record.find("./field[@name='arch']")
        if view_model_node is None or arch_node is None or not view_model_node.text:
            continue
        view_model = view_model_node.text.strip()

        for node in arch_node.iter():
            domain_text = node.attrib.get("domain")
            if not domain_text:
                continue

            search_domain_attribute_count += 1
            field_paths = _domain_field_paths(domain_text)
            search_domain_leaf_count += len(field_paths)

            for field_path in field_paths:
                status, resolved_model, resolved_field = _resolve_local_domain_path(
                    view_model, field_path
                )
                if status == "unsearchable":
                    failed(
                        "Odoo 19 search domain uses target-local non-searchable field: "
                        f"{view_path.relative_to(ROOT)} / view_model={view_model} / "
                        f"domain={domain_text!r} / path={field_path!r} / "
                        f"resolved={resolved_model}.{resolved_field}"
                    )
                elif status == "invalid_path":
                    failed(
                        "Recruitment search domain traverses a non-relational target-local field: "
                        f"{view_path.relative_to(ROOT)} / view_model={view_model} / "
                        f"domain={domain_text!r} / path={field_path!r}"
                    )
                elif status == "searchable":
                    resolved_local_leaf_count += 1
                else:
                    # Parent/native or sibling-owned fields cannot be fully proven by this
                    # addon-only static gate. They remain subject to Odoo runtime validation.
                    external_domain_paths.append(
                        f"{view_model}:{field_path}"
                    )

if not any("search domain uses target-local non-searchable field" in item for item in errors):
    passed(
        "generic Odoo 19 Recruitment search-domain audit finds no "
        "target-local non-searchable domain leaves"
    )

if search_domain_attribute_count:
    passed(
        "generic Recruitment search-domain audit scanned "
        f"{search_domain_attribute_count} domain attributes / "
        f"{search_domain_leaf_count} domain leaves"
    )
else:
    failed("generic Recruitment search-domain audit found no domain attributes")

native_source = (ROOT / "models/native_recruitment.py").read_text(encoding="utf-8")
native_view_source = (ROOT / "views/native_recruitment_views.xml").read_text(encoding="utf-8")

# Semantics-preserving accepted-offer filter: "latest offer" remains the
# business field; it is made searchable rather than replacing the filter with
# "any accepted offer", which would change historical meaning.
applicant_field_meta = source_field_registry.get("hr.applicant", {}).get(
    "onehr_latest_offer_state", {}
)
if (
    applicant_field_meta.get("compute") == "_compute_onehr_recruitment_counts"
    and applicant_field_meta.get("store") is True
    and applicant_field_meta.get("search") in (None, False)
):
    passed("Latest Offer state is stored/searchable while preserving its compute semantics")
else:
    failed(
        "onehr_latest_offer_state must remain computed and become stored/searchable"
    )

if '"onehr_offer_ids.state"' in native_source:
    passed("Latest Offer stored compute invalidates when offer lifecycle state changes")
else:
    failed("Latest Offer stored compute must depend on onehr_offer_ids.state")

if (
    "latest = applicant.onehr_offer_ids.sorted" in native_source
    and 'applicant.onehr_latest_offer_state = latest.state if latest else "none"' in native_source
):
    passed("Latest Offer business semantics still select the most recently created offer")
else:
    failed("Latest Offer selection semantics changed or cannot be proven")

accepted_offer_domain = "[('onehr_latest_offer_state', '=', 'accepted')]"
if native_view_source.count(accepted_offer_domain) == 1:
    passed("Applicant Offer Accepted filter preserves latest-offer semantics")
else:
    failed("Applicant Offer Accepted filter no longer has exact latest-offer domain")

expected_open_requisition_domain = (
    "[('onehr_requisition_ids.state', 'in', ('approved', 'recruiting'))]"
)
if native_view_source.count(expected_open_requisition_domain) == 1:
    passed("Job Open Requisitions filter uses searchable requisition lifecycle relation")
else:
    failed(
        "Job Open Requisitions filter must use searchable requisition lifecycle relation"
    )

if "onehr_open_requisition_count" in "\n".join(
    node.attrib.get("domain", "")
    for path in sorted((ROOT / "views").glob("*.xml"))
    for node in ET.parse(path).getroot().iter()
):
    failed("Recruitment XML domains still filter non-searchable onehr_open_requisition_count")
else:
    passed("Recruitment XML domains do not filter onehr_open_requisition_count")



# HARD GATE 4 — exact Registry rows / native-first ownership.
custom_models: set[str] = set()
native_inherits: set[str] = set()
all_declared_names: set[str] = set()
for path in sorted((ROOT / "models").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for class_node in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        model_name = literal_assign(class_node, "_name")
        inherit = literal_assign(class_node, "_inherit")
        if isinstance(model_name, str):
            custom_models.add(model_name)
            all_declared_names.add(model_name)
        if model_name is None and isinstance(inherit, str):
            native_inherits.add(inherit)
        elif model_name is None and isinstance(inherit, (list, tuple)):
            native_inherits.update(item for item in inherit if isinstance(item, str))

if custom_models == EXPECTED_CUSTOM_MODELS:
    passed("exact seven OneHR-owned persistent Registry models")
else:
    failed(f"custom model set mismatch: {sorted(custom_models)}")

if native_inherits == EXPECTED_NATIVE_INHERITS:
    passed("exact four Odoo-native recruitment Registry extensions")
else:
    failed(f"native inherit set mismatch: {sorted(native_inherits)}")

if not (all_declared_names & FORBIDDEN_PARALLEL_MODELS):
    passed("no prohibited parallel canonical recruitment model")
else:
    failed(f"forbidden parallel model(s): {sorted(all_declared_names & FORBIDDEN_PARALLEL_MODELS)}")

# Security / unsafe execution checks.
model_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "models").glob("*.py")))
if ".sudo()" not in model_text and ".sudo(" not in model_text:
    passed("no sudo business-security bypass in recruitment models")
else:
    failed("sudo found in recruitment business model source")

if not re.search(r"\bsafe_eval\b|(?<![\w.])eval\s*\(", model_text):
    passed("no executable eval/safe_eval recruitment business logic")
else:
    failed("eval/safe_eval found in recruitment business model source")

if "def unlink(" not in model_text:
    passed("no business unlink override; uninstall-safe ondelete pattern used")
else:
    failed("business unlink override found")

ondelete_count = model_text.count("@api.ondelete(at_uninstall=False)")
if ondelete_count == 7:
    passed("all seven governed custom models have uninstall-safe ondelete protection")
else:
    failed(f"expected 7 uninstall-safe ondelete protections, found {ondelete_count}")

# Explicit server authority on native employee conversion.
preboarding_text = (ROOT / "models/preboarding.py").read_text(encoding="utf-8")
ensure_fragment = preboarding_text[preboarding_text.find("def _ensure_employee"):preboarding_text.find("def _find_hire_checklist_template")]
if "require_recruitment_manager(self)" in ensure_fragment and "create_employee_from_applicant()" in ensure_fragment:
    passed("native applicant-to-employee conversion is explicitly Recruitment Manager-controlled")
else:
    failed("employee conversion authority/native path contract missing")

# ACL inventory.
acl_path = ROOT / "security/ir.model.access.csv"
try:
    with acl_path.open(encoding="utf-8", newline="") as handle:
        acl_rows = list(csv.DictReader(handle))
except Exception as exc:
    acl_rows = []
    failed(f"ACL CSV parse: {exc}")

if len(acl_rows) == 21:
    passed("exact 21 custom-model ACL rows")
else:
    failed(f"expected 21 ACL rows, found {len(acl_rows)}")

if not any(row.get("group_id:id") == "base.group_user" for row in acl_rows):
    passed("no broad base.group_user custom-model ACL")
else:
    failed("base.group_user custom-model ACL found")

if not any(row.get("perm_unlink") == "1" for row in acl_rows):
    passed("no ACL grants unlink on governed recruitment evidence")
else:
    failed("ACL unlink grant found")

rules_text = (ROOT / "security/onehr_recruitment_rules.xml").read_text(encoding="utf-8")
for model_fragment in (
    "model_onehr_recruitment_requisition",
    "model_onehr_interview_template",
    "model_onehr_interview_session",
    "model_onehr_interview_score",
    "model_onehr_offer",
    "model_onehr_preboarding",
    "model_onehr_recruitment_source_metric",
):
    if model_fragment not in rules_text:
        failed(f"missing record-rule coverage: {model_fragment}")
if not any(item.startswith("missing record-rule coverage") for item in errors):
    passed("record-rule coverage for every custom persistent model")

# HARD GATE 8 / 9 — dedicated list/form/search for every custom persistent model.
view_types_by_model: dict[str, set[str]] = {}
for path in sorted((ROOT / "views").glob("*.xml")):
    tree = ET.parse(path)
    for record in tree.findall(".//record[@model='ir.ui.view']"):
        model_field = record.find("field[@name='model']")
        arch_field = record.find("field[@name='arch']")
        if model_field is None or arch_field is None or not (model_field.text or "").strip():
            continue
        model = (model_field.text or "").strip()
        types = view_types_by_model.setdefault(model, set())
        for child in list(arch_field):
            tag = child.tag.split("}")[-1]
            if tag in {"list", "form", "search", "calendar", "pivot", "graph", "kanban"}:
                types.add(tag)

for model in sorted(EXPECTED_CUSTOM_MODELS):
    missing = {"list", "form", "search"} - view_types_by_model.get(model, set())
    if missing:
        failed(f"{model} missing dedicated view type(s): {sorted(missing)}")
if not any("missing dedicated view type" in item for item in errors):
    passed("list/form/search view coverage for all seven custom persistent models")

views_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "views").glob("*.xml")))
ui_markers = {
    "statusbar": 'widget="statusbar"',
    "smart buttons": "oe_stat_button",
    "One2many/List row buttons": "<list" if "<button" in views_text else "__missing__",
    "calendar": "<calendar",
    "pivot": "<pivot",
    "graph": "<graph",
    "chatter": "<chatter",
}
for label, marker in ui_markers.items():
    if marker in views_text:
        passed(f"enterprise UI marker: {label}")
    else:
        failed(f"missing enterprise UI marker: {label}")

# Require a real button nested inside a list (One2many/list-row operation).
row_button = False
for path in sorted((ROOT / "views").glob("*.xml")):
    tree = ET.parse(path)
    for list_node in tree.findall(".//list"):
        if list_node.find(".//button") is not None:
            row_button = True
            break
    if row_button:
        break
if row_button:
    passed("business-meaningful One2many/list row button present")
else:
    failed("no One2many/list row button found")

# HARD GATE 14 / test inventory.
test_count = 0
tagged_test_files = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    test_count += sum(
        1 for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    )
    if "post_install" in text and "-at_install" in text and "onehr_recruitment" in text:
        tagged_test_files += 1
if test_count == 20:
    passed("exact 20 post-install test methods structurally present")
else:
    failed(f"expected 20 test methods, found {test_count}")

if tagged_test_files == 4:
    passed("all four test modules carry post-install OneHR Recruitment tags")
else:
    failed(f"expected 4 tagged test modules, found {tagged_test_files}")

# Governance docs / hard gate enumeration.
required_docs = {
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "INTEGRATION_CONTRACTS.md",
    "ONEHR_RECRUITMENT_IMPLEMENTATION_REPORT.md",
}
missing_docs = sorted(name for name in required_docs if not (ROOT / "docs" / name).exists())
if not missing_docs:
    passed("all mandatory governance/completeness documents present")
else:
    failed(f"missing governance documents: {missing_docs}")

guardrail_text = (ROOT / "docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").read_text(encoding="utf-8") if (ROOT / "docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").exists() else ""
for gate in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]:
    if f"HARD GATE {gate}" not in guardrail_text and not (gate == 0 and "HARD GATE 0" in guardrail_text):
        failed(f"addon Guardrail missing HARD GATE {gate}")
if "HARD GATE 11 — INTENTIONALLY UNDEFINED" in guardrail_text:
    passed("Hard Gate 11 intentionally undefined; not invented")
else:
    failed("Hard Gate 11 intentional-undefined marker missing")

for contract in (
    "CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER",
    "ARCHITECTURE_AUTHORITY: NONE",
    "SIMPLIFICATION_AUTHORITY: NONE",
    "DELETION_AUTHORITY: NONE",
    "MODEL_OWNERSHIP_CHANGE_AUTHORITY: NONE",
    "DEPENDENCY_CHANGE_AUTHORITY: NONE",
    "MAX_CODEX_ATTEMPTS_PER_TASK: 2",
    "MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1",
):
    if contract not in guardrail_text:
        failed(f"Guardrail Codex contract missing: {contract}")
if not any(item.startswith("Guardrail Codex contract missing") for item in errors):
    passed("bounded Codex role/retry contract present")

print()
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")
print("MASTER_MODEL_REGISTRY_TARGET_ROWS: 11")
print("CUSTOM_PERSISTENT_MODELS: 7")
print("ODOO_NATIVE_INHERIT_ROWS: 4")
print(f"ACL_ROWS: {len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS: {test_count}")
if errors:
    print("ONEHR_RECRUITMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
    print("ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO")
    sys.exit(1)

print("ONEHR_RECRUITMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO")
