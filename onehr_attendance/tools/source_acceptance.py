#!/usr/bin/env python3
"""Static/source acceptance for OneHR Attendance Direct Full Build.

This deliberately does not pretend to be an Odoo runtime test. It verifies the
frozen source contract before the addon is moved to the user's Windows runtime.
"""

from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
PASSES: list[str] = []

EXPECTED_DEPENDS = ["onehr_corehr", "onehr_security", "hr_attendance"]
CUSTOM_MODELS = {
    "onehr.shift",
    "onehr.shift.pattern",
    "onehr.shift.assignment",
    "onehr.attendance.exception",
    "onehr.attendance.reconciliation",
    "onehr.attendance.import.batch",
}
NATIVE_INHERITS = {
    "hr.attendance",
    "hr.attendance.overtime.line",
    "hr.attendance.overtime.rule",
    "hr.attendance.overtime.ruleset",
}
EXPECTED_ACL_ROWS = 15
EXPECTED_TEST_METHODS = 29
REQUIRED_DOCS = {
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "MASTER_MODEL_REGISTRY_ALIGNMENT.md",
    "BASELINE_FEATURE_PRESERVATION_MATRIX.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "INTEGRATION_CONTRACTS.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_ATTENDANCE_IMPLEMENTATION_REPORT.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md",
}


def check(condition: bool, message: str) -> None:
    if condition:
        PASSES.append(message)
    else:
        FAILURES.append(message)


def read_manifest() -> dict:
    return ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))


def source_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "models").glob("*.py"))
    )


def model_contracts() -> tuple[set[str], set[str]]:
    custom: set[str] = set()
    inherited: set[str] = set()
    for path in (ROOT / "models").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for statement in node.body:
                if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                names = [target.id for target in targets if isinstance(target, ast.Name)]
                value = statement.value
                if "_name" in names and isinstance(value, ast.Constant) and isinstance(value.value, str):
                    custom.add(value.value)
                if "_inherit" in names:
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        inherited.add(value.value)
                    elif isinstance(value, (ast.List, ast.Tuple)):
                        inherited.update(
                            item.value for item in value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        )
    return custom, inherited


def view_models_and_types() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in list((ROOT / "views").glob("*.xml")) + list((ROOT / "reports").glob("*.xml")):
        tree = ET.parse(path)
        for record in tree.findall(".//record"):
            if record.get("model") != "ir.ui.view":
                continue
            model = record.find("field[@name='model']")
            arch = record.find("field[@name='arch']")
            if model is None or not (model.text or "").strip() or arch is None:
                continue
            model_name = (model.text or "").strip()
            types = result.setdefault(model_name, set())
            for child in list(arch):
                tag = child.tag.split("}")[-1]
                if tag in {"list", "form", "search", "calendar", "pivot", "graph"}:
                    types.add(tag)
    return result


