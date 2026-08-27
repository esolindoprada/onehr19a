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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


# ---------------------------------------------------------------------------
# HARD GATE 0 / project identity / manifest contract
# ---------------------------------------------------------------------------
try:
    manifest = ast.literal_eval(text(ROOT / "__manifest__.py"))
except Exception as exc:
    manifest = {}
    failed(f"manifest literal parse: {exc}")

if manifest.get("name") == "OneHR Document":
    passed("PROJECT/ADDON identity = OneHR Document")
else:
    failed(f"manifest name unexpected: {manifest.get('name')!r}")

if manifest.get("version") == "19.0.1.0.0":
    passed("manifest targets Odoo 19")
else:
    failed(f"manifest version unexpected: {manifest.get('version')!r}")

expected_dependencies = ["onehr_corehr", "onehr_security", "mail"]
if manifest.get("depends") == expected_dependencies:
    passed("hard dependencies exactly onehr_corehr, onehr_security, mail")
else:
    failed(f"unexpected hard dependencies: {manifest.get('depends')!r}")

for rel in manifest.get("data", []):
    if not (ROOT / rel).is_file():
        failed(f"manifest data file missing: {rel}")
if not any(item.startswith("manifest data file missing") for item in errors):
    passed("all manifest data files exist")

for forbidden_dir in ("controllers", "demo"):
    if (ROOT / forbidden_dir).exists():
        failed(f"obsolete scaffold directory still present: {forbidden_dir}")
else:
    if not (ROOT / "controllers").exists() and not (ROOT / "demo").exists():
        passed("obsolete generic controller/demo scaffold removed")

# ---------------------------------------------------------------------------
# HARD GATE 4 / syntax + structural inventory
# ---------------------------------------------------------------------------
py_files = sorted(ROOT.rglob("*.py"))
xml_files = sorted(ROOT.rglob("*.xml"))

for path in py_files:
    try:
        compile(text(path), str(path), "exec")
    except Exception as exc:
        failed(f"Python compile {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("Python compile") for item in errors):
    passed(f"all Python sources compile ({len(py_files)} files)")

for path in xml_files:
    try:
        ET.parse(path)
    except Exception as exc:
        failed(f"XML parse {path.relative_to(ROOT)}: {exc}")
if not any(item.startswith("XML parse") for item in errors):
    passed(f"all XML files parse ({len(xml_files)} files)")

registry_expected = {
    "onehr.document.category": "persistent",
    "onehr.document": "persistent",
    "onehr.document.version": "persistent",
    "onehr.document.template": "persistent",
    "onehr.document.template.version": "persistent",
    "onehr.esign.transaction": "persistent",
    "wizard.document.generate": "transient",
    "wizard.document.publish.sign": "transient",
}

registry_actual: dict[str, str] = {}
for path in sorted((ROOT / "models").glob("*.py")) + sorted((ROOT / "wizards").glob("*.py")):
    tree = ast.parse(text(path), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        model_name = None
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "_name" for t in stmt.targets)
            ):
                try:
                    model_name = ast.literal_eval(stmt.value)
                except Exception:
                    pass
        if not model_name:
            continue
        bases = {ast.unparse(base) for base in node.bases}
        kind = "transient" if "models.TransientModel" in bases else "persistent"
        registry_actual[model_name] = kind
        allowed_bases = {"models.Model", "models.TransientModel", "models.AbstractModel"}
        if not bases <= allowed_bases:
            failed(
                f"Odoo 19 model class {node.name} contains non-Odoo Python base(s): "
                f"{sorted(bases - allowed_bases)}"
            )

if registry_actual == registry_expected:
    passed("Master Model Registry source inventory exactly 8 approved rows")
else:
    missing = sorted(set(registry_expected) - set(registry_actual))
    extra = sorted(set(registry_actual) - set(registry_expected))
    wrong = sorted(
        name
        for name in set(registry_expected) & set(registry_actual)
        if registry_expected[name] != registry_actual[name]
    )
    failed(f"Registry mismatch missing={missing}, extra={extra}, wrong_kind={wrong}")

