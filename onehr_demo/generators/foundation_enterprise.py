
"""MASTER PROMPT 05 — deterministic legal-company, branch and organization foundation.

The selected scenario company remains the canonical Odoo legal company. This generator
does not create a parallel legal-company master and never uses production sequences as
identity. Branches and departments use stable deterministic business codes plus the
central demo provenance registry.
"""

from datetime import timedelta

from odoo import _, fields
from odoo.exceptions import AccessError, ValidationError

from ..services.deterministic import stable_identifier

GENERATOR_KEY = "foundation.enterprise"
RESET_POLICY = "REUSE_ON_REBUILD"

_PROFILE_RANK = {"quick": 1, "standard": 2, "full": 3}

BRANCH_CATALOG = (
    {"token": "hq_jakarta", "name": "Kantor Pusat Jakarta", "branch_type": "head_office", "parent": None, "rank": 1},
    {"token": "bali", "name": "Cabang Bali", "branch_type": "operational", "parent": "hq_jakarta", "rank": 1},
    {"token": "bandung", "name": "Cabang Bandung", "branch_type": "operational", "parent": "hq_jakarta", "rank": 2},
    {"token": "surabaya", "name": "Cabang Surabaya", "branch_type": "operational", "parent": "hq_jakarta", "rank": 2},
    {"token": "medan", "name": "Cabang Medan", "branch_type": "operational", "parent": "hq_jakarta", "rank": 3},
    {"token": "makassar", "name": "Cabang Makassar", "branch_type": "operational", "parent": "hq_jakarta", "rank": 3},
)

DEPARTMENT_CATALOG = (
    {"token": "corp", "name": "Corporate Services", "unit_type": "division", "parent": None, "rank": 1},
    {"token": "hr", "name": "Human Resources", "unit_type": "department", "parent": "corp", "rank": 1},
    {"token": "finance", "name": "Finance & Accounting", "unit_type": "department", "parent": "corp", "rank": 1},
    {"token": "operations", "name": "Operations", "unit_type": "division", "parent": None, "rank": 1},
    {"token": "operations_delivery", "name": "Operations Delivery", "unit_type": "department", "parent": "operations", "rank": 1},
    {"token": "technology", "name": "Technology", "unit_type": "division", "parent": None, "rank": 1},
    {"token": "it", "name": "Information Technology", "unit_type": "department", "parent": "technology", "rank": 1},
    {"token": "commercial", "name": "Commercial", "unit_type": "division", "parent": None, "rank": 2},
    {"token": "sales", "name": "Sales", "unit_type": "department", "parent": "commercial", "rank": 2},
    {"token": "marketing", "name": "Marketing", "unit_type": "department", "parent": "commercial", "rank": 2},
    {"token": "procurement", "name": "Procurement", "unit_type": "department", "parent": "operations", "rank": 3},
    {"token": "learning", "name": "Learning & Development", "unit_type": "team", "parent": "hr", "rank": 2},
    {"token": "talent", "name": "Talent & Succession", "unit_type": "team", "parent": "hr", "rank": 3},
    {"token": "data", "name": "Data & Analytics", "unit_type": "team", "parent": "technology", "rank": 2},
    {"token": "customer_experience", "name": "Customer Experience", "unit_type": "department", "parent": "commercial", "rank": 3},
    {"token": "internal_audit", "name": "Internal Audit", "unit_type": "department", "parent": "corp", "rank": 3},
)


def _profile_rows(catalog, profile):
    rank = _PROFILE_RANK.get(profile)
    if rank is None:
        raise ValidationError(_("Unsupported OneHR Demo dataset profile: %s") % profile)
    return [dict(row) for row in catalog if row["rank"] <= rank]


def expected_foundation_shape(profile):
    """Return deterministic MP05 profile counts for UI/tests/evidence."""
    return {
        "company": 1,
        "branches": len(_profile_rows(BRANCH_CATALOG, profile)),
        "departments": len(_profile_rows(DEPARTMENT_CATALOG, profile)),
    }


def _branch_code(scenario, token):
    return stable_identifier("DMB", f"{scenario.code}.branch.{token}", max_length=40)


def _department_code(scenario, token):
    return stable_identifier("DORG", f"{scenario.code}.department.{token}", max_length=48)


def _reference_key(scenario, entity, token):
    return scenario.deterministic_key(
        "enterprise" if entity in {"company", "branch"} else "organization",
        entity,
        token,
    )


