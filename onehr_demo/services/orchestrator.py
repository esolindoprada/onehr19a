
"""Fixed code-owned orchestration boundary for implemented OneHR Demo generators."""

from time import monotonic

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError

from .contracts import CONTRACT_BY_KEY, IMPLEMENTED_GENERATOR_KEYS
from .sanitization import safe_exception_summary
from ..generators.foundation_enterprise import (
    generate_foundation_enterprise,
    readiness_blockers_foundation_enterprise,
    validate_foundation_enterprise,
)
from ..generators.organization_jobs_positions import (
    generate_organization_jobs_positions,
    readiness_blockers_organization_jobs_positions,
    validate_organization_jobs_positions,
)

BUSINESS_GENERATOR_HANDLERS = {
    "foundation.enterprise": generate_foundation_enterprise,
    "organization.jobs_positions": generate_organization_jobs_positions,
}
BUSINESS_GENERATOR_VALIDATORS = {
    "foundation.enterprise": validate_foundation_enterprise,
    "organization.jobs_positions": validate_organization_jobs_positions,
}
BUSINESS_GENERATOR_READINESS_CHECKS = {
    "foundation.enterprise": readiness_blockers_foundation_enterprise,
    "organization.jobs_positions": readiness_blockers_organization_jobs_positions,
}


def classify_generator_exception(exc):
    if isinstance(exc, AccessError):
        return "ENVIRONMENT_FAILURE"
    if isinstance(exc, (ValidationError, UserError)):
        return "DATA/MIGRATION_FAILURE"
    return "ADDON_SOURCE_FAILURE"


def implemented_readiness_blockers(scenario):
    """Audit every currently executable generator before the first mutation."""
    blockers = []
    for generator_key in IMPLEMENTED_GENERATOR_KEYS:
        checker = BUSINESS_GENERATOR_READINESS_CHECKS.get(generator_key)
        if not checker:
            blockers.append(f"{generator_key}: fixed readiness checker is missing.")
            continue
        for detail in checker(scenario):
            blockers.append(f"{generator_key}: {detail}")
    return blockers


