
"""MASTER PROMPT 06 — deterministic jobs, grades, work locations and positions.

This bounded generator consumes only the frozen MP05 foundation and uses explicit
business identifiers/provenance. It never calls an Odoo production sequence for
identity or ordering.
"""
from datetime import timedelta

from odoo import _, fields
from odoo.exceptions import AccessError, ValidationError

from ..services.deterministic import stable_identifier
from .foundation_enterprise import _ensure_profile_departments

GENERATOR_KEY = "organization.jobs_positions"
RESET_POLICY = "REUSE_ON_REBUILD"
_PROFILE_RANK = {"quick": 1, "standard": 2, "full": 3}

JOB_CATALOG = (
    {"token":"hr_manager", "name":"HR Manager", "department":"hr", "rank":1},
    {"token":"finance_manager", "name":"Finance Manager", "department":"finance", "rank":1},
    {"token":"operations_manager", "name":"Operations Manager", "department":"operations_delivery", "rank":1},
    {"token":"it_manager", "name":"IT Manager", "department":"it", "rank":1},
    {"token":"sales_manager", "name":"Sales Manager", "department":"sales", "rank":2},
    {"token":"learning_specialist", "name":"Learning Specialist", "department":"learning", "rank":2},
    {"token":"data_analyst", "name":"Data Analyst", "department":"data", "rank":2},
    {"token":"procurement_officer", "name":"Procurement Officer", "department":"procurement", "rank":3},
)
GRADE_CATALOG = (
    {"token":"g1", "code":"G1", "name":"Grade 1 — Professional", "sequence":10, "rank":1},
    {"token":"g2", "code":"G2", "name":"Grade 2 — Senior Professional", "sequence":20, "rank":1},
    {"token":"g3", "code":"G3", "name":"Grade 3 — Manager", "sequence":30, "rank":2},
    {"token":"g4", "code":"G4", "name":"Grade 4 — Senior Manager", "sequence":40, "rank":3},
)
LOCATION_CATALOG = (
    {"token":"jakarta", "code":"LOC-JKT", "name":"OneHR Jakarta HQ", "timezone":"Asia/Jakarta", "rank":1},
    {"token":"bali", "code":"LOC-BAL", "name":"OneHR Bali Office", "timezone":"Asia/Makassar", "rank":1},
    {"token":"bandung", "code":"LOC-BDG", "name":"OneHR Bandung Office", "timezone":"Asia/Jakarta", "rank":2},
    {"token":"surabaya", "code":"LOC-SBY", "name":"OneHR Surabaya Office", "timezone":"Asia/Jakarta", "rank":3},
)
POSITION_CATALOG = (
    {"token":"hr_manager", "name":"HR Manager — Corporate", "job":"hr_manager", "department":"hr", "grade":"g3", "location":"jakarta", "hc":1, "fte":1.0, "status":"filled", "rank":1},
    {"token":"finance_manager", "name":"Finance Manager — Corporate", "job":"finance_manager", "department":"finance", "grade":"g3", "location":"jakarta", "hc":1, "fte":1.0, "status":"open", "rank":1},
    {"token":"operations_manager", "name":"Operations Manager — Delivery", "job":"operations_manager", "department":"operations_delivery", "grade":"g3", "location":"bali", "hc":1, "fte":1.0, "status":"open", "rank":1},
    {"token":"it_manager", "name":"IT Manager — Technology", "job":"it_manager", "department":"it", "grade":"g3", "location":"bandung", "hc":1, "fte":1.0, "status":"filled", "rank":2},
    {"token":"sales_manager", "name":"Sales Manager — Commercial", "job":"sales_manager", "department":"sales", "grade":"g3", "location":"jakarta", "hc":1, "fte":1.0, "status":"open", "rank":2},
    {"token":"learning_specialist", "name":"Learning Specialist", "job":"learning_specialist", "department":"learning", "grade":"g2", "location":"bandung", "hc":2, "fte":2.0, "status":"open", "rank":2},
    {"token":"data_analyst", "name":"Data Analyst", "job":"data_analyst", "department":"data", "grade":"g2", "location":"bandung", "hc":2, "fte":2.0, "status":"open", "rank":2},
    {"token":"procurement_officer", "name":"Procurement Officer", "job":"procurement_officer", "department":"procurement", "grade":"g1", "location":"surabaya", "hc":2, "fte":2.0, "status":"open", "rank":3},
)


def _rows(catalog, profile):
    rank = _PROFILE_RANK[profile]
    return [dict(row) for row in catalog if row["rank"] <= rank]


