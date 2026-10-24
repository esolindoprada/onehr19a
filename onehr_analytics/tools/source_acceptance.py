#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
passes = []
warnings = []
failures = []


def ok(label):
    passes.append(label)
    print(f"PASS: {label}")


def warn(label):
    warnings.append(label)
    print(f"WARN: {label}")


def fail(label, details=""):
    message = f"{label}{': ' + details if details else ''}"
    failures.append(message)
    print(f"FAIL: {message}")


def check(condition, label, details=""):
    ok(label) if condition else fail(label, details)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def parse_manifest():
    return ast.literal_eval(read("__manifest__.py"))


# ---------------------------------------------------------------------------
# Hard Gate 0 / manifest / task identity
# ---------------------------------------------------------------------------
manifest = parse_manifest()
check(manifest.get("name") == "OneHR Analytics & KPI Dashboards", "Manifest product identity")
check(manifest.get("version") == "19.0.1.0.0", "Manifest version 19.0.1.0.0")
check(manifest.get("depends") == ["onehr_security"], "Hard dependencies exactly onehr_security")
check(manifest.get("license") == "LGPL-3", "Manifest LGPL-3 license")
check(manifest.get("installable") is True, "Manifest installable")
check(manifest.get("application") is False, "Analytics remains OneHR addon, not duplicate root application")
for data_file in manifest.get("data", []):
    check((ROOT / data_file).is_file(), f"Manifest data exists — {data_file}")

readme = read("README.md")
check("Odoo 19 Community Edition" in readme, "README target is Odoo 19 CE")
check("onehr.analytics.tile" in readme and "onehr.kpi.snapshot" in readme and "onehr.mixin.analytics" in readme,
      "README exact Analytics model contract")

# ---------------------------------------------------------------------------
# Python / model structural inventory
# ---------------------------------------------------------------------------
py_files = sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)
for py in py_files:
    try:
        ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        ok(f"Python syntax — {py.relative_to(ROOT)}")
    except SyntaxError as exc:
        fail(f"Python syntax — {py.relative_to(ROOT)}", str(exc))

model_source = "\n".join(read(p.relative_to(ROOT)) for p in (ROOT / "models").glob("*.py"))
persistent_names = set(re.findall(r'_name\s*=\s*[\"\']([^\"\']+)[\"\']', model_source))
# abstract one still appears in _name; classify by its source explicitly.
expected_all = {"onehr.analytics.tile", "onehr.kpi.snapshot", "onehr.mixin.analytics"}
check(persistent_names == expected_all, "Exact Analytics ORM model names", f"found={sorted(persistent_names)}")
check('models.AbstractModel' in read("models/analytics_mixin.py"), "onehr.mixin.analytics is abstract")
check('_name = "onehr.analytics.tile"' in read("models/analytics_tile.py"), "Persistent model onehr.analytics.tile")
check('_name = "onehr.kpi.snapshot"' in read("models/kpi_snapshot.py"), "Persistent model onehr.kpi.snapshot")
check("onehr_analytics.onehr_analytics" not in model_source, "Tutorial model removed")
check("from . import controllers" not in read("__init__.py"), "No Analytics controller import")
check(not (ROOT / "controllers").exists(), "No public/private controller scaffold retained")
check(not (ROOT / "demo").exists(), "Tutorial demo scaffold removed")

# human-friendly decomposition
for rel in ("models/analytics_mixin.py", "models/provider_engine.py", "models/analytics_tile.py", "models/kpi_snapshot.py"):
    check((ROOT / rel).exists(), f"Human-friendly model module present — {rel}")
check("AnalyticsProviderEngine" in read("models/provider_engine.py"), "Provider engine decomposed from ORM model")
check("class OneHRAnalyticsTile" in read("models/analytics_tile.py"), "Human-readable Tile class name")
check("class OneHRKPISnapshot" in read("models/kpi_snapshot.py"), "Human-readable Snapshot class name")

# ---------------------------------------------------------------------------
# Odoo 19 ORM / DB identifier safety
# ---------------------------------------------------------------------------
for identifier in (
    "onehr_analytics_tile",
    "onehr_kpi_snapshot",
    "onehr_analytics_tile_alert_user_rel",
    "onehr_analytics_tile_favorite_user_rel",
):
    check(len(identifier.encode()) < 63, f"PostgreSQL identifier <63 bytes — {identifier}")