def _existing_target_from_reference(scenario, stable_key, expected_model):
    Reference = scenario.env["onehr.demo.reference"]
    reference = Reference.search([
        ("scenario_id", "=", scenario.id),
        ("stable_key", "=", stable_key),
    ], limit=1)
    if not reference:
        return reference, scenario.env[expected_model].browse()
    if reference.target_model != expected_model:
        raise ValidationError(
            _("Deterministic key %(key)s points to %(actual)s; expected %(expected)s.")
            % {"key": stable_key, "actual": reference.target_model, "expected": expected_model}
        )
    target = scenario.env[expected_model].browse(reference.target_res_id).exists()
    if not target:
        raise ValidationError(
            _("Deterministic provenance %(key)s points to a missing %(model)s/%(res_id)s record. "
              "Do not silently remap provenance; reconcile the demo baseline first.")
            % {
                "key": stable_key,
                "model": expected_model,
                "res_id": reference.target_res_id,
            }
        )
    return reference, target


def _exact_or_error(Model, domain, label):
    # Include archived records in deterministic collision detection. Missing an
    # archived match would convert a known identity conflict into a duplicate-create
    # failure later in the same path.
    records = Model.with_context(active_test=False).search(domain, order="id")
    if len(records) > 1:
        raise ValidationError(
            _("Deterministic MP05 business key is ambiguous for %(label)s: %(count)s records match.")
            % {"label": label, "count": len(records)}
        )
    return records[:1]


def readiness_blockers_foundation_enterprise(scenario):
    """Audit all MP05 operator/data preconditions before any create occurs."""
    blockers = []
    env = scenario.env
    company = scenario.company_id

    if company not in env.user.company_ids:
        blockers.append(
            _("Scenario company %(company)s is outside the current operator's allowed companies.")
            % {"company": company.display_name}
        )

    if not company.onehr_branch_enabled:
        blockers.append(
            _("Scenario company %(company)s has OneHR Branch Scope disabled. Enable it before MP05 generation; "
              "the demo generator will not silently mutate legal-company security configuration.")
            % {"company": company.display_name}
        )

    branch_authorized = (
        env.user.has_group("base.group_system")
        or env.user.has_group("onehr_multicompany_branch.group_onehr_branch_admin")
    )
    if not branch_authorized:
        blockers.append(
            _("MP05 requires either Odoo Settings/System Administrator authority or OneHR Branch Admin authority.")
        )

    access_requirements = {
        "res.company": ("read",),
        "onehr.branch": ("read", "create"),
        "hr.department": ("read", "create"),
    }
    for model_name, operations in access_requirements.items():
        Model = env[model_name]
        for operation in operations:
            try:
                Model.check_access(operation)
            except AccessError as exc:
                blockers.append(
                    _("%(model)s %(operation)s authority is missing: %(detail)s")
                    % {"model": model_name, "operation": operation, "detail": str(exc)}
                )

    # Exercise the same company-scoped read surfaces the generator will use.
    try:
        env["onehr.branch"].search_count([("company_id", "=", company.id)], limit=1)
    except AccessError as exc:
        blockers.append(_("OneHR Branch company-scope read is blocked: %s") % str(exc))
    try:
        env["hr.department"].search_count([("company_id", "=", company.id)], limit=1)
    except AccessError as exc:
        blockers.append(_("HR Department company-scope read is blocked: %s") % str(exc))

    return blockers


def _assert_branch_matches(branch, *, company, code, name, branch_type, parent, valid_from):
    expected_parent_id = parent.id if parent else False
    mismatches = []
    if branch.company_id != company:
        mismatches.append("company")
    if branch.code != code:
        mismatches.append("code")
    if branch.name != name:
        mismatches.append("name")
    if branch.branch_type != branch_type:
        mismatches.append("branch_type")
    if branch.parent_id.id != expected_parent_id:
        mismatches.append("parent")
    if branch.valid_from != valid_from:
        mismatches.append("valid_from")
    if branch.valid_to:
        mismatches.append("valid_to")
    if not branch.active:
        mismatches.append("active")
    if mismatches:
        raise ValidationError(
            _("Existing deterministic branch %(code)s conflicts with the frozen MP05 contract: %(fields)s. "
              "The generator will not rewrite an ambiguous/effective-dated master.")
            % {"code": code, "fields": ", ".join(mismatches)}
        )


def _assert_department_matches(department, *, company, code, name, unit_type, parent, valid_from):
    expected_parent_id = parent.id if parent else False
    mismatches = []
    if department.company_id != company:
        mismatches.append("company")
    if department.onehr_code != code:
        mismatches.append("onehr_code")
    if department.name != name:
        mismatches.append("name")
    if department.onehr_unit_type != unit_type:
        mismatches.append("onehr_unit_type")
    if department.parent_id.id != expected_parent_id:
        mismatches.append("parent")
    if department.onehr_valid_from != valid_from:
        mismatches.append("onehr_valid_from")
    if department.onehr_valid_to:
        mismatches.append("onehr_valid_to")
    if not department.active:
        mismatches.append("active")
    if mismatches:
        raise ValidationError(
            _("Existing deterministic organization %(code)s conflicts with the frozen MP05 contract: %(fields)s.")
            % {"code": code, "fields": ", ".join(mismatches)}
        )