class DemoOrchestrator:
    def __init__(self, scenario, run):
        self.scenario = scenario
        self.run = run
        self.env = scenario.env

    def _generator_metadata(self, generator_key):
        generator = self.env["onehr.demo.generator"].search([("key", "=", generator_key)], limit=1)
        if not generator:
            raise UserError(f"Fixed generator metadata missing: {generator_key}")
        return generator

    def _new_checkpoint(self, generator):
        return self.env["onehr.demo.checkpoint"]._controlled_create({
            "run_id": self.run.id,
            "scenario_id": self.scenario.id,
            "company_id": self.scenario.company_id.id,
            "generator_id": generator.id,
            "generator_key": generator.key,
            "sequence": generator.sequence,
            "state": "running",
            "started_at": fields.Datetime.now(),
        })

    def execute_generator(self, generator_key):
        """Execute exactly one deterministic contract unit.

        Ordering is supplied by the frozen contract registry, never by mutable
        production sequences/counters. The caller is responsible for selecting
        the next contract from the scenario-wide evidence state.
        """
        if generator_key not in IMPLEMENTED_GENERATOR_KEYS:
            raise UserError(f"{generator_key} is not implemented in this bounded release.")
        contract = CONTRACT_BY_KEY[generator_key]
        generator = self._generator_metadata(generator_key)
        Checkpoint = self.env["onehr.demo.checkpoint"]
        passed = Checkpoint.search([
            ("scenario_id", "=", self.scenario.id),
            ("generator_key", "=", generator_key),
            ("state", "=", "pass"),
        ], limit=1)
        if passed:
            return {"already_passed": True, "generator_key": generator_key, "summary": passed.validation_summary or "PASS"}
        for prerequisite in contract.get("prerequisites", []):
            if not Checkpoint.search_count([
                ("scenario_id", "=", self.scenario.id),
                ("generator_key", "=", prerequisite),
                ("state", "=", "pass"),
            ]):
                raise UserError(f"{generator_key} is blocked until prerequisite {prerequisite} is PASS.")
        handler = BUSINESS_GENERATOR_HANDLERS.get(generator_key)
        validator = BUSINESS_GENERATOR_VALIDATORS.get(generator_key)
        if not handler or not validator:
            raise UserError(f"{generator_key} is marked implemented but its fixed handler/validator contract is incomplete.")
        checkpoint = self._new_checkpoint(generator)
        started = monotonic()
        totals = {"created":0,"reused":0,"updated":0,"skipped":0,"protected":0}
        try:
            with self.env.cr.savepoint():
                result = handler(self.scenario, self.run) or {}
                validation = validator(self.scenario, self.run) or {}
                for key in totals:
                    totals[key] = int(result.get(key, 0))
                checkpoint._controlled_write({
                    "state":"pass",
                    "created_count":totals["created"],
                    "reused_count":totals["reused"],
                    "updated_count":totals["updated"],
                    "skipped_count":totals["skipped"],
                    "protected_count":totals["protected"],
                    "validation_summary":str(validation.get("summary", "PASS"))[:2000],
                    "finished_at":fields.Datetime.now(),
                    "duration_seconds":monotonic()-started,
                })
        except Exception as exc:
            classification = classify_generator_exception(exc)
            checkpoint._controlled_write({
                "state":"failed",
                "root_cause_classification":classification,
                "first_actionable_root_cause":safe_exception_summary(exc, 1000),
                "technical_detail":safe_exception_summary(exc, 2000),
                "finished_at":fields.Datetime.now(),
                "duration_seconds":monotonic()-started,
            })
            raise
        return {"generator_key":generator_key, "already_passed":False, **totals, "summary":checkpoint.validation_summary}

    def execute(self):
        if not IMPLEMENTED_GENERATOR_KEYS:
            raise UserError("No bounded business generator is implemented.")

        Checkpoint = self.env["onehr.demo.checkpoint"]
        totals = {"created": 0, "reused": 0, "updated": 0, "skipped": 0, "protected": 0}

        for generator_key in IMPLEMENTED_GENERATOR_KEYS:
            contract = CONTRACT_BY_KEY[generator_key]
            generator = self._generator_metadata(generator_key)

            failed_predecessor = Checkpoint.search([
                ("run_id", "=", self.run.id),
                ("generator_key", "in", contract.get("prerequisites", [])),
                ("state", "in", ("failed", "blocked")),
            ], limit=1)
            if failed_predecessor:
                Checkpoint._controlled_create({
                    "run_id": self.run.id,
                    "scenario_id": self.scenario.id,
                    "company_id": self.scenario.company_id.id,
                    "generator_id": generator.id,
                    "generator_key": generator_key,
                    "sequence": generator.sequence,
                    "state": "blocked",
                    "validation_summary": (
                        f"Blocked by {failed_predecessor.generator_key}: {failed_predecessor.state}"
                    ),
                })
                break

            handler = BUSINESS_GENERATOR_HANDLERS.get(generator_key)
            validator = BUSINESS_GENERATOR_VALIDATORS.get(generator_key)
            if not handler or not validator:
                raise UserError(
                    f"{generator_key} is marked implemented but its fixed handler/validator contract is incomplete."
                )

            checkpoint = self._new_checkpoint(generator)
            started = monotonic()
            try:
                # One generator == one bounded atomic unit. Business work and its
                # immediate postcondition validation share one savepoint.
                with self.env.cr.savepoint():
                    result = handler(self.scenario, self.run) or {}
                    validation = validator(self.scenario, self.run) or {}
                    for key in totals:
                        totals[key] += int(result.get(key, 0))
                    checkpoint._controlled_write({
                        "state": "pass",
                        "created_count": int(result.get("created", 0)),
                        "reused_count": int(result.get("reused", 0)),
                        "updated_count": int(result.get("updated", 0)),
                        "skipped_count": int(result.get("skipped", 0)),
                        "protected_count": int(result.get("protected", 0)),
                        "validation_summary": str(validation.get("summary", "PASS"))[:2000],
                        "finished_at": fields.Datetime.now(),
                        "duration_seconds": monotonic() - started,
                    })
            except Exception as exc:
                classification = classify_generator_exception(exc)
                checkpoint._controlled_write({
                    "state": "failed",
                    "root_cause_classification": classification,
                    "first_actionable_root_cause": safe_exception_summary(exc, 1000),
                    "technical_detail": safe_exception_summary(exc, 2000),
                    "finished_at": fields.Datetime.now(),
                    "duration_seconds": monotonic() - started,
                })
                raise

        return totals

    def validate(self):
        """Re-validate all implemented generators without creating business data."""
        summaries = []
        for generator_key in IMPLEMENTED_GENERATOR_KEYS:
            generator = self._generator_metadata(generator_key)
            validator = BUSINESS_GENERATOR_VALIDATORS.get(generator_key)
            if not validator:
                raise UserError(f"{generator_key} is implemented but has no fixed validator.")

            checkpoint = self._new_checkpoint(generator)
            started = monotonic()
            try:
                with self.env.cr.savepoint():
                    result = validator(self.scenario, self.run) or {}
                    summary = str(result.get("summary", "PASS"))
                    summaries.append(summary)
                    checkpoint._controlled_write({
                        "state": "pass",
                        "validation_summary": summary[:2000],
                        "finished_at": fields.Datetime.now(),
                        "duration_seconds": monotonic() - started,
                    })
            except Exception as exc:
                classification = classify_generator_exception(exc)
                checkpoint._controlled_write({
                    "state": "failed",
                    "root_cause_classification": classification,
                    "first_actionable_root_cause": safe_exception_summary(exc, 1000),
                    "technical_detail": safe_exception_summary(exc, 2000),
                    "finished_at": fields.Datetime.now(),
                    "duration_seconds": monotonic() - started,
                })
                raise
        return {"summary": " | ".join(summaries), "validated_generators": len(summaries)}