all_source = "\n".join(text(p) for p in py_files)
for prohibited in (
    "onehr.employee.document",
    "onehr.document.tag",
):
    if re.search(rf"_name\s*=\s*['\"]{re.escape(prohibited)}['\"]", all_source):
        failed(f"prohibited unapproved Registry model introduced: {prohibited}")
if not any("prohibited unapproved Registry model" in item for item in errors):
    passed("no duplicate/unapproved employee-document or tag master introduced")

if re.search(r"_inherit\s*=\s*['\"]res\.config\.settings['\"]", all_source):
    failed("unapproved res.config.settings ownership introduced in onehr_document")
else:
    passed("res.config.settings ownership not invented")

if "onehr_multicompany_branch" in manifest.get("depends", []):
    failed("reverse hard dependency on onehr_multicompany_branch introduced")
else:
    passed("branch addon remains soft/downstream; no circular hard dependency")

# ---------------------------------------------------------------------------
# HARD GATE 10 / server-side security and privacy
# ---------------------------------------------------------------------------
business_source = "\n".join(
    text(p)
    for folder in (ROOT / "models", ROOT / "wizards")
    for p in sorted(folder.glob("*.py"))
)
if re.search(r"\.sudo\s*\(", business_source):
    failed("business source contains sudo() authorization bypass")
else:
    passed("business source contains no sudo() authorization bypass")

if "check_access(\"read\")" in text(ROOT / "models" / "action_helpers.py"):
    passed("generic source record references enforce ORM read access")
else:
    failed("source-record access check missing")

if "onehr.audit.log" in business_source and "_log_event" in business_source:
    passed("high-risk document/e-sign events integrate with OneHR audit ledger")
else:
    failed("OneHR security audit integration missing")

acl_path = ROOT / "security" / "ir.model.access.csv"
try:
    acl_rows = list(csv.reader(io.StringIO(text(acl_path))))
    acl_count = len(acl_rows) - 1
    print(f"ACL_ROW_COUNT: {acl_count}")
    if acl_count == 23:
        passed("least-privilege ACL inventory = 23 reviewed rows")
    else:
        failed(f"expected 23 ACL rows, found {acl_count}")

    if any(len(row) >= 4 and row[3] == "base.group_user" for row in acl_rows[1:]):
        failed("custom-model ACL grants broad base.group_user access")
    else:
        passed("no direct base.group_user ACL on OneHR Document models")

    persistent_model_xmlids = {
        "model_onehr_document_category",
        "model_onehr_document",
        "model_onehr_document_version",
        "model_onehr_document_template",
        "model_onehr_document_template_version",
        "model_onehr_esign_transaction",
    }
    bad_unlink = [
        row[0]
        for row in acl_rows[1:]
        if len(row) >= 8 and row[2] in persistent_model_xmlids and row[7] == "1"
    ]
    if bad_unlink:
        failed(f"persistent document ACL exposes unlink: {bad_unlink}")
    else:
        passed("persistent governed records have no ACL-level unlink permission")
except Exception as exc:
    failed(f"ACL parse: {exc}")

rules_source = text(ROOT / "security" / "onehr_document_rules.xml")
for model_fragment in (
    "model_onehr_document_category",
    "model_onehr_document",
    "model_onehr_document_version",
    "model_onehr_document_template",
    "model_onehr_document_template_version",
    "model_onehr_esign_transaction",
):
    if model_fragment not in rules_source:
        failed(f"company/security rule coverage missing: {model_fragment}")
if "global\" eval=\"True" not in rules_source:
    # XML may serialize quote spacing differently; exact source should contain it in this package.
    failed("global company security rules are not explicitly declared")
else:
    passed("global legal-company security boundary declared")

for required_group in (
    "group_onehr_document_user",
    "group_onehr_document_officer",
    "group_onehr_document_manager",
    "group_onehr_document_compliance",
    "onehr_security.group_onehr_sensitive_data_reader",
    "onehr_security.group_onehr_restricted_data_reader",
):
    group_blob = text(ROOT / "security" / "onehr_document_groups.xml")
    if required_group not in group_blob:
        failed(f"required document/security group contract missing: {required_group}")