check('"onehr_analytics_tile_alert_user_rel"' in read("models/analytics_tile.py"), "Alert Many2many relation explicitly named")
check('"onehr_analytics_tile_favorite_user_rel"' in read("models/analytics_tile.py"), "Favorite Many2many relation explicitly named")
check("_sql_constraints" not in model_source, "No legacy _sql_constraints")
check(model_source.count("models.Constraint(") >= 2, "Odoo 19 models.Constraint used")
check("UNIQUE(company_id, code)" in model_source, "Tile company/code uniqueness constraint")
check("UNIQUE(tile_id, period_start, period_end)" in model_source, "Snapshot tile/period uniqueness constraint")

# ---------------------------------------------------------------------------
# XML syntax / IDs / Odoo 19 view hygiene
# ---------------------------------------------------------------------------
xml_files = sorted(ROOT.rglob("*.xml"))
xml_ids = []
for xml in xml_files:
    try:
        tree = ET.parse(xml)
        ok(f"XML syntax — {xml.relative_to(ROOT)}")
        for node in tree.iter():
            value = node.attrib.get("id")
            if value:
                xml_ids.append((value, xml.relative_to(ROOT)))
    except ET.ParseError as exc:
        fail(f"XML syntax — {xml.relative_to(ROOT)}", str(exc))
seen = {}
dups = []
for xid, path in xml_ids:
    if xid in seen:
        dups.append((xid, seen[xid], path))
    else:
        seen[xid] = path
check(not dups, "No duplicate XML IDs", str(dups[:5]))
xml_source = "\n".join(x.read_text(encoding="utf-8") for x in xml_files)
check("<tree" not in xml_source, "No legacy tree view tag")
check("attrs=" not in xml_source, "No legacy attrs modifier")
check("states=" not in xml_source, "No legacy states modifier")
check('<field name="groups_id">' not in xml_source, "No invalid action groups_id field")
# menu updates may legitimately use group_ids; actions must use group_ids if grouped.
check("group_ids" in read("views/analytics_tile_views.xml"), "Odoo 19 action group_ids used")

# Standalone labels need for= in form XML; plain text should use div/span.
for xml in (ROOT / "views").glob("*.xml"):
    try:
        tree = ET.parse(xml)
        bad_labels=[]
        for node in tree.iter("label"):
            if "string" in node.attrib and "for" not in node.attrib:
                bad_labels.append(node.attrib)
        check(not bad_labels, f"Form labels have field target — {xml.name}", str(bad_labels))
    except ET.ParseError:
        pass

# search groups carry no unsupported attributes
for xml in (ROOT / "views").glob("*.xml"):
    try:
        tree = ET.parse(xml)
        bad=[]
        for search in tree.iter("search"):
            for group in search.findall(".//group"):
                if group.attrib:
                    bad.append(group.attrib)
        check(not bad, f"Search group elements attribute-free — {xml.name}", str(bad))
    except ET.ParseError:
        pass

# ---------------------------------------------------------------------------
# UI matrix and professional UX
# ---------------------------------------------------------------------------
tile_view = read("views/analytics_tile_views.xml")
snapshot_view = read("views/kpi_snapshot_views.xml")
for view_name, src in (("Tile", tile_view), ("Snapshot", snapshot_view)):
    for tag,label in (("<list", "List"), ("<form", "Form"), ("<search", "Search")):
        check(tag in src, f"{view_name} {label} view")
check("<kanban" in tile_view, "Tile executive Kanban dashboard")
check("<pivot" in snapshot_view, "Snapshot Pivot analysis")
check("<graph" in snapshot_view, "Snapshot Graph analysis")
check('widget="statusbar"' in tile_view, "Tile workflow Statusbar Widget")
check('widget="statusbar"' in snapshot_view, "Snapshot KPI outcome Statusbar Widget")
for token,label in (
    ("action_activate", "Activate Action Button"),
    ("action_pause", "Pause Action Button"),
    ("action_resume", "Resume Action Button"),
    ("action_retire", "Retire Action Button"),
    ("action_snapshot_now", "Generate Snapshot Action Button"),
    ("oe_stat_button", "Smart Button framework"),
    ("action_open_snapshots", "Snapshot Smart Button"),
    ("action_open_breaches", "Breach Smart Button"),
    ("action_test_provider", "Provider body action"),
    ("action_open_source_records", "Drill-through body action"),
    ("action_export_snapshot_csv", "CSV body action"),
    ("action_toggle_favorite", "Favorite action"),
):
    check(token in tile_view, f"Professional Tile UI — {label}")
