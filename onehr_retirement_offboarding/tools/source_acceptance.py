#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
passes, warnings, failures = [], [], []


def ok(label):
    passes.append(label); print(f"PASS: {label}")


def warn(label):
    warnings.append(label); print(f"WARN: {label}")


def fail(label, details=""):
    text = f"{label}{': ' + details if details else ''}"
    failures.append(text); print(f"FAIL: {text}")


def check(condition, label, details=""):
    ok(label) if condition else fail(label, details)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


manifest = ast.literal_eval(read("__manifest__.py"))
check(manifest.get("name") == "OneHR Retirement & Offboarding", "Manifest product identity")
check(manifest.get("version") == "19.0.1.0.0", "Manifest version 19.0.1.0.0")
check(manifest.get("depends") == ["onehr_corehr", "onehr_security", "onehr_workflow_approval"], "Hard dependencies exactly CoreHR, Security, Workflow Approval")
check(manifest.get("license") == "LGPL-3", "Manifest LGPL-3")
check(manifest.get("installable") is True, "Manifest installable")
check(manifest.get("application") is False, "Addon does not duplicate OneHR root application")
for data in manifest.get("data", []):
    check((ROOT / data).is_file(), f"Manifest data exists — {data}")

readme = read("README.md")
check("Odoo 19 Community Edition" in readme, "README target Odoo 19 CE")
for model in ("onehr.offboarding", "onehr.offboarding.checklist", "onehr.clearance.item", "onehr.exit.interview"):
    check(model in readme, f"README owns model — {model}")

# Python syntax and exact model ownership.
py_files = sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)
for p in py_files:
    try:
        ast.parse(p.read_text(encoding="utf-8"), filename=str(p)); ok(f"Python syntax — {p.relative_to(ROOT)}")
    except SyntaxError as exc:
        fail(f"Python syntax — {p.relative_to(ROOT)}", str(exc))

model_files = sorted((ROOT / "models").glob("*.py"))
model_source = "\n".join(p.read_text(encoding="utf-8") for p in model_files)
custom_names = set(re.findall(r'_name\s*=\s*["\']([^"\']+)["\']', model_source))
expected = {"onehr.offboarding", "onehr.offboarding.checklist", "onehr.clearance.item", "onehr.exit.interview"}
check(custom_names == expected, "Exactly four custom persistent model names", f"found={sorted(custom_names)}")
check('_inherit = "hr.employee"' in read("models/hr_employee.py"), "Native hr.employee extension")
check('_inherit = "res.users"' in read("models/res_users.py"), "Native res.users extension")
check('_inherit = "hr.contract"' not in model_source and 'self.env["hr.contract"]' not in model_source, "No static hr.contract ownership/inheritance")
check('_inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]' in read("models/offboarding.py"), "Offboarding inherits audit + Workflow Approval contract")
for rel in ("action_helpers.py", "security_helpers.py", "clearance_item.py", "offboarding_checklist.py", "exit_interview.py", "offboarding.py", "hr_employee.py", "res_users.py"):
    check((ROOT / "models" / rel).is_file(), f"Human-friendly model module — {rel}")
check("onehr_retirement_offboarding.onehr_retirement_offboarding" not in model_source, "Tutorial model removed")
check("controllers" not in read("__init__.py"), "No controller import")
check(not (ROOT / "controllers").exists(), "Generic controller scaffold removed")
check(not (ROOT / "demo").exists(), "Generic demo scaffold removed")

# DB/ORM safety.
for ident in ("onehr_offboarding", "onehr_offboarding_checklist", "onehr_clearance_item", "onehr_exit_interview", "onehr_offboarding_checklist_attachment_rel"):
    check(len(ident.encode()) < 63, f"PostgreSQL identifier <63 bytes — {ident}")
check('"onehr_offboarding_checklist_attachment_rel"' in read("models/offboarding_checklist.py"), "Checklist attachment relation explicitly named")
check("_sql_constraints" not in model_source, "No legacy _sql_constraints")
check(model_source.count("models.Constraint(") >= 10, "Odoo 19 models.Constraint used extensively")
check("UNIQUE(offboarding_id, clearance_item_id)" in model_source, "Checklist case/item uniqueness constraint")
check("UNIQUE(offboarding_id)" in model_source, "Exit interview one-per-case constraint")
check("CHECK(sla_days >= 0)" in model_source, "Clearance SLA check constraint")