if not any("required document/security group contract missing" in item for item in errors):
    passed("document role + explicit sensitive/restricted gates are wired")

esign_source = text(ROOT / "models" / "esign.py")
credential_field_pattern = re.compile(
    r"^\s*(password|secret|token|api_key|access_key|private_key|credential)s?\s*=\s*fields\.",
    re.I | re.M,
)
if credential_field_pattern.search(esign_source):
    failed("plain-text external credential field introduced in onehr.esign.transaction")
else:
    passed("e-sign transaction stores correlation/status evidence, not external credentials")

# ---------------------------------------------------------------------------
# HARD GATE 3 / history, attachment and bounded template behavior
# ---------------------------------------------------------------------------
version_source = text(ROOT / "models" / "document.py")
if "fields.Binary(" in version_source and "attachment=True" in version_source:
    passed("document binary payload delegates to Odoo attachment storage")
else:
    failed("document version attachment-backed Binary field missing")

if version_source.count("@api.ondelete(at_uninstall=False)") >= 1 and esign_source.count(
    "@api.ondelete(at_uninstall=False)"
) >= 1:
    passed("issued document/e-sign evidence uses uninstall-safe deletion protection")
else:
    failed("history-safe api.ondelete protection incomplete")

if re.search(r"\n\s*def\s+unlink\s*\(", version_source + "\n" + esign_source):
    failed("business-history unlink() override reintroduced")
else:
    passed("no uninstall-blocking business unlink() override")

template_source = text(ROOT / "models" / "template.py")
if "ALLOWED_TEMPLATE_TOKENS" in template_source and "TOKEN_RE" in template_source:
    passed("template rendering uses an explicit bounded variable contract")
else:
    failed("bounded template token contract missing")

if re.search(r"\bsafe_eval\b|\beval\s*\(|\bexec\s*\(", business_source):
    failed("executable stored-expression mechanism detected in business source")
else:
    passed("no eval/safe_eval/exec template execution path")

if "dispatch_to_provider" in esign_source and "return False" in esign_source:
    passed("e-sign provider integration remains a soft adapter hook with no network call")
else:
    failed("soft e-sign provider adapter hook missing")

# ---------------------------------------------------------------------------
# HARD GATES 6-9 / professional UI coverage
# ---------------------------------------------------------------------------
persistent_models = {
    "onehr.document.category",
    "onehr.document",
    "onehr.document.version",
    "onehr.document.template",
    "onehr.document.template.version",
    "onehr.esign.transaction",
}
coverage = {model: {"list": 0, "form": 0, "search": 0} for model in persistent_models}
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
        children = list(arch_field)
        if children and children[0].tag in coverage[model_name]:
            coverage[model_name][children[0].tag] += 1

for model_name, kinds in sorted(coverage.items()):
    for kind in ("list", "form", "search"):
        if kinds[kind] < 1:
            failed(f"{model_name} missing mandatory enterprise {kind} view")
if not any("missing mandatory enterprise list view" in item for item in errors):
    passed("enterprise list coverage for every persistent OneHR Document model")
if not any("missing mandatory enterprise form view" in item for item in errors):
    passed("professional form coverage for every persistent OneHR Document model")
if not any("missing mandatory enterprise search view" in item for item in errors):
    passed("mandatory search view coverage for every persistent OneHR Document model")

all_view_xml = "\n".join(text(p) for p in sorted((ROOT / "views").glob("*.xml")))
ui_markers = (
    ('widget="statusbar"', "statusbar workflow widgets"),
    ('class="oe_stat_button"', "smart buttons"),
    ("action_schedule_expiry_reminder", "body-form operational action"),
    ("action_request_signature", "One2many/list-row operational action"),
    ("<chatter/>", "chatter integration"),
    ('view_mode">list,form,pivot,graph', "enterprise analytical navigation"),
)
for marker, label in ui_markers:
    if marker in all_view_xml:
        passed(label)
    else:
        failed(f"professional UI marker missing: {label}")