# One2many row actions appear inside snapshot_ids list.
check('name="snapshot_ids"' in tile_view and 'name="action_open_snapshot"' in tile_view and 'name="action_open_source"' in tile_view,
      "One2many snapshot row action buttons")
check("<chatter" in tile_view, "Tile chatter/activity surface")
check('create="0" edit="0" delete="0"' in snapshot_view, "Snapshot immutable form UX")
check("web_ribbon" in tile_view and "web_ribbon" in snapshot_view, "Enterprise ribbons used where meaningful")

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
security = read("security/onehr_analytics_groups.xml")
rules = read("security/onehr_analytics_rules.xml")
acl_path = ROOT / "security/ir.model.access.csv"
with acl_path.open(newline="", encoding="utf-8") as fh:
    acl_rows = list(csv.DictReader(fh))
check(len(acl_rows) == 6, "Exactly six custom-model ACL rows", f"found={len(acl_rows)}")
check(all(row["group_id:id"] != "base.group_user" for row in acl_rows), "No broad base.group_user Analytics ACL")
for gid in ("group_onehr_analytics_analyst", "group_onehr_analytics_manager", "group_onehr_analytics_admin"):
    check(gid in security, f"Security role present — {gid}")
check('model="res.groups.privilege"' in security, "Odoo 19 res.groups.privilege pattern")
check("onehr_security.group_onehr_security_user" in security, "Analytics Analyst implies OneHR security user")
check("hr.group_hr_user" not in security and "hr.group_hr_manager" not in security and "base.group_system" not in security,
      "Analytics roles do not escalate HR/System authority")
check(rules.count('<field name="global" eval="True"/>') == 2, "Two global company boundary rules")
check("model_onehr_analytics_tile" in rules and "model_onehr_kpi_snapshot" in rules, "Company rules cover both persistent models")
# No business sudo anywhere in Python source.
check(".sudo(" not in model_source, "No business sudo bypass in Analytics models/provider")
safe_eval_code = re.sub(r'(?s)""".*?"""|\'\'\'.*?\'\'\'', '', model_source)
check("safe_eval(" not in safe_eval_code, "No safe_eval formula execution")
# ast.literal_eval contains 'literal_eval', not raw Python eval call.
raw_eval_calls = [m.group(0) for m in re.finditer(r'(?<!literal_)\beval\s*\(', model_source)]
check(not raw_eval_calls, "No raw eval formula execution", str(raw_eval_calls))
check("ast.literal_eval" in read("models/analytics_mixin.py"), "Literal-only configured domain parsing")

# ---------------------------------------------------------------------------
# Provider ownership / soft integration
# ---------------------------------------------------------------------------
provider = read("models/provider_engine.py")
for model_name in (
    "hr.employee", "hr.applicant", "onehr.recruitment.source.metric", "hr.attendance",
    "onehr.leave.request", "onehr.learning.session", "onehr.learning.enrollment",
    "onehr.appraisal.form", "onehr.payroll.export", "onehr.talent.pool",
    "onehr.succession.plan", "onehr.discipline.case",
):
    check(model_name in provider, f"Approved provider allow-list — {model_name}")
for method,label in (
    ("onehr_appraisal_kpi_snapshot", "Appraisal KPI service"),
    ("onehr_learning_kpi_snapshot", "Learning KPI service"),
    ("onehr_career_kpi_snapshot", "Career KPI service"),
):
    check(method in provider, f"Soft integration contract — {label}")