def count_tests() -> tuple[int, bool]:
    count = 0
    all_tagged = True
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        count += sum(
            isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
        if '@tagged("post_install", "-at_install", "onehr_attendance")' not in text:
            all_tagged = False
    return count, all_tagged


def main() -> int:
    manifest = read_manifest()
    check(manifest.get("version", "").startswith("19.0."), "Manifest targets Odoo 19")
    check(manifest.get("depends") == EXPECTED_DEPENDS, "Hard dependencies exactly match frozen contract")
    check(manifest.get("installable") is True, "Addon is installable")
    check(manifest.get("application") is True, "Addon is an application surface")

    py_files = sorted(ROOT.rglob("*.py"))
    compile_ok = True
    for path in py_files:
        if "__pycache__" in path.parts:
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            compile_ok = False
            FAILURES.append(f"Python compile failed: {path.relative_to(ROOT)}: {exc}")
    check(compile_ok, "All Python files compile")

    xml_files = sorted(ROOT.rglob("*.xml"))
    xml_ok = True
    for path in xml_files:
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            xml_ok = False
            FAILURES.append(f"XML parse failed: {path.relative_to(ROOT)}: {exc}")
    check(xml_ok, "All XML files parse")

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

    # Odoo 19 date-filter contract:
    # default_period uses internal period ids such as "month" / "year", not
    # presentation labels such as "this_month".  Validate every declared
    # default period so a well-formed XML file cannot still fail at runtime.
    invalid_default_periods = []
    base_period_ids = {
        "first_quarter", "second_quarter", "third_quarter", "fourth_quarter",
        "month", "year",
    }
    period_pattern = re.compile(r"^(?:month|year)[+-][1-9]\d*$")
    for view_path in sorted((ROOT / "views").glob("*.xml")):
        try:
            view_tree = ET.parse(view_path)
        except Exception:
            continue
        for filter_node in view_tree.findall(".//filter[@date][@default_period]"):
            raw_value = (filter_node.get("default_period") or "").strip()
            custom_names = {
                f"custom_{child.get('name')}"
                for child in filter_node.findall("./filter[@name]")
                if child.get("name")
            }
            for period_id in [item.strip() for item in raw_value.split(",") if item.strip()]:
                valid = (
                    period_id in base_period_ids
                    or bool(period_pattern.match(period_id))
                    or period_id in custom_names
                )
                if not valid:
                    invalid_default_periods.append(
                        f"{view_path.relative_to(ROOT)}: {period_id}"
                    )
    check(
        not invalid_default_periods,
        "Odoo 19 date-filter default_period values are valid",
    )

    custom, inherited = model_contracts()
    check(custom == CUSTOM_MODELS, f"Exactly {len(CUSTOM_MODELS)} approved custom persistent models")
    check(NATIVE_INHERITS.issubset(inherited), "All four native Attendance/Overtime models are extended")
    check("onehr.attendance" not in custom, "No duplicate onehr.attendance model")

    business_source = source_text()
    check(".sudo(" not in business_source, "No sudo() bypass in business model source")
    check("_sql_constraints" not in business_source, "No legacy _sql_constraints")
    check(not re.search(r"\bdef\s+unlink\s*\(", business_source), "No business unlink() override")
    check("@api.ondelete(at_uninstall=False)" in business_source, "Uninstall-safe ondelete protections are present")
    check("onehr_ingest_interval" in business_source, "Stable governed attendance ingestion service exists")
    check("_onehr_exclusion_reason_for_date" in business_source, "Timeoff/Learning exclusion extension hook exists")
    check("hr.attendance.overtime.line" in business_source, "Odoo 19 actual overtime-line mapping is explicit")

    acl_path = ROOT / "security" / "ir.model.access.csv"
    with acl_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    check(len(rows) == EXPECTED_ACL_ROWS, f"ACL row count is exactly {EXPECTED_ACL_ROWS}")
    check(not any(row["group_id:id"] == "base.group_user" for row in rows), "No broad base.group_user custom ACL")
    support_models = {"hr.model_hr_employee", "onehr_base.model_onehr_position", "resource.model_resource_calendar"}
    support_rows = [row for row in rows if row["model_id:id"] in support_models]
    check(len(support_rows) == 3 and all(
        row["perm_read"] == "1" and row["perm_write"] == "0" and row["perm_create"] == "0" and row["perm_unlink"] == "0"
        for row in support_rows
    ), "Employee/position/calendar support ACLs are read-only")

    groups = (ROOT / "security" / "onehr_attendance_groups.xml").read_text(encoding="utf-8")
    check("onehr_corehr.group_onehr_corehr_officer" not in groups, "Attendance Officer does not imply Core HR Officer")
    check("hr.group_hr_user" not in groups, "Attendance Officer does not imply broad HR Officer")
    check("res.groups.privilege" in groups, "Odoo 19 privilege model is used")

    view_matrix = view_models_and_types()
    for model in CUSTOM_MODELS:
        types = view_matrix.get(model, set())
        check({"list", "form", "search"}.issubset(types), f"{model}: explicit list/form/search coverage")
    check({"list", "form", "search", "calendar", "pivot", "graph"}.issubset(view_matrix.get("hr.attendance", set())), "hr.attendance has enterprise list/form/search/calendar/pivot/graph")
    for model in ("hr.attendance.overtime.line", "hr.attendance.overtime.rule", "hr.attendance.overtime.ruleset"):
        check({"list", "form", "search"}.issubset(view_matrix.get(model, set())), f"{model}: explicit list/form/search coverage")

    view_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "views").glob("*.xml"))
    for marker, label in [
        ('widget="statusbar"', "Statusbar widgets"),
        ('class="oe_stat_button"', "Smart buttons"),
        ('class="btn-secondary"', "Body/action buttons"),
        ('<chatter', "Chatter"),
        ('<list', "Enterprise list/One2many row actions"),
    ]:
        check(marker in view_text, f"Professional UI marker present: {label}")
    check(view_text.count('type="object"') >= 25, "Rich object-action coverage is present")

    test_count, all_tagged = count_tests()
    check(test_count == EXPECTED_TEST_METHODS, f"Exactly {EXPECTED_TEST_METHODS} runtime test methods")
    check(all_tagged, "All runtime test classes are post_install/-at_install tagged")

    existing_docs = {path.name for path in (ROOT / "docs").glob("*.md")}
    check(REQUIRED_DOCS.issubset(existing_docs), "All mandatory governance/completeness documents exist")
    guardrail = (ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md").read_text(encoding="utf-8")
    check("HARD GATE 11 — INTENTIONALLY UNDEFINED" in guardrail, "Hard Gate 11 is intentionally not invented")
    check("MAX_CODEX_ATTEMPTS_PER_TASK: 2" in guardrail, "Codex retry limit is hard-coded")
    check("CODEX_ROLE: BOUNDED_IMPLEMENTATION_WORKER" in guardrail, "Codex role is bounded")

    implementation_paths = []
    for folder in ("models", "security", "data", "views", "reports", "static", "tests"):
        implementation_paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file())
    implementation_paths.append(ROOT / "__manifest__.py")
    all_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in implementation_paths if path.suffix in {".py", ".xml", ".md", ".csv", ".html"}
    )
    check("Odoo 18" not in all_text and "odoo 18" not in all_text, "No Odoo 18 implementation residue")

    print(f"SOURCE_FILES_PYTHON: {len([p for p in py_files if '__pycache__' not in p.parts])}")
    print(f"SOURCE_FILES_XML: {len(xml_files)}")
    print(f"CUSTOM_PERSISTENT_MODELS: {len(CUSTOM_MODELS)}")
    print(f"NATIVE_MODELS_EXTENDED: {len(NATIVE_INHERITS)}")
    print(f"ACL_ROWS: {len(rows)}")
    print(f"RUNTIME_TEST_METHODS: {test_count}")
    print(f"SOURCE_ACCEPTANCE_PASS_COUNT: {len(PASSES)}")
    print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"FAIL: {failure}")

    if FAILURES:
        print("ONEHR_ATTENDANCE_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
        print("WINDOWS_RUNTIME_ACCEPTANCE: NOT_RUN")
        print("ONEHR_ATTENDANCE_MOVE_FORWARD_READY: NO")
        return 1

    print("ONEHR_ATTENDANCE_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
    print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
    print("ONEHR_ATTENDANCE_MOVE_FORWARD_READY: NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