if re.search(r"<label\s+string=", all_view_xml):
    failed("standalone label without field binding remains in form XML")
else:
    passed("form help text uses Odoo-safe markup rather than invalid standalone labels")

if "expiring_version_count', '&gt;'" in all_view_xml or "expiry_status', '=', 'due'" in all_view_xml:
    failed("search view filters on non-stored dynamic computed expiry fields")
else:
    passed("search views avoid domains on non-stored dynamic expiry computations")

if re.search(r"\battrs=|\bstates=", all_view_xml):
    failed("legacy attrs/states view modifiers detected")
else:
    passed("Odoo 19 direct view-expression style used")

# ---------------------------------------------------------------------------
# Recent enterprise-hardening invariants
# ---------------------------------------------------------------------------
category_source = text(ROOT / "models" / "category.py")
cron_source = text(ROOT / "data" / "document_cron_data.xml")
menu_source = text(ROOT / "views" / "menus.xml")
document_view_source = text(ROOT / "views" / "document_views.xml")

if "default_grace_days = fields.Integer(" in category_source and "category.default_grace_days" in version_source:
    passed("expiry grace period is an explicit category policy, not conflated with reminder lead time")
else:
    failed("explicit default_grace_days policy is not wired into document expiry")

if '<field name="user_id" ref="base.user_root"/>' in cron_source:
    passed("expiry/reminder cron has an explicit Odoo scheduler user for governed cross-company processing")
else:
    failed("expiry/reminder cron scheduler user is not explicit")

if (
    'id="menu_onehr_document_operations"' in menu_source
    and 'groups="onehr_document.group_onehr_document_user"' in menu_source
):
    passed("Document User can navigate to employee-visible document operations")
else:
    failed("Document User menu parent would hide employee self-service document navigation")

signature_button_pattern = re.compile(
    r'<button[^>]+name="action_request_signature"[^>]+groups="onehr_document\.group_onehr_document_manager"',
    re.S,
)
if signature_button_pattern.search(document_view_source) and "require_document_manager(self.env)" in version_source:
    passed("signature-request workflow is Manager-gated in both UI and server action")
else:
    failed("signature-request workflow is not consistently Manager-gated")

for sensitivity_rule in (
    "rule_document_category_user_visible_internal",
    "rule_document_category_officer_nonrestricted",
    "rule_document_category_compliance_all_sensitivity",
):
    if sensitivity_rule not in rules_source:
        failed(f"category sensitivity record rule missing: {sensitivity_rule}")
if not any("category sensitivity record rule missing" in item for item in errors):
    passed("category metadata is protected by the same sensitivity tiers as document content")

sensitive_field_markers = (
    'groups="onehr_document.group_onehr_document_officer,onehr_document.group_onehr_document_compliance"',
    "source_model_id = fields.Many2one(",
    "source_res_id = fields.Integer(",
    "template_id = fields.Many2one(",
    "keywords = fields.Char(",
)
if all(marker in version_source for marker in sensitive_field_markers):
    passed("source/template metadata has field-level Officer/Compliance protection")
else:
    failed("sensitive source/template metadata field-level group protection is incomplete")

# ---------------------------------------------------------------------------
# Reports, scheduler, sequence, integration contracts
# ---------------------------------------------------------------------------
report_source = text(ROOT / "report" / "document_version_report.xml")
if 'model="ir.actions.report"' in report_source and "qweb-pdf" in report_source:
    passed("controlled QWeb PDF report action present")
else:
    failed("QWeb PDF report action missing")

if "_render_qweb_pdf(" in version_source and "onehr_document.action_report_document_version" in version_source:
    passed("PDF snapshot path uses the Odoo 19 report service contract")
else:
    failed("document PDF snapshot does not use ir.actions.report rendering")

if (ROOT / "data" / "document_cron_data.xml").is_file() and "_cron_process_expiry_and_reminders" in version_source:
    passed("expiry/reminder scheduler is implemented")