def _key(scenario, entity, token):
    return scenario.deterministic_key("organization", entity, token)


def _code(scenario, prefix, token):
    return stable_identifier(prefix, f"{scenario.code}.{token}", max_length=48)


def _existing_target(scenario, stable_key, expected_model):
    Reference = scenario.env["onehr.demo.reference"]
    reference = Reference.search([("scenario_id","=",scenario.id),("stable_key","=",stable_key)], limit=1)
    if not reference:
        return reference, scenario.env[expected_model].browse()
    if reference.target_model != expected_model:
        raise ValidationError(_("Deterministic key %(key)s points to %(actual)s; expected %(expected)s.") % {
            "key": stable_key, "actual": reference.target_model, "expected": expected_model})
    target = scenario.env[expected_model].browse(reference.target_res_id).exists()
    if not target:
        raise ValidationError(_("Deterministic provenance %(key)s points to missing %(model)s/%(id)s.") % {
            "key": stable_key, "model": expected_model, "id": reference.target_res_id})
    return reference, target


def _exact_or_error(Model, domain, label):
    rows = Model.with_context(active_test=False).search(domain, order="id")
    if len(rows) > 1:
        raise ValidationError(_("Deterministic MP06 identity is ambiguous for %(label)s: %(count)s records match.") % {
            "label": label, "count": len(rows)})
    return rows[:1]


def _register(scenario, run, stable_key, target, disposition):
    return scenario.env["onehr.demo.reference"].register_reference(
        scenario=scenario, generator_key=GENERATOR_KEY, stable_key=stable_key,
        target=target, run=run, disposition=disposition, reset_policy=RESET_POLICY)


def readiness_blockers_organization_jobs_positions(scenario):
    blockers = []
    env = scenario.env
    company = scenario.company_id
    if company not in env.user.company_ids:
        blockers.append(_("Scenario company is outside the current operator's allowed companies."))
    for model_name, operations in {
        "hr.job": ("read","create"),
        "onehr.grade": ("read","create"),
        "hr.work.location": ("read","create"),
        "onehr.position": ("read","create"),
        "hr.department": ("read",),
    }.items():
        Model = env[model_name]
        for operation in operations:
            try:
                Model.check_access(operation)
            except AccessError as exc:
                blockers.append(_("%(model)s %(operation)s authority is missing: %(detail)s") % {
                    "model":model_name,"operation":operation,"detail":str(exc)})
    for model_name in ("hr.department","hr.job","onehr.grade","hr.work.location","onehr.position"):
        try:
            env[model_name].search_count([("company_id","=",company.id)], limit=1)
        except AccessError as exc:
            blockers.append(_("%(model)s company-scoped read is blocked: %(detail)s") % {
                "model":model_name,"detail":str(exc)})
    return blockers


def _assert_common(record, expected):
    mismatches = []
    for field_name, value in expected.items():
        actual = record[field_name]
        if hasattr(actual, "id"):
            actual = actual.id
        if actual != value:
            mismatches.append(field_name)
    if mismatches:
        raise ValidationError(_("Existing deterministic MP06 record conflicts with frozen contract: %(fields)s.") % {
            "fields":", ".join(mismatches)})