# XML hygiene.
xml_files = sorted(ROOT.rglob("*.xml")); xml_ids=[]
for p in xml_files:
    try:
        tree=ET.parse(p); ok(f"XML syntax — {p.relative_to(ROOT)}")
        for node in tree.iter():
            if node.attrib.get("id"): xml_ids.append((node.attrib["id"], str(p.relative_to(ROOT))))
    except ET.ParseError as exc:
        fail(f"XML syntax — {p.relative_to(ROOT)}", str(exc))
seen={}; dup=[]
for xid,path in xml_ids:
    if xid in seen: dup.append((xid,seen[xid],path))
    else: seen[xid]=path
check(not dup, "No duplicate XML IDs", str(dup[:5]))
xml_source="\n".join(p.read_text(encoding="utf-8") for p in xml_files)
check("<tree" not in xml_source, "No legacy tree view tag")
check("attrs=" not in xml_source, "No legacy attrs modifier")
check("states=" not in xml_source, "No legacy states modifier")
views_source="\n".join(p.read_text(encoding="utf-8") for p in (ROOT/"views").glob("*.xml"))
check('<field name="groups_id">' not in views_source, "No invalid groups_id on window-action/view definitions")
check("group_ids" in views_source, "Odoo 19 action/menu group_ids used")
for p in (ROOT/"views").glob("*.xml"):
    try:
        tree=ET.parse(p)
        bad_groups=[]; bad_labels=[]
        for search in tree.iter("search"):
            for group in search.findall(".//group"):
                if group.attrib: bad_groups.append(group.attrib)
        for label in tree.iter("label"):
            if "string" in label.attrib and "for" not in label.attrib: bad_labels.append(label.attrib)
        check(not bad_groups, f"Search group elements attribute-free — {p.name}", str(bad_groups))
        check(not bad_labels, f"Standalone labels target fields — {p.name}", str(bad_labels))
    except ET.ParseError:
        pass

# UI/UX matrix.
view_map={
    "Offboarding": read("views/offboarding_views.xml"),
    "Checklist": read("views/offboarding_checklist_views.xml"),
    "Clearance Item": read("views/clearance_item_views.xml"),
    "Exit Interview": read("views/exit_interview_views.xml"),
}
for name,src in view_map.items():
    for tag,label in (("<list", "List"),("<form", "Form"),("<search", "Search")):
        check(tag in src, f"{name} {label} view")
check("<kanban" in view_map["Offboarding"], "Offboarding executive Kanban")
check("<pivot" in view_map["Offboarding"] and "<graph" in view_map["Offboarding"], "Offboarding Pivot + Graph")
check("<kanban" in view_map["Checklist"] and "<calendar" in view_map["Checklist"], "Checklist Kanban + SLA Calendar")
check("<pivot" in view_map["Exit Interview"] and "<graph" in view_map["Exit Interview"], "Exit Interview Pivot + Graph")
for token,label in (
    ("widget=\"statusbar\"", "statusbar widgets"),
    ("oe_stat_button", "smart buttons"),
    ("action_check_readiness", "readiness body action"),
    ("action_refresh_contract_status", "contract refresh body action"),
    ("action_print_clearance_summary", "print body action"),
    ("action_submit_offboarding_approval", "approval action button"),
    ("action_generate_checklist", "checklist generation action"),
    ("action_complete", "completion action"),
    ("action_close", "closure action"),
    ("action_revoke_odoo_access", "controlled access-revoke action"),
):
    check(token in view_map["Offboarding"], f"Professional Offboarding UI — {label}")
check('name="checklist_ids"' in view_map["Offboarding"] and 'name="action_assign_to_me"' in view_map["Offboarding"] and 'name="action_reopen"' in view_map["Offboarding"], "Offboarding One2many row buttons")
check('create="0" delete="0"' in view_map["Offboarding"], "Generated checklist One2many blocks manual add/delete")
check("web_ribbon" in views_source, "Enterprise ribbons used")
check(views_source.count("<chatter") >= 4, "Chatter/activity surfaces on four persistent forms")

# Security.
groups=read("security/onehr_offboarding_groups.xml"); rules=read("security/onehr_offboarding_rules.xml")
with (ROOT/"security/ir.model.access.csv").open(newline="",encoding="utf-8") as fh:
    acls=list(csv.DictReader(fh))