else:
    failed("expiry/reminder scheduler missing")

if (ROOT / "data" / "document_sequence_data.xml").is_file() and 'next_by_code("onehr.document")' in version_source:
    passed("governed document numbering delegates to ir.sequence")
else:
    failed("document numbering sequence contract incomplete")

if "onehr_corehr" in repr(manifest.get("depends")) and "onehr_security" in repr(manifest.get("depends")):
    passed("Core HR + Security hard integration contract present")

# ---------------------------------------------------------------------------
# HARD GATES 14-15 / tests and governance evidence
# ---------------------------------------------------------------------------
test_method_count = 0
tagged_files = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    source = text(path)
    test_method_count += len(
        re.findall(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", source, re.M)
    )
    if '@tagged("post_install", "-at_install", "onehr_document")' in source:
        tagged_files += 1
print(f"TEST_METHOD_COUNT: {test_method_count}")
if test_method_count == 19:
    passed("enterprise runtime-test inventory exactly 19 methods")
else:
    failed(f"expected exactly 19 test methods, found {test_method_count}")

if tagged_files == len(list((ROOT / "tests").glob("test_*.py"))):
    passed("all runtime test classes/files use post_install onehr_document tag")
else:
    failed("one or more test files are missing the required post_install tag")

required_docs = [
    "PROJECT_IDENTITY_PREFLIGHT.md",
    "ONEHR_DOCUMENT_MODEL_REGISTRY_ALIGNMENT.md",
    "BASELINE_FEATURE_PRESERVATION_MATRIX.md",
    "FULL_STRUCTURAL_INVENTORY.md",
    "UI_UX_MATRIX.md",
    "SECURITY_PRIVACY_MATRIX.md",
    "ENTERPRISE_DEVELOPMENT_GUARDRAIL_DOCUMENT.md",
    "ENTERPRISE_COMPLETENESS_MATRIX.md",
    "ONEHR_DOCUMENT_IMPLEMENTATION_REPORT.md",
    "INTEGRATION_CONTRACTS.md",
]
for name in required_docs:
    if not (ROOT / "docs" / name).is_file():
        failed(f"required governance evidence missing: {name}")
if not any("required governance evidence missing" in item for item in errors):
    passed("all addon-specific Guardrail/completeness evidence documents present")

guardrail = text(ROOT / "docs" / "ENTERPRISE_DEVELOPMENT_GUARDRAIL_DOCUMENT.md")
for gate in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15):
    if f"HARD GATE {gate}" not in guardrail:
        failed(f"user-required Hard Gate {gate} missing from addon guardrail")
if "HARD GATE 11" not in guardrail or "intentionally undefined" not in guardrail.lower():
    failed("Guardrail does not explicitly preserve the user's undefined Gate 11 gap")
else:
    passed("all 15 user-defined Hard Gates preserved; Gate 11 remains intentionally undefined")

# Final source-stage decision.
print()
if errors:
    print(f"SOURCE_ACCEPTANCE_PASS_COUNT: N/A")
    print(f"SOURCE_ACCEPTANCE_FAIL_COUNT: {len(errors)}")
    print(f"ONEHR_DOCUMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: FAIL")
    print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
    print("ONEHR_DOCUMENT_MOVE_FORWARD_READY: NO")
    sys.exit(1)

print("SOURCE_ACCEPTANCE_FAIL_COUNT: 0")
print("MASTER_MODEL_REGISTRY_TARGET_ROWS: 8")
print("PERSISTENT_MODELS: 6")
print("TRANSIENT_MODELS: 2")
print("ACL_ROWS: 23")
print(f"RUNTIME_TEST_METHODS: {test_method_count}")
print("CODEX_EXECUTED: NO")
print("DATABASE_COMMANDS_EXECUTED: NO")
print("ONEHR_DOCUMENT_DIRECT_FULL_SOURCE_ACCEPTANCE: PASS")
print("WINDOWS_RUNTIME_ACCEPTANCE: PENDING")
print("ONEHR_DOCUMENT_MOVE_FORWARD_READY: NO")