def _register_reference(scenario, run, stable_key, target, disposition):
    return scenario.env["onehr.demo.reference"].register_reference(
        scenario=scenario,
        generator_key=GENERATOR_KEY,
        stable_key=stable_key,
        target=target,
        run=run,
        disposition=disposition,
        reset_policy=RESET_POLICY,
    )


def generate_foundation_enterprise(scenario, run):
    """Create/reuse the selected legal-company foundation atomically."""
    company = scenario.company_id
    valid_from = fields.Date.to_date(scenario.reference_date) - timedelta(days=730)
    counters = {"created": 0, "reused": 0, "updated": 0, "skipped": 0, "protected": 0}

    if not company.onehr_branch_enabled:
        # Readiness is required to catch this before the savepoint, but retain a
        # defensive server-side gate so direct calls cannot silently change policy.
        raise ValidationError(
            _("OneHR Branch Scope is disabled for the scenario company. MP05 does not silently enable it.")
        )

    company_key = _reference_key(scenario, "company", "selected")
    _, referenced_company = _existing_target_from_reference(scenario, company_key, "res.company")
    if referenced_company and referenced_company != company:
        raise ValidationError(
            _("The selected legal-company provenance no longer matches the scenario company.")
        )
    _register_reference(scenario, run, company_key, company, "reused")
    counters["reused"] += 1

    Branch = scenario.env["onehr.branch"]
    branches = {}
    for spec in _profile_rows(BRANCH_CATALOG, scenario.profile):
        parent = branches.get(spec["parent"]) if spec["parent"] else Branch.browse()
        code = _branch_code(scenario, spec["token"])
        stable_key = _reference_key(scenario, "branch", spec["token"])
        reference, branch = _existing_target_from_reference(scenario, stable_key, "onehr.branch")

        if not branch:
            branch = _exact_or_error(
                Branch,
                [("company_id", "=", company.id), ("code", "=", code)],
                f"onehr.branch {code}",
            )

        if branch:
            _assert_branch_matches(
                branch,
                company=company,
                code=code,
                name=spec["name"],
                branch_type=spec["branch_type"],
                parent=parent,
                valid_from=valid_from,
            )
            disposition = "reused"
            counters["reused"] += 1
        else:
            branch = Branch.create({
                "code": code,
                "name": spec["name"],
                "company_id": company.id,
                "branch_type": spec["branch_type"],
                "parent_id": parent.id or False,
                "active": True,
                "valid_from": valid_from,
                "valid_to": False,
                "notes": "Synthetic OneHR Enterprise Demo master. No real employee/customer PII.",
            })
            disposition = "created"
            counters["created"] += 1

        _register_reference(scenario, run, stable_key, branch, disposition)
        branches[spec["token"]] = branch

    Department = scenario.env["hr.department"]
    department_result = _ensure_profile_departments(scenario, run, counters)
    counters.update(department_result)

    return counters


def _ensure_profile_departments(scenario, run, counters=None):
    """Ensure the frozen MP05 department provenance required by downstream consumers.

    This is deliberately the same deterministic producer used by MP05 itself. It
    exists so an already-PASSed MP05 checkpoint can safely reconcile a missing
    prerequisite introduced by an earlier bounded source version without rerunning
    or duplicating the entire foundation dataset. No mutable production sequence is
    consulted and every created/reused department receives foundation provenance.
    """
    company = scenario.company_id
    valid_from = fields.Date.to_date(scenario.reference_date) - timedelta(days=730)
    Department = scenario.env["hr.department"]
    departments = {}
    local = {"created": 0, "reused": 0, "updated": 0, "skipped": 0, "protected": 0}
    for spec in _profile_rows(DEPARTMENT_CATALOG, scenario.profile):
        parent = departments.get(spec["parent"]) if spec["parent"] else Department.browse()
        code = _department_code(scenario, spec["token"])
        stable_key = _reference_key(scenario, "department", spec["token"])
        reference, department = _existing_target_from_reference(scenario, stable_key, "hr.department")
        if not department:
            department = _exact_or_error(
                Department,
                [("company_id", "=", company.id), ("onehr_code", "=", code)],
                f"hr.department {code}",
            )
        if department:
            _assert_department_matches(
                department, company=company, code=code, name=spec["name"],
                unit_type=spec["unit_type"], parent=parent, valid_from=valid_from,
            )
            disposition = "reused"
            local["reused"] += 1
        else:
            department = Department.create({
                "name": spec["name"], "company_id": company.id,
                "parent_id": parent.id or False, "active": True,
                "onehr_code": code, "onehr_unit_type": spec["unit_type"],
                "onehr_valid_from": valid_from, "onehr_valid_to": False,
            })
            disposition = "created"
            local["created"] += 1
        _register_reference(scenario, run, stable_key, department, disposition)
        departments[spec["token"]] = department
    return local

    return counters