check(len(acls)==11, "Exactly eleven custom-model ACL rows", f"found={len(acls)}")
check(all(row["group_id:id"] != "base.group_user" for row in acls), "No base.group_user custom-model ACL")
for gid in ("group_onehr_offboarding_task_owner", "group_onehr_offboarding_officer", "group_onehr_offboarding_manager", "group_onehr_offboarding_admin"):
    check(gid in groups, f"Security role present — {gid}")
check('model="res.groups.privilege"' in groups, "Odoo 19 res.groups.privilege security pattern")
check("onehr_security.group_onehr_security_user" in groups, "Task Owner implies OneHR security user")
check("base.group_system" not in groups and "hr.group_hr_manager" not in groups, "Offboarding groups do not imply System/HR Manager")
check(rules.count('<field name="global" eval="True"/>')==4, "Four global company boundary rules")
for model_id in ("model_onehr_offboarding", "model_onehr_offboarding_checklist", "model_onehr_clearance_item", "model_onehr_exit_interview"):
    check(model_id in rules, f"Company rule covers — {model_id}")
check("assigned_user_id" in rules and "checklist_ids.assigned_user_id" in rules, "Task-owner participation rules present")
check("require_offboarding_admin(self)" in read("models/offboarding.py") and "require_system_admin(self)" in read("models/offboarding.py"), "Odoo user revocation requires dual authority")
check("user == self.env.user" in read("models/offboarding.py"), "Self-revocation blocked")
check("onehr_offboarding_access_evidence" in read("models/res_users.py"), "res.users revocation evidence guarded")
check(".sudo(" not in model_source, "No business sudo bypass in addon models")

# Workflow/evidence guards.
off=read("models/offboarding.py"); task=read("models/offboarding_checklist.py"); interview=read("models/exit_interview.py")
for token,label in (
    ("_approval_payload", "approval payload hook"),
    ("_approval_rule_context", "approval rule-context hook"),
    ("_approval_branch_scope_key", "branch scope hook"),
    ("_approval_cancel_guard", "approval cancellation hook"),
    ("_on_approval_finalized", "approval-finalized hook"),
    ("onehr_mark_approval_executed", "approval execution evidence"),
): check(token in off, f"Workflow Approval contract — {label}")
check("Use governed Offboarding workflow actions" in off, "Direct case-state mutation blocked")
check("Governed offboarding evidence fields" in off, "High-risk case evidence direct mutation blocked")
check("Use checklist workflow actions" in task, "Direct task-state mutation blocked")
check("Checklist timestamps and actor evidence" in task, "Task actor/timestamp evidence guarded")
check("Use exit-interview workflow actions" in interview, "Direct interview-state mutation blocked")
check("Exit-interview actor/timestamp evidence" in interview, "Interview actor/timestamp evidence guarded")

# Integration ownership contracts.
for token,label in (
    ("onehr_offboarding_payroll_payload", "Payroll bridge payload"),
    ("calculate_amount\": False", "No payroll calculation ownership"),
    ("onehr_offboarding_portal_payload", "Portal service payload"),
    ("onehr_offboarding_api_payload", "API service payload"),
    ("onehr_offboarding_document_payload", "Document service payload"),
    ("onehr_offboarding_kpi_snapshot", "Analytics KPI service"),
    ("onehr_offboarding_access_revoke_payload", "SSO/access revoke payload"),
    ("self.env.registry.get(\"onehr.contract\")", "Employment Contract soft runtime resolution"),
    ("action_request_termination_review", "Contract-owned termination review delegation"),
    ("action_execute_termination", "Contract-owned termination execution delegation"),
): check(token in off, f"Integration boundary — {label}")
check('"onehr_employment_contract"' not in read("__manifest__.py"), "Employment Contract remains soft dependency")
for dep in ("onehr_document", "onehr_portal_self_service", "onehr_payroll_bridge", "onehr_analytics", "onehr_integrations_api", "onehr_multicompany_branch"):
    check(dep not in manifest.get("depends", []), f"Soft sibling not promoted to hard dependency — {dep}")

# Reports/data.
reports=read("report/offboarding_reports.xml"); templates=read("report/offboarding_report_templates.xml")
check('<field name="groups_id"' not in reports, "Odoo 19 ir.actions.report rejects legacy groups_id")
check('<field name="group_ids"' in reports, "Odoo 19 ir.actions.report uses group_ids")
check("Offboarding Clearance Summary" in reports and "report_offboarding_clearance" in templates, "Clearance Summary QWeb report")
check("Exit Interview Summary" in reports and "report_exit_interview" in templates, "Exit Interview QWeb report")
check("onehr.offboarding" in read("data/offboarding_sequence.xml"), "Offboarding sequence data")
check("_cron_remind_due_clearance" in read("data/offboarding_cron.xml"), "Daily SLA reminder cron")

