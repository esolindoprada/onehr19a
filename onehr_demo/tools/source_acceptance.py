
#!/usr/bin/env python3
"""Whole-unit static acceptance for OneHR Demo MASTER PROMPT 02-05.

This source gate deliberately audits the complete frozen production contract, not only
the newly implemented MP05 handler. Runtime/Windows acceptance remains a separate gate.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

ADDON_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ADDON_ROOT / "docs" / "FROZEN_MP02_MP05_CONTRACT.json"

EXPECTED_MODELS = {
    "onehr.demo.scenario",
    "onehr.demo.run",
    "onehr.demo.generator",
    "onehr.demo.checkpoint",
    "onehr.demo.reference",
    "onehr.demo.log",
}
FIELD_CALLS = {
    "Char": "char",
    "Text": "text",
    "Integer": "integer",
    "Float": "float",
    "Boolean": "boolean",
    "Selection": "selection",
    "Many2one": "many2one",
    "One2many": "one2many",
    "Many2many": "many2many",
    "Date": "date",
    "Datetime": "datetime",
    "Binary": "binary",
    "Json": "json",
    "Html": "html",
    "Monetary": "monetary",
    "Properties": "properties",
    "Reference": "reference",
}
FRAMEWORK_NATIVE_FIELDS = {
    "hr.department": {
        "name": "char",
        "company_id": "many2one",
        "parent_id": "many2one",
        "active": "boolean",
    },
    "res.company": {
        "name": "char",
    },
}
REQUIRED_DOCS = {
    "README.md",
    "docs/FROZEN_MP02_MP04_CONTRACT.json",
    "docs/FROZEN_MP02_MP05_CONTRACT.json",
    "docs/PROJECT_IDENTITY_PREFLIGHT.md",
    "docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
    "docs/MP02_MP04_IMPLEMENTATION_EVIDENCE.md",
    "docs/MP02_MP05_IMPLEMENTATION_EVIDENCE.md",
    "docs/MP05_IMPLEMENTATION_EVIDENCE.md",
    "docs/MP05_FOUNDATION_DATASET_CONTRACT.md",
    "docs/WHOLE_PATH_RUNTIME_CONTRACT.md",
    "docs/DETERMINISTIC_SEQUENCE_POLICY.md",
    "docs/SECURITY_PRIVACY_MATRIX.md",
    "docs/UI_UX_MATRIX.md",
    "docs/RESET_CAPABILITY_MATRIX.md",
    "docs/SIDE_EFFECT_QUARANTINE_MATRIX.md",
    "docs/WINDOWS_RUNTIME_ACCEPTANCE.md",
    "docs/ENTERPRISE_COMPLETENESS_MATRIX.md",
    "docs/CONTROL_CENTER_NAVIGATION_CLOSURE.md",
}


class Result:
    def __init__(self):
        self.passes = []
        self.warns = []
        self.fails = []

    def ok(self, condition, message):
        (self.passes if condition else self.fails).append(message)

    def warn(self, message):
        self.warns.append(message)

    def render(self):
        lines = []
        lines += [f"PASS: {item}" for item in self.passes]
        lines += [f"WARN: {item}" for item in self.warns]
        lines += [f"FAIL: {item}" for item in self.fails]
        lines += [
            f"SOURCE_ACCEPTANCE_PASS_COUNT={len(self.passes)}",
            f"SOURCE_ACCEPTANCE_WARN_COUNT={len(self.warns)}",
            f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(self.fails)}",
            "ONEHR_DEMO_MP02_MP05_SOURCE_ACCEPTANCE=" + ("PASS" if not self.fails else "FAILED"),
            "MP02_MP05_STATIC_RESULT=" + ("PASS_FOR_WINDOWS_RUNTIME_TRIAL" if not self.fails else "BLOCKED"),
            "WINDOWS_RUNTIME_INSTALL=NOT_RUN",
            "MP05_RUNTIME_GENERATION=NOT_RUN",
            "MP05_MOVE_FORWARD_READY=NO",
            "ONEHR_DEMO_MOVE_FORWARD_READY=NO",
        ]
        return "\n".join(lines)


def normalized_text_sha(path: Path):
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def manifest(path: Path):
    return ast.literal_eval(path.read_text(encoding="utf-8-sig"))


def inventory(root: Path):
    """Static OneHR inventory with explicit OneHR abstract-mixin propagation."""
    models = defaultdict(lambda: {"fields": {}, "methods": set(), "selections": {}})
    owned = set()
    inheritance = defaultdict(set)

    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except SyntaxError:
            continue

        for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
            model_name = None
            inherits = []
            fields = {}
            methods = set()
            selections = {}

            for stmt in cls.body:
                if isinstance(stmt, ast.Assign) and stmt.targets and isinstance(stmt.targets[0], ast.Name):
                    key = stmt.targets[0].id
                    if key in {"_name", "_inherit"}:
                        try:
                            value = ast.literal_eval(stmt.value)
                        except Exception:
                            value = None
                        if key == "_name" and isinstance(value, str):
                            model_name = value
                        elif key == "_inherit":
                            if isinstance(value, str):
                                inherits = [value]
                            elif isinstance(value, (list, tuple)):
                                inherits = [item for item in value if isinstance(item, str)]

                    if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute):
                        ftype = FIELD_CALLS.get(stmt.value.func.attr)
                        if ftype:
                            fields[key] = ftype
                            if ftype == "selection" and stmt.value.args:
                                try:
                                    raw = ast.literal_eval(stmt.value.args[0])
                                except Exception:
                                    raw = None
                                if isinstance(raw, (list, tuple)):
                                    selections[key] = [
                                        item[0]
                                        for item in raw
                                        if isinstance(item, (list, tuple)) and item
                                    ]

                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(stmt.name)

            effective = model_name
            if not effective and len(inherits) == 1:
                effective = inherits[0]
            if not effective:
                continue

            if model_name:
                owned.add(model_name)
                inheritance[model_name].update(inherits)

            models[effective]["fields"].update(fields)
            models[effective]["methods"].update(methods)
            models[effective]["selections"].update(selections)

    # Merge only mixins visible in the supplied OneHR source. Native Odoo ownership
    # is not fabricated here and is represented separately by runtime_fields.
    for _round in range(8):
        changed = False
        for model_name, bases in inheritance.items():
            for base in bases:
                if base not in models:
                    continue
                before = (
                    len(models[model_name]["fields"]),
                    len(models[model_name]["methods"]),
                    len(models[model_name]["selections"]),
                )
                models[model_name]["fields"].update(models[base]["fields"])
                models[model_name]["methods"].update(models[base]["methods"])
                for field_name, values in models[base]["selections"].items():
                    models[model_name]["selections"].setdefault(field_name, values)
                after = (
                    len(models[model_name]["fields"]),
                    len(models[model_name]["methods"]),
                    len(models[model_name]["selections"]),
                )
                changed = changed or before != after
        if not changed:
            break

    return models, owned


def xml_inventory(project_root: Path):
    ids = set()
    groups = set()
    sequences = set()
    for path in project_root.rglob("*.xml"):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        try:
            addon = path.relative_to(project_root).parts[0]
        except Exception:
            addon = ""
        for rec in tree.getroot().iter("record"):
            rid = rec.get("id")
            if rid:
                ids.add(f"{addon}.{rid}")
                if rec.get("model") == "res.groups":
                    groups.add(f"{addon}.{rid}")
            if rec.get("model") == "ir.sequence":
                for field in rec.findall("field"):
                    if field.get("name") == "code" and (field.text or "").strip():
                        sequences.add((field.text or "").strip())
        for menu in tree.getroot().iter("menuitem"):
            rid = menu.get("id")
            if rid:
                ids.add(f"{addon}.{rid}")
    return ids, groups, sequences


def view_type_matrix(xml_files):
    matrix = defaultdict(set)
    for path in xml_files:
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        for rec in tree.getroot().iter("record"):
            if rec.get("model") != "ir.ui.view":
                continue
            model = None
            arch = None
            for field in rec.findall("field"):
                if field.get("name") == "model":
                    model = (field.text or "").strip()
                if field.get("name") == "arch":
                    arch = field
            if not model or arch is None:
                continue
            for child in list(arch):
                if child.tag in {"list", "form", "search"}:
                    matrix[model].add(child.tag)
    return matrix


def xml_registry_rows(path: Path):
    rows = {}
    tree = ET.parse(path)
    for rec in tree.getroot().iter("record"):
        if rec.get("model") != "onehr.demo.generator":
            continue
        values = {}
        for field in rec.findall("field"):
            name = field.get("name")
            if name == "implemented":
                values[name] = field.get("eval") == "True"
            elif name in {
                "key",
                "implementation_state",
                "contract_digest",
                "side_effect_classification",
                "reset_policy",
            }:
                values[name] = (field.text or "").strip()
        if values.get("key"):
            rows[values["key"]] = values
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    result = Result()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Identity / frozen authority / dependency topology
    # ------------------------------------------------------------------
    target_manifest = manifest(ADDON_ROOT / "__manifest__.py")
    result.ok(target_manifest.get("name") == "OneHR Enterprise Demo Dataset", "Manifest identity")
    result.ok(target_manifest.get("version") == "19.0.1.0.7", "Manifest version 19.0.1.0.7")
    result.ok(target_manifest.get("license") == "LGPL-3", "Manifest LGPL-3")
    result.ok(target_manifest.get("installable") is True, "Manifest installable")
    result.ok(target_manifest.get("application") is False, "Capstone addon is not a duplicate root application")

    expected_deps = sorted(contract["production_addon_versions"])
    result.ok(
        sorted(target_manifest.get("depends", [])) == expected_deps,
        f"Hard dependencies exactly frozen production suite ({len(expected_deps)})",
    )
    result.ok(len(expected_deps) == 25, "Revision-time production addon baseline rediscovered as 25")
    result.ok(len(contract["generator_contracts"]) == 20, "Whole-path MP05-MP24 generator contracts = 20")
    result.ok(len(contract["sequence_policies"]) == 34, "Explicit production sequence policies = 34")
    result.ok(
        contract["implemented_generator_keys"] == ["foundation.enterprise", "organization.jobs_positions"],
        "Exactly bounded MP05 + MP06 generators implemented",
    )
    result.ok(
        contract["authoritative_source_sha256"]
        == "db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e",
        "Latest authoritative composite source SHA-256 frozen",
    )
    result.ok(
        contract["root_guardrail_sha256"].upper()
        == "9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55",
        "Root Guardrail SHA-256 frozen",
    )
    result.ok(
        contract["mp05_profile_shape"]
        == {
            "quick": {"company": 1, "branches": 2, "departments": 6},
            "standard": {"company": 1, "branches": 4, "departments": 10},
            "full": {"company": 1, "branches": 6, "departments": 16},
        },
        "MP05 profile volume contract frozen",
    )

    for rel in target_manifest.get("data", []):
        result.ok((ADDON_ROOT / rel).is_file(), f"Manifest data exists — {rel}")

    # ------------------------------------------------------------------
    # Target source syntax / ORM / forbidden patterns
    # ------------------------------------------------------------------
    py_files = sorted(ADDON_ROOT.rglob("*.py"))
    xml_files = sorted(ADDON_ROOT.rglob("*.xml"))
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"))
            result.ok(True, f"Python syntax — {path.relative_to(ADDON_ROOT)}")
        except SyntaxError as exc:
            result.ok(False, f"Python syntax — {path.relative_to(ADDON_ROOT)}: {exc}")

    for path in xml_files:
        try:
            ET.parse(path)
            result.ok(True, f"XML syntax — {path.relative_to(ADDON_ROOT)}")
        except ET.ParseError as exc:
            result.ok(False, f"XML syntax — {path.relative_to(ADDON_ROOT)}: {exc}")

    xml_text = "\n".join(path.read_text(encoding="utf-8") for path in xml_files)
    result.ok("<tree" not in xml_text, "No legacy tree view tag")
    result.ok(" attrs=" not in xml_text, "No legacy attrs modifier")
    result.ok(" states=" not in xml_text, "No legacy states modifier")
    result.ok('name="groups_id"' not in xml_text, "No invalid Odoo 19 action groups_id field")
    result.ok("@string=" not in xml_text, "No inherited XPath selector by @string")

    target_xml_ids = []
    for path in xml_files:
        tree = ET.parse(path)
        for node in tree.getroot().iter():
            if node.get("id"):
                target_xml_ids.append(node.get("id"))
    result.ok(
        len(target_xml_ids) == len(set(target_xml_ids)),
        "No duplicate XML IDs inside onehr_demo",
    )

    target_models, owned = inventory(ADDON_ROOT)
    result.ok(owned == EXPECTED_MODELS, "Exact six persistent demo-owned models")
    for model in sorted(EXPECTED_MODELS):
        result.ok(model in target_models, f"Model present — {model}")
        result.ok(
            len(model.replace(".", "_").encode("utf-8")) < 63,
            f"PostgreSQL table identifier safe — {model.replace('.', '_')}",
        )

    target_runtime_py = "\n".join(
        path.read_text(encoding="utf-8")
        for path in py_files
        if path.name != "source_acceptance.py"
    )
    result.ok("_sql_constraints" not in target_runtime_py, "No legacy _sql_constraints")
    result.ok("models.Constraint(" in target_runtime_py, "Odoo 19 models.Constraint used")
    result.ok("sudo(" not in target_runtime_py, "No business sudo() bypass")
    result.ok("safe_eval(" not in target_runtime_py, "No safe_eval execution")
    result.ok(not re.search(r"(?<!literal_)eval\s*\(", target_runtime_py), "No raw eval execution")
    result.ok("getattr(" not in target_runtime_py, "No arbitrary getattr dispatch")
    result.ok("__import__(" not in target_runtime_py, "No dynamic import execution")
    result.ok(".next_by_code(" not in target_runtime_py, "Direct onehr_demo next_by_code usage is forbidden")
    result.ok("fields.Date.today(" not in target_runtime_py, "No uncontrolled fields.Date.today business clock")
    result.ok(
        "fields.Date.context_today(" not in target_runtime_py,
        "No uncontrolled context_today business clock",
    )
    result.ok(
        "datetime.now(" not in target_runtime_py and "date.today(" not in target_runtime_py,
        "No wall-clock datetime/date business truth",
    )
    result.ok("random.Random(" in target_runtime_py, "Deterministic seeded pseudo-random helper present")

    # ------------------------------------------------------------------
    # Security / UI preservation
    # ------------------------------------------------------------------
    group_text = (ADDON_ROOT / "security" / "onehr_demo_groups.xml").read_text(encoding="utf-8")
    result.ok('model="res.groups.privilege"' in group_text, "Odoo 19 res.groups.privilege pattern")
    for gid in (
        "group_onehr_demo_viewer",
        "group_onehr_demo_operator",
        "group_onehr_demo_admin",
    ):
        result.ok(f'id="{gid}"' in group_text, f"Security role present — {gid}")

    acl_text = (ADDON_ROOT / "security" / "ir.model.access.csv").read_text(encoding="utf-8-sig").lstrip("\r\n")
    acl = list(csv.DictReader(io.StringIO(acl_text)))
    result.ok(len(acl) == 12, "Exactly 12 bounded ACL rows")
    result.ok(
        all(row["group_id:id"] != "base.group_user" for row in acl),
        "No broad base.group_user custom-model ACL",
    )
    result.ok(
        all(
            row["perm_unlink"] == "0"
            for row in acl
            if row["model_id:id"] != "model_onehr_demo_scenario"
        ),
        "Operational evidence models have no ACL delete permission",
    )

    rules_tree = ET.parse(ADDON_ROOT / "security" / "onehr_demo_rules.xml")
    rules = [
        node
        for node in rules_tree.getroot().iter("record")
        if node.get("model") == "ir.rule"
    ]
    result.ok(len(rules) == 5, "Five company-boundary record rules")
    result.ok(
        all("company_ids" in ET.tostring(node, encoding="unicode") for node in rules),
        "All company rules use caller allowed-company scope",
    )

    scenario_source = (ADDON_ROOT / "models" / "demo_scenario.py").read_text(encoding="utf-8")
    result.ok(
        "require_system_demo_admin" in scenario_source,
        "High-impact server actions require system plus demo authority",
    )
    result.ok(
        "implemented_readiness_blockers(self)" in scenario_source,
        "Readiness audits all implemented generator authorities before mutation",
    )
    result.ok(
        "sanitize_text" in (ADDON_ROOT / "models" / "demo_log.py").read_text(encoding="utf-8"),
        "Persisted operational logs use sanitization",
    )

    matrix = view_type_matrix(xml_files)
    for model in sorted(EXPECTED_MODELS):
        for view_type in ("list", "form", "search"):
            result.ok(
                view_type in matrix[model],
                f"{model} has {view_type.title()} view",
            )

    # ------------------------------------------------------------------
    # Operator navigation contract
    # ------------------------------------------------------------------
    menu_tree = ET.parse(ADDON_ROOT / "views" / "menus.xml")
    menu_nodes = {node.get("id"): node for node in menu_tree.getroot().iter("menuitem")}
    dataset_parent = menu_nodes.get("menu_onehr_enterprise_demo_dataset")
    control_center_menu = menu_nodes.get("menu_onehr_demo_control_center")
    evidence_menu = menu_nodes.get("menu_onehr_demo_evidence")
    result.ok(
        dataset_parent is not None and not dataset_parent.get("action"),
        "Enterprise Demo Dataset parent is a pure navigation container",
    )
    result.ok(
        control_center_menu is not None
        and control_center_menu.get("parent") == "menu_onehr_enterprise_demo_dataset"
        and control_center_menu.get("action") == "action_onehr_demo_scenarios",
        "Creatable Demo Control Center is an explicit reachable leaf menu",
    )
    result.ok(
        evidence_menu is not None
        and evidence_menu.get("parent") == "menu_onehr_enterprise_demo_dataset",
        "Demo Evidence remains a separate secondary navigation branch",
    )

    scenario_action_tree = ET.parse(ADDON_ROOT / "views" / "demo_scenario_views.xml")
    scenario_action = next(
        (node for node in scenario_action_tree.getroot().iter("record")
         if node.get("id") == "action_onehr_demo_scenarios"),
        None,
    )
    action_context = ""
    if scenario_action is not None:
        for field in scenario_action.findall("field"):
            if field.get("name") == "context":
                action_context = (field.text or "").strip()
                break
    result.ok(
        scenario_action is not None and "create" not in action_context.lower(),
        "Demo Control Center action does not suppress Scenario creation",
    )

    evidence_action_files = {
        "action_onehr_demo_generators": "views/demo_generator_views.xml",
        "action_onehr_demo_runs": "views/demo_run_views.xml",
        "action_onehr_demo_checkpoints": "views/demo_checkpoint_views.xml",
        "action_onehr_demo_references": "views/demo_reference_views.xml",
        "action_onehr_demo_logs": "views/demo_log_views.xml",
    }
    for action_id, relpath in evidence_action_files.items():
        action_tree = ET.parse(ADDON_ROOT / relpath)
        action_node = next(
            (node for node in action_tree.getroot().iter("record") if node.get("id") == action_id),
            None,
        )
        context_text = ""
        if action_node is not None:
            for field in action_node.findall("field"):
                if field.get("name") == "context":
                    context_text = (field.text or "").replace('"', "'").replace(" ", "").lower()
                    break
        result.ok(
            action_node is not None and "'create':false" in context_text,
            f"Evidence action intentionally suppresses manual create — {action_id}",
        )

    dataset_children = [
        node.get("id") for node in menu_nodes.values()
        if node.get("parent") == "menu_onehr_enterprise_demo_dataset"
    ]
    evidence_children = [
        node.get("id") for node in menu_nodes.values()
        if node.get("parent") == "menu_onehr_demo_evidence"
    ]
    result.ok(
        dataset_children == ["menu_onehr_demo_control_center", "menu_onehr_demo_evidence"],
        "Enterprise Demo Dataset exposes exactly Control Center plus Evidence branches",
    )
    result.ok(
        evidence_children == [
            "menu_onehr_demo_generators", "menu_onehr_demo_runs", "menu_onehr_demo_checkpoints",
            "menu_onehr_demo_references", "menu_onehr_demo_logs",
        ],
        "Demo Evidence exposes exactly the five governed evidence lists",
    )

    scenario_view = (ADDON_ROOT / "views" / "demo_scenario_views.xml").read_text(encoding="utf-8")
    for token, label in [
        ('widget="statusbar"', "Control Center statusbar"),
        ('name="action_refresh_compatibility"', "Refresh Source Compatibility button"),
        ('name="action_validate_readiness"', "Validate Readiness button"),
        ('name="action_enable_demo_generation"', "Explicit non-production enable button"),
        ('name="action_generate_full"', "Full Enterprise generation boundary"),
        ('name="action_validate_dataset"', "Dataset validation button"),
        ('name="action_reset_preview"', "Reset Preview button"),
        ('name="action_reset_demo_dataset"', "Safe Reset button"),
        ('name="action_rebuild_dataset"', "Rebuild button"),
        ('class="oe_stat_button"', "Smart buttons"),
        ('widget name="web_ribbon"', "NON-PRODUCTION ribbon"),
        ("compatibility_evidence_json", "Compatibility Evidence surface"),
    ]:
        result.ok(token in scenario_view, label)

    # ------------------------------------------------------------------
    # Fixed generator registry / deterministic identity
    # ------------------------------------------------------------------
    registry_rows = xml_registry_rows(ADDON_ROOT / "data" / "generator_registry.xml")
    expected_keys = [item["key"] for item in contract["generator_contracts"]]
    result.ok(len(registry_rows) == 20, "Fixed generator registry contains 20 rows")
    result.ok(
        sorted(registry_rows) == sorted(expected_keys),
        "Generator registry exactly matches frozen code-owned keys",
    )
    result.ok(len(registry_rows) == len(set(registry_rows)), "Generator keys unique")

    implemented = [
        item["key"]
        for item in contract["generator_contracts"]
        if item.get("implemented")
    ]
    result.ok(implemented == ["foundation.enterprise", "organization.jobs_positions"], "Exactly MP05 + MP06 bounded generators are implemented")

    for item in contract["generator_contracts"]:
        row = registry_rows.get(item["key"], {})
        result.ok(
            row.get("implemented") == bool(item.get("implemented")),
            f"{item['key']}: XML implementation flag matches frozen contract",
        )
        result.ok(
            row.get("contract_digest") == item.get("contract_digest"),
            f"{item['key']}: XML contract digest matches frozen contract",
        )
        result.ok(
            row.get("side_effect_classification") == item.get("side_effect"),
            f"{item['key']}: XML side-effect classification matches contract",
        )
        result.ok(
            row.get("reset_policy") == item.get("reset_policy"),
            f"{item['key']}: XML reset policy matches contract",
        )
        result.ok(
            item["side_effect"] != "UNVERIFIED",
            f"{item['key']}: side-effect classification explicit",
        )
        result.ok(
            item["reset_policy"] != "UNVERIFIED",
            f"{item['key']}: reset policy explicit",
        )

    for item in contract["sequence_policies"]:
        result.ok(
            item["direct_demo_next_by_code"] == "FORBIDDEN",
            f"{item['code']}: direct demo sequence use forbidden",
        )
        result.ok(
            item["strategy"]
            in {
                "EXPLICIT_DETERMINISTIC_IDENTIFIER",
                "PRODUCTION_MANAGED_PRESENTATION_ONLY",
                "PROHIBITED_DIRECT_GENERATOR",
            },
            f"{item['code']}: deterministic sequence strategy explicit",
        )

    orchestrator_source = (ADDON_ROOT / "services" / "orchestrator.py").read_text(encoding="utf-8")
    result.ok(
        '"foundation.enterprise": generate_foundation_enterprise' in orchestrator_source,
        "MP05 fixed code-owned generator handler",
    )
    result.ok(
        '"foundation.enterprise": validate_foundation_enterprise' in orchestrator_source,
        "MP05 fixed code-owned generator validator",
    )
    result.ok(
        '"foundation.enterprise": readiness_blockers_foundation_enterprise' in orchestrator_source,
        "MP05 fixed readiness checker",
    )
    result.ok("getattr(" not in orchestrator_source, "No arbitrary dynamic generator dispatch")
    result.ok(
        '"organization.jobs_positions": generate_organization_jobs_positions' in orchestrator_source,
        "MP06 fixed code-owned generator handler",
    )
    result.ok(
        '"organization.jobs_positions": validate_organization_jobs_positions' in orchestrator_source,
        "MP06 fixed code-owned generator validator",
    )
    result.ok(
        '"organization.jobs_positions": readiness_blockers_organization_jobs_positions' in orchestrator_source,
        "MP06 fixed readiness checker",
    )

    mp05_source = (ADDON_ROOT / "generators" / "foundation_enterprise.py").read_text(encoding="utf-8")
    result.ok("BRANCH_CATALOG" in mp05_source, "MP05 deterministic branch catalog")
    result.ok("DEPARTMENT_CATALOG" in mp05_source, "MP05 deterministic organization catalog")
    result.ok("stable_identifier(" in mp05_source, "MP05 deterministic production business codes")
    result.ok(".next_by_code(" not in mp05_source, "MP05 consumes no mutable production sequence")
    result.ok("sudo(" not in mp05_source, "MP05 does not bypass production security")
    result.ok(
        "fields.Date.context_today(" not in mp05_source
        and "fields.Date.today(" not in mp05_source,
        "MP05 business dates come only from scenario reference clock",
    )
    result.ok(
        all(token in mp05_source for token in ("res.company", "onehr.branch", "hr.department")),
        "MP05 uses canonical production owners",
    )
    result.ok("REUSE_ON_REBUILD" in mp05_source, "MP05 reset policy explicit in generator")
    result.ok(
        "with_context(active_test=False).search" in mp05_source,
        "MP05 deterministic collision lookup includes archived masters",
    )

    scenario_source = (ADDON_ROOT / "models" / "demo_scenario.py").read_text(encoding="utf-8")
    result.ok(
        '"code","company_id","profile","profile_version","scenario_version","reference_date"' in scenario_source,
        "Scenario stable identity includes code/profile/reference contract",
    )
    result.ok(
        "Scenario identity is frozen after demo provenance exists" in scenario_source,
        "Scenario identity mutation is blocked after provenance exists",
    )

    reset_source = (ADDON_ROOT / "services" / "reset.py").read_text(encoding="utf-8")
    result.ok(".unlink(" not in reset_source, "Reset service has no generic unlink fallback")
    result.ok(
        '("scenario_id", "=", self.scenario.id)' in reset_source,
        "Reset preview starts from explicit scenario provenance",
    )
    for model in ("res.company", "onehr.branch", "hr.department"):
        result.ok(
            f'("{model}", "REUSE_ON_REBUILD")' in reset_source,
            f"MP05 bounded reset handler — {model}",
        )
    result.ok("PROTECTED_NO_HANDLER" in reset_source, "Reset fails closed for unimplemented model/policy pairs")
    result.ok("with self.env.cr.savepoint()" in reset_source, "Reset executes as one bounded atomic unit")
    result.ok("Reset postcondition failed" in reset_source, "Reset verifies active-provenance postcondition")

    result.ok("def action_execute_next_10(self):" in scenario_source, "Control Center Execute Next 10 action exists")
    result.ok("range(10)" in scenario_source, "Execute Next 10 is bounded to ten contracts")
    result.ok("reload_form=False" in scenario_source, "Batch failure notification does not auto-reload the form")
    result.ok("fail-closed" in scenario_source, "Batch execution remains fail-closed")

    # ------------------------------------------------------------------
    # Root guardrail and exact latest production source baseline
    # ------------------------------------------------------------------
    guardrail = project_root / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md"
    guardrail_sha = project_root / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.sha256"
    if guardrail.is_file() and guardrail_sha.is_file():
        actual = hashlib.sha256(guardrail.read_bytes()).hexdigest().upper()
        declared = guardrail_sha.read_text(encoding="utf-8").strip().split()[0].upper()
        expected = contract["root_guardrail_sha256"].upper()
        result.ok(actual == expected, "Root Guardrail raw SHA-256 matches")
        result.ok(declared == expected, "Root Guardrail declared checksum matches")
    else:
        result.ok(False, "Root Guardrail and checksum exist")

    for addon, version in sorted(contract["production_addon_versions"].items()):
        manifest_path = project_root / addon / "__manifest__.py"
        result.ok(manifest_path.is_file(), f"Production manifest exists — {addon}")
        if not manifest_path.is_file():
            continue
        try:
            production_manifest = manifest(manifest_path)
        except Exception:
            result.ok(False, f"Production manifest parses — {addon}")
            continue
        result.ok(
            production_manifest.get("version") == version,
            f"Production source version — {addon}={version}",
        )
        result.ok(
            normalized_text_sha(manifest_path)
            == contract["production_manifest_normalized_sha256"][addon],
            f"Production manifest fingerprint — {addon}",
        )

    for addon, expected_hash in sorted(
        contract["published_fingerprint_normalized_sha256"].items()
    ):
        fp = project_root / addon / "docs" / "SOURCE_FINGERPRINT_SHA256.txt"
        result.ok(fp.is_file(), f"Published source fingerprint exists — {addon}")
        if fp.is_file():
            result.ok(
                normalized_text_sha(fp) == expected_hash,
                f"Published source fingerprint frozen — {addon}",
            )

    project_models, _ = inventory(project_root)
    xmlids, groups, sequences = xml_inventory(project_root)

    foundation = next(
        item
        for item in contract["generator_contracts"]
        if item["key"] == "foundation.enterprise"
    )
    result.ok(
        foundation.get("runtime_fields") == FRAMEWORK_NATIVE_FIELDS,
        "MP05 Odoo-native runtime field contract is explicit and bounded",
    )

    for item in contract["generator_contracts"]:
        prefix = item["key"]
        for model, expected_fields in sorted(item.get("models", {}).items()):
            result.ok(model in project_models, f"{prefix}: production model — {model}")
            if model not in project_models:
                continue
            for field_name, expected_type in sorted(expected_fields.items()):
                result.ok(
                    project_models[model]["fields"].get(field_name) == expected_type,
                    f"{prefix}: field/type — {model}.{field_name}={expected_type}",
                )

        for model, methods in sorted(item.get("methods", {}).items()):
            for method_name in methods:
                result.ok(
                    method_name in project_models[model]["methods"],
                    f"{prefix}: business method — {model}.{method_name}",
                )

        for path, expected_values in sorted(item.get("selections", {}).items()):
            model, field_name = path.rsplit(".", 1)
            actual = set(project_models[model]["selections"].get(field_name, []))
            result.ok(
                set(expected_values).issubset(actual),
                f"{prefix}: selection contract — {path}",
            )

        for group in item.get("groups", []):
            result.ok(group in groups, f"{prefix}: actor group — {group}")
        for xmlid in item.get("xmlids", []):
            result.ok(xmlid in xmlids, f"{prefix}: critical XML ID — {xmlid}")

    for item in contract["sequence_policies"]:
        result.ok(
            item.get("demo_generation_dependency") == "NONE",
            f"{item['code']}: production sequence is audit-only for current demo generation",
        )
        result.ok(
            item["direct_demo_next_by_code"] == "FORBIDDEN",
            f"{item['code']}: direct demo sequence use remains forbidden",
        )
        # Source-level ownership/identity contracts remain auditable. Their runtime
        # sequence rows are intentionally not a prerequisite for the current MP05 generator.
        model = item["model"]
        for field_name in item["stable_fields"]:
            result.ok(
                field_name in project_models[model]["fields"],
                f"Sequence stable identity contract — {item['code']} -> {model}.{field_name}",
            )

    # ------------------------------------------------------------------
    # Runtime audit implementation itself
    # ------------------------------------------------------------------
    compatibility = (ADDON_ROOT / "services" / "compatibility.py").read_text(encoding="utf-8")
    result.ok(
        'contract.get("runtime_fields", {})' in compatibility,
        "Runtime compatibility audits MP05 Odoo-native fields",
    )
    result.ok(
        "for contract in GENERATOR_CONTRACTS" in compatibility,
        "Runtime compatibility audits every generator contract",
    )
    result.ok(
        "for policy in SEQUENCE_POLICIES" in compatibility,
        "Runtime compatibility audits every sequence policy",
    )
    result.ok(
        'demo_generation_dependency' in compatibility and 'required_for_demo = dependency != "NONE"' in compatibility,
        "Runtime sequence audit explicitly separates production sequence state from demo generation dependency",
    )
    result.ok(
        'not row["key"].startswith(("sequence.", "sequence_identity."))' in compatibility,
        "Mutable production sequence state is excluded from compatibility fingerprint",
    )
    result.ok(
        "PRODUCTION_MANIFEST_NORMALIZED_SHA256" in compatibility,
        "Runtime compatibility validates source manifests",
    )
    result.ok(
        "PUBLISHED_FINGERPRINT_NORMALIZED_SHA256" in compatibility,
        "Runtime compatibility validates published fingerprints",
    )
    result.ok(
        all(token in compatibility for token in ("to install", "to upgrade", "to remove")),
        "Module-operation quiescence covers install/upgrade/remove",
    )
    fingerprint_block = compatibility.split("fingerprint_payload = {", 1)[1].split("fingerprint = hashlib.sha256", 1)[0]
    evidence_block = compatibility.split("evidence = {", 1)[1].split("return {", 1)[0]
    result.ok(
        '"database"' not in fingerprint_block
        and "AUTHORITATIVE_SOURCE_LABEL" not in fingerprint_block
        and '"operator"' not in fingerprint_block
        and '"checked_at"' not in fingerprint_block
        and '"database"' in evidence_block
        and "AUTHORITATIVE_SOURCE_LABEL" in evidence_block
        and '"operator"' in evidence_block
        and '"checked_at"' in evidence_block,
        "Stable compatibility lock excludes execution-only metadata and human source label",
    )

    # ------------------------------------------------------------------
    # Runtime regression surface and documentation
    # ------------------------------------------------------------------
    test_files = sorted((ADDON_ROOT / "tests").glob("test_*.py"))
    test_count = 0
    for path in test_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        count = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
        test_count += count
        result.ok('"post_install"' in source, f"Post-install runtime tag — {path.name}")
    result.ok(
        test_count >= 23,
        f"Bounded runtime regression methods >=23 (actual {test_count})",
    )

    for rel in sorted(REQUIRED_DOCS):
        result.ok((ADDON_ROOT / rel).is_file(), f"Governance/documentation artifact — {rel}")

    result.warn(
        "Windows/Odoo runtime install and registry acceptance are intentionally NOT_RUN by static acceptance."
    )
    result.warn(
        "Windows/Odoo MP05 generation, idempotency, reset/rebuild and UI acceptance remain NOT_RUN by static acceptance."
    )

    print(result.render())
    return 0 if not result.fails else 1


if __name__ == "__main__":
    raise SystemExit(main())