check("Model.check_access(\"read\")" in provider, "Provider preserves source model read authority")
check("Branch.check_access(\"read\")" in provider, "Branch resolution preserves source authority")
check("fails closed" in provider.lower() or "fail" in provider.lower(), "Provider documents fail-closed branch behavior")
check('if "branch_id" not in Model._fields' in provider, "Branch-scoped provider requires branch_id")
check('if not self.env.registry.get("onehr.branch")' in provider, "Branch master remains soft capability")
check("ALLOWED_SOURCE_MODELS" in provider, "Fixed model allow-list enforcement")
check("SERVICE_METRIC_SELECTION" in provider, "Fixed service metric allow-list enforcement")
check("getattr(Model" in provider and "service_metric_key" in provider, "Only selected fixed KPI service dispatch")

# ---------------------------------------------------------------------------
# KPI lifecycle / evidence / analytics completeness
# ---------------------------------------------------------------------------
tile_model = read("models/analytics_tile.py")
snap_model = read("models/kpi_snapshot.py")
mixin = read("models/analytics_mixin.py")
for token,label in (
    ("draft", "Draft lifecycle"), ("active", "Active lifecycle"), ("paused", "Paused lifecycle"), ("retired", "Retired lifecycle"),
    ("warning_threshold", "Warning threshold"), ("critical_threshold", "Critical threshold"),
    ("snapshot_frequency", "Snapshot frequency"), ("next_snapshot_date", "Next snapshot scheduling"),
    ("alert_user_ids", "Alert recipients"), ("favorite_user_ids", "Per-user favorites"),
    ("_schedule_threshold_activities", "Threshold activity alerts"),
    ("_cron_generate_due_snapshots", "Scheduled snapshot generation"),
    ("_cron_archive_old_snapshots", "Retention archival"),
    ("action_open_source_records", "Source drill-through"),
    ("action_export_snapshot_csv", "CSV export"),
    ("onehr_analytics_kpi_feed", "Downstream model-level KPI feed"),
):
    check(token in tile_model, f"Analytics functional contract — {label}")
for token,label in (
    ("previous_value", "Previous-period baseline"),
    ("mom_baseline_value", "Month-over-month baseline"),
    ("hoh_baseline_value", "Half-over-half baseline"),
    ("yoy_baseline_value", "Year-over-year baseline"),
    ("previous_change_percent", "Previous-period percent change"),
    ("mom_change_percent", "MoM percent change"),
    ("hoh_change_percent", "HoH percent change"),
    ("yoy_change_percent", "YoY percent change"),
    ("source_record_count", "Aggregate record count provenance"),
    ("source_payload_json", "Sanitized provider provenance"),
    ("drilldown_domain", "Drill-through domain evidence"),
):
    check(token in snap_model, f"Snapshot evidence contract — {label}")
check("onehr_analytics_snapshot_create" in snap_model and "AccessError" in snap_model, "Snapshot create path is transport-controlled")
check("def unlink" in snap_model and "cannot be deleted" in snap_model, "Snapshot deletion blocked")
check("onehr_analytics_archive" in snap_model, "Snapshot archival write is context-gated")
check("ast.literal_eval" in mixin, "Configured domains use ast.literal_eval")
check("_analytics_threshold_status" in mixin, "Central threshold evaluation helper")
check("_analytics_percent_change" in mixin, "Central trend percentage helper")
check("_analytics_period_bounds" in mixin, "Central periodic snapshot helper")

# no fake Enterprise-only capabilities in manifest/source
combined_text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "models").glob("*.py"))
check("spreadsheet" not in combined_text.lower(), "No fabricated Spreadsheet engine in Python source")
check("cohort" not in xml_source.lower(), "No fabricated Cohort view")
check("<gantt" not in xml_source.lower(), "No fabricated Gantt view")

# ---------------------------------------------------------------------------
# Tests and governance docs
# ---------------------------------------------------------------------------
test_files = sorted((ROOT / "tests").glob("test_*.py"))
test_source = "\n".join(p.read_text(encoding="utf-8") for p in test_files)
test_count = len(re.findall(r"^\s+def test_", test_source, flags=re.M))
check(test_count == 34, "Exactly 34 bounded runtime test methods", f"found={test_count}")
for tf in test_files:
    check('@tagged("post_install", "-at_install", "onehr_analytics")' in tf.read_text(encoding="utf-8"),
          f"Post-install runtime tag — {tf.name}")