# Tests.
test_files=sorted((ROOT/"tests").glob("test_*.py")); test_count=0
for p in test_files:
    src=p.read_text(encoding="utf-8")
    count=len(re.findall(r"^\s+def test_",src,re.M)); test_count += count
    check('@tagged("post_install", "-at_install", "onehr_retirement_offboarding")' in src, f"Post-install tag — {p.name}")
    check(count==10, f"Ten runtime tests — {p.name}", f"found={count}")
check(test_count==40, "Exactly forty post-install runtime test methods", f"found={test_count}")

# Hard-gate docs.
docs = {p.name: p.read_text(encoding="utf-8") for p in (ROOT/"docs").glob("*.md")}
required_docs=(
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL.md", "PROJECT_IDENTITY_PREFLIGHT.md", "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md", "SECURITY_PRIVACY_MATRIX.md", "INTEGRATION_CONTRACT.md", "CONTRACT_TERMINATION_BOUNDARY.md",
    "MODEL_REGISTRY_ALIGNMENT.md", "DATABASE_IDENTIFIER_ORM_SAFETY.md", "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "WINDOWS_RUNTIME_ACCEPTANCE.md", "IMPLEMENTATION_REPORT.md", "ROOT_GUARDRAIL_REFERENCE.md",
    "SCOPE_ISOLATION_REPORT.md", "CODEX_BOUNDED_IMPLEMENTATION_CONTRACT.md", "BOUNDED_IMPLEMENTATION_EVIDENCE.md",
    "LATEST_WORKSPACE_ALIGNMENT.md",
)
for d in required_docs: check(d in docs, f"Governance document exists — {d}")
guard=docs.get("ENTERPRISE_DEVELOPMENT_GUARDRAIL.md","")
for gate in range(16):
    marker = "HARD GATE 0" if gate == 0 else f"HARD GATE {gate}"
    check(marker in guard, f"Enterprise Development Guardrail contains {marker}")
check("DATABASE IDENTIFIER & ORM NAMING SAFETY" in guard, "Hard Gate 11 exact database/ORM title")
check("MAX_CODEX_ATTEMPTS_PER_TASK: `2`" in guard, "Codex attempt limit = 2")
check("STOP_REASON: MAX_ATTEMPTS_REACHED" in guard, "Bounded retry stop reason documented")
check("ONEHR_RETIREMENT_OFFBOARDING_MOVE_FORWARD_READY: NO" in docs.get("ENTERPRISE_COMPLETENESS_MATRIX.md", ""), "Move-forward remains NO before runtime")

warn("Exact Master Model Registry ED0–ED5 rows are not available in the searchable baseline; classification remains pending rather than invented.")
warn("Windows Odoo 19 fresh-install/runtime/security/upgrade acceptance is pending and is not inferred from source checks.")

print()
print(f"SOURCE_FILES_PYTHON={len(py_files)}")
print(f"SOURCE_FILES_XML={len(xml_files)}")
print("CUSTOM_PERSISTENT_MODELS=4")
print("NATIVE_MODEL_EXTENSIONS=2")
print("ACL_ROWS=11")
print(f"RUNTIME_TEST_METHODS={test_count}")
print(f"SOURCE_ACCEPTANCE_PASS_COUNT={len(passes)}")
print(f"SOURCE_ACCEPTANCE_WARN_COUNT={len(warnings)}")
print(f"SOURCE_ACCEPTANCE_FAIL_COUNT={len(failures)}")
if failures:
    print("ONEHR_RETIREMENT_OFFBOARDING_DIRECT_FULL_SOURCE_ACCEPTANCE=FAIL")
    print("SOURCE_ENTERPRISE_COMPLETENESS=FAIL")
    sys.exit(1)
print("ONEHR_RETIREMENT_OFFBOARDING_DIRECT_FULL_SOURCE_ACCEPTANCE=PASS")
print("SOURCE_ENTERPRISE_COMPLETENESS=PASS_FOR_RUNTIME")
print("REGISTRY_ED_CLASSIFICATION=PENDING_EXACT_REGISTRY_ROW_VERIFICATION")
print("WINDOWS_RUNTIME_ACCEPTANCE=PENDING")
print("ONEHR_RETIREMENT_OFFBOARDING_MOVE_FORWARD_READY=NO")