def validate_foundation_enterprise(scenario, run=None):
    """Validate MP05 semantics from real records/provenance, not from counts alone."""
    company = scenario.company_id
    reference_date = fields.Date.to_date(scenario.reference_date)
    valid_from = reference_date - timedelta(days=730)
    expected_branches = _profile_rows(BRANCH_CATALOG, scenario.profile)
    expected_departments = _profile_rows(DEPARTMENT_CATALOG, scenario.profile)

    expected_keys = {_reference_key(scenario, "company", "selected")}
    expected_keys.update(_reference_key(scenario, "branch", row["token"]) for row in expected_branches)
    expected_keys.update(_reference_key(scenario, "department", row["token"]) for row in expected_departments)

    Reference = scenario.env["onehr.demo.reference"]
    references = Reference.search([
        ("scenario_id", "=", scenario.id),
        ("generator_key", "=", GENERATOR_KEY),
        ("state", "=", "active"),
    ])
    actual_keys = set(references.mapped("stable_key"))
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValidationError(
            _("MP05 provenance set does not match the selected profile. Missing=%(missing)s Extra=%(extra)s")
            % {"missing": missing, "extra": extra}
        )

    company_ref = references.filtered(
        lambda row: row.stable_key == _reference_key(scenario, "company", "selected")
    )
    if len(company_ref) != 1 or company_ref.target_model != "res.company" or company_ref.target_res_id != company.id:
        raise ValidationError(_("MP05 legal-company provenance is invalid."))

    branches = {}
    for spec in expected_branches:
        stable_key = _reference_key(scenario, "branch", spec["token"])
        ref = references.filtered(lambda row, key=stable_key: row.stable_key == key)
        if len(ref) != 1 or ref.target_model != "onehr.branch":
            raise ValidationError(_("MP05 branch provenance missing or invalid: %s") % stable_key)
        branch = scenario.env["onehr.branch"].browse(ref.target_res_id).exists()
        if not branch:
            raise ValidationError(_("MP05 branch target no longer exists: %s") % stable_key)
        parent = branches.get(spec["parent"]) if spec["parent"] else scenario.env["onehr.branch"].browse()
        _assert_branch_matches(
            branch,
            company=company,
            code=_branch_code(scenario, spec["token"]),
            name=spec["name"],
            branch_type=spec["branch_type"],
            parent=parent,
            valid_from=valid_from,
        )
        if not (branch.valid_from <= reference_date and (not branch.valid_to or branch.valid_to >= reference_date)):
            raise ValidationError(_("MP05 branch is not effective on the scenario reference date: %s") % branch.display_name)
        branches[spec["token"]] = branch

    departments = {}
    for spec in expected_departments:
        stable_key = _reference_key(scenario, "department", spec["token"])
        ref = references.filtered(lambda row, key=stable_key: row.stable_key == key)
        if len(ref) != 1 or ref.target_model != "hr.department":
            raise ValidationError(_("MP05 organization provenance missing or invalid: %s") % stable_key)
        department = scenario.env["hr.department"].browse(ref.target_res_id).exists()
        if not department:
            raise ValidationError(_("MP05 organization target no longer exists: %s") % stable_key)
        parent = departments.get(spec["parent"]) if spec["parent"] else scenario.env["hr.department"].browse()
        _assert_department_matches(
            department,
            company=company,
            code=_department_code(scenario, spec["token"]),
            name=spec["name"],
            unit_type=spec["unit_type"],
            parent=parent,
            valid_from=valid_from,
        )
        if not department.onehr_is_effective_on(reference_date):
            raise ValidationError(_("MP05 organization is not effective on the scenario reference date: %s") % department.display_name)
        departments[spec["token"]] = department

    shape = expected_foundation_shape(scenario.profile)
    return {
        "status": "PASS",
        "summary": (
            "MP05 Foundation PASS — selected legal company reused; "
            f"{shape['branches']} deterministic branch(es); "
            f"{shape['departments']} deterministic organization unit(s); "
            "company scope, hierarchy, effective dates and provenance are coherent."
        ),
        "reference_count": len(references),
        **shape,
    }