def generate_organization_jobs_positions(scenario, run):
    env = scenario.env
    company = scenario.company_id
    valid_from = fields.Date.to_date(scenario.reference_date) - timedelta(days=730)
    counters = {"created":0,"reused":0,"updated":0,"skipped":0,"protected":0}
    # MP05 may already be PASS from an earlier bounded source revision while a
    # department required by this MP06 profile was not yet materialized. Reconcile
    # the exact frozen MP05 department contract before MP06 consumes it.
    prerequisite = _ensure_profile_departments(scenario, run)
    for key in counters:
        counters[key] += int(prerequisite.get(key, 0))
    departments = {}
    Department = env["hr.department"]
    for token in {r["department"] for r in _rows(JOB_CATALOG, scenario.profile)} | {r["department"] for r in _rows(POSITION_CATALOG, scenario.profile)}:
        stable_key = _key(scenario, "department", token)
        ref, dept = _existing_target(scenario, stable_key, "hr.department")
        if not dept:
            raise ValidationError(_("MP06 prerequisite department provenance is missing: %s") % stable_key)
        departments[token] = dept

    Grade = env["onehr.grade"]
    grades = {}
    for spec in _rows(GRADE_CATALOG, scenario.profile):
        key = _key(scenario, "grade", spec["token"])
        ref, grade = _existing_target(scenario, key, "onehr.grade")
        code = _code(scenario, "DGR", spec["token"])
        if not grade:
            grade = _exact_or_error(Grade, [("company_id","=",company.id),("code","=ilike",code)], f"onehr.grade {code}")
        if grade:
            _assert_common(grade, {"code":code,"name":spec["name"],"sequence":spec["sequence"],"company_id":company.id,"active":True})
            disposition="reused"; counters["reused"] += 1
        else:
            grade = Grade.create({"code":code,"name":spec["name"],"sequence":spec["sequence"],"company_id":company.id,"active":True,"valid_from":valid_from})
            disposition="created"; counters["created"] += 1
        _register(scenario, run, key, grade, disposition)
        grades[spec["token"]] = grade

    Location = env["hr.work.location"]
    locations = {}
    for spec in _rows(LOCATION_CATALOG, scenario.profile):
        key = _key(scenario, "work_location", spec["token"])
        ref, location = _existing_target(scenario, key, "hr.work.location")
        if not location:
            location = _exact_or_error(Location, [("company_id","=",company.id),("onehr_site_code","=",spec["code"])], f"hr.work.location {spec['code']}")
        values = {"name":spec["name"],"company_id":company.id,"onehr_site_code":spec["code"],"onehr_timezone":spec["timezone"],"onehr_valid_from":valid_from,"active":True}
        if location:
            _assert_common(location, values)
            disposition="reused"; counters["reused"] += 1
        else:
            location = Location.create(values)
            disposition="created"; counters["created"] += 1
        _register(scenario, run, key, location, disposition)
        locations[spec["token"]] = location

    Job = env["hr.job"]
    jobs = {}
    for spec in _rows(JOB_CATALOG, scenario.profile):
        key = _key(scenario, "job", spec["token"])
        ref, job = _existing_target(scenario, key, "hr.job")
        code = _code(scenario, "DJOB", spec["token"])
        values = {"name":spec["name"],"company_id":company.id,"onehr_code":code,"onehr_valid_from":valid_from,"active":True}
        if not job:
            job = _exact_or_error(Job, [("company_id","=",company.id),("onehr_code","=ilike",code)], f"hr.job {code}")
        if job:
            _assert_common(job, values)
            disposition="reused"; counters["reused"] += 1
        else:
            job = Job.create(values)
            disposition="created"; counters["created"] += 1
        _register(scenario, run, key, job, disposition)
        jobs[spec["token"]] = job

    Position = env["onehr.position"]
    for spec in _rows(POSITION_CATALOG, scenario.profile):
        key = _key(scenario, "position", spec["token"])
        ref, position = _existing_target(scenario, key, "onehr.position")
        code = _code(scenario, "DPOS", spec["token"])
        values = {
            "code":code,"name":spec["name"],"company_id":company.id,"job_id":jobs[spec["job"]].id,
            "department_id":departments[spec["department"]].id,"grade_id":grades[spec["grade"]].id,
            "work_location_id":locations[spec["location"]].id,"authorized_headcount":spec["hc"],
            "authorized_fte":spec["fte"],"status":spec["status"],"active":True,"valid_from":valid_from,
        }
        if not position:
            position = _exact_or_error(Position, [("company_id","=",company.id),("code","=ilike",code)], f"onehr.position {code}")
        if position:
            _assert_common(position, values)
            disposition="reused"; counters["reused"] += 1
        else:
            position = Position.create(values)
            disposition="created"; counters["created"] += 1
        _register(scenario, run, key, position, disposition)

    return counters


def validate_organization_jobs_positions(scenario, run):
    profile = scenario.profile
    expected_jobs = _rows(JOB_CATALOG, profile)
    expected_grades = _rows(GRADE_CATALOG, profile)
    expected_locations = _rows(LOCATION_CATALOG, profile)
    expected_positions = _rows(POSITION_CATALOG, profile)
    refs = scenario.env["onehr.demo.reference"].search([("scenario_id","=",scenario.id),("generator_key","=",GENERATOR_KEY),("state","=","active")])
    required = len(expected_jobs)+len(expected_grades)+len(expected_locations)+len(expected_positions)
    if len(refs) < required:
        raise ValidationError(_("MP06 provenance incomplete: expected at least %(required)s active references, found %(found)s.") % {"required":required,"found":len(refs)})
    return {"summary":f"MP06 PASS — jobs={len(expected_jobs)}, grades={len(expected_grades)}, locations={len(expected_locations)}, positions={len(expected_positions)}; deterministic provenance complete."}