for token,label in (
    ("test_13_manual_snapshot_is_created", "snapshot creation"),
    ("test_14_same_period_snapshot_is_idempotent", "snapshot idempotency"),
    ("test_21_company_rule_hides_other_company_tile", "company isolation"),
    ("test_25_literal_domain_rejects_python_expression", "domain injection defense"),
    ("test_28_branch_scope_fails_closed_without_source_branch", "branch fail-closed"),
    ("test_29_analyst_cannot_manage_tile_configuration", "analyst configuration denial"),
    ("test_34_service_contracts_remain_soft", "soft service contracts"),
):
    check(token in test_source, f"Runtime regression coverage — {label}")

required_docs = [
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md", "PROJECT_IDENTITY_PREFLIGHT.md", "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md", "SECURITY_PRIVACY_MATRIX.md", "INTEGRATION_CONTRACT.md", "ANALYTICS_PROVIDER_MATRIX.md",
    "MODEL_REGISTRY_ALIGNMENT.md", "DATABASE_IDENTIFIER_ORM_SAFETY.md", "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE.md", "IMPLEMENTATION_REPORT.md", "ROOT_GUARDRAIL_REFERENCE.md",
    "SCOPE_ISOLATION_REPORT.md", "CODEX_BOUNDED_IMPLEMENTATION_CONTRACT.md", "BOUNDED_IMPLEMENTATION_EVIDENCE.md",
]
for rel in required_docs:
    check((ROOT / "docs" / rel).is_file(), f"Governance documentation — {rel}")
guardrail = read("docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md")
for n in range(16):
    check(f"HARD GATE {n}" in guardrail, f"Enterprise Guardrail contains Hard Gate {n}")
check("DATABASE IDENTIFIER & ORM NAMING SAFETY" in guardrail, "Hard Gate 11 exact database/ORM safety title")
check("BOUNDED_IMPLEMENTATION_WORKER" in guardrail, "Codex bounded implementation worker role")
check("ATTEMPT: `1 / 2`" in guardrail, "Bounded task Attempt 1/2 documented")
check("MAX_CODEX_ATTEMPTS_PER_TASK = 2" in guardrail, "Maximum two source attempts documented")
check("MAX_REPEAT_OF_SAME_ROOT_CAUSE = 1" in guardrail, "Same root-cause repeat limit documented")
check("9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55" in read("docs/ROOT_GUARDRAIL_REFERENCE.md"),
      "Root guardrail SHA-256 reference recorded")

# Static description corrected to CE contract.
desc = read("static/description/index.html")
check("Odoo 19 Community Edition" in desc, "Static description corrected to Odoo 19 CE")
check("onehr.analytics.tile" in desc and "onehr.kpi.snapshot" in desc and "onehr.mixin.analytics" in desc,
      "Static description exact model footprint")
check("no enterprise-only spreadsheet" in desc.lower() and "fabricated" in desc.lower(), "Static description discloses non-fabricated CE capability boundary")
check((ROOT / "static/description/ICON_PRESERVATION_NOTE.txt").exists(), "Icon preservation note present")

# Junk guard
junk = [p for p in ROOT.rglob("*") if p.is_file() and (p.suffix in {".pyc", ".pyo"} or "__pycache__" in p.parts)]
if junk:
    fail("No compiled/junk Python artifacts", ", ".join(str(p.relative_to(ROOT)) for p in junk[:5]))
else:
    ok("No compiled/junk Python artifacts")

# Final non-blocking known limitations.
warn("Exact Master Model Registry ED classification is unavailable; no ED0–ED5 value is invented")
warn("Spreadsheet/Cohort/Gantt are not fabricated on Odoo 19 CE; runtime uses native Kanban/List/Form/Search/Pivot/Graph plus CSV")

print(f"SOURCE_FILES_PYTHON={len(py_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print("CUSTOM_PERSISTENT_MODELS=2")
print("CUSTOM_ABSTRACT_MODELS=1")
print("EXPLICIT_RELATION_NAMES=2")
print(f"ACL_ROWS={len(acl_rows)}")
print(f"RUNTIME_TEST_METHODS={test_count}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")
if failures:
    print("ONEHR_ANALYTICS_DIRECT_FULL_SOURCE_ACCEPTANCE=FAIL")
    sys.exit(1)
print("ONEHR_ANALYTICS_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_ANALYTICS_MOVE_FORWARD_READY=NO")
