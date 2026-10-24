
"""Provenance-first bounded reset service.

Reset never falls back to broad company/date/name deletion. MP05 company, branch and
organization masters are deliberately retained under REUSE_ON_REBUILD; only their
scenario provenance references are invalidated so a rebuild can rebind to the exact
same deterministic records.
"""

from odoo.exceptions import UserError, ValidationError


def _retain_for_rebuild(scenario, row):
    Reference = scenario.env["onehr.demo.reference"]
    reference = Reference.search([
        ("scenario_id", "=", scenario.id),
        ("stable_key", "=", row["stable_key"]),
    ], limit=1)
    if not reference:
        raise ValidationError(f"Reset provenance disappeared: {row['stable_key']}")
    if reference.reset_policy != "REUSE_ON_REBUILD":
        raise ValidationError(
            f"Reset handler policy mismatch for {row['stable_key']}: {reference.reset_policy}"
        )
    reference.with_context(onehr_demo_reference_controlled=True).write({"state": "invalidated"})
    return {"processed": 1, "protected": 0}


RESET_HANDLERS = {
    ("res.company", "REUSE_ON_REBUILD"): _retain_for_rebuild,
    ("onehr.branch", "REUSE_ON_REBUILD"): _retain_for_rebuild,
    ("hr.department", "REUSE_ON_REBUILD"): _retain_for_rebuild,
}


class DemoResetService:
    def __init__(self, scenario):
        self.scenario = scenario
        self.env = scenario.env

    def preview(self):
        references = self.env["onehr.demo.reference"].search([
            ("scenario_id", "=", self.scenario.id),
            ("state", "=", "active"),
        ], order="generator_key, stable_key")
        rows = []
        for reference in references:
            handler = RESET_HANDLERS.get((reference.target_model, reference.reset_policy))
            rows.append({
                "stable_key": reference.stable_key,
                "generator_key": reference.generator_key,
                "model": reference.target_model,
                "record_id": reference.target_res_id,
                "company_id": reference.company_id.id,
                "reset_policy": reference.reset_policy,
                "planned_action": "RETAIN_FOR_REBUILD" if handler else "PROTECTED_NO_HANDLER",
            })
        return rows

    def execute(self):
        rows = self.preview()
        blockers = [row for row in rows if row["planned_action"] == "PROTECTED_NO_HANDLER"]
        if blockers:
            policies = sorted({f"{row['model']}:{row['reset_policy']}" for row in blockers})
            raise UserError(
                "Reset blocked because bounded reset handlers are not frozen for: " + ", ".join(policies)
            )

        totals = {"processed": 0, "protected": 0}
        # Reset is one bounded atomic unit. A mid-reset failure must not leave only
        # part of the provenance invalidated.
        with self.env.cr.savepoint():
            for row in rows:
                result = RESET_HANDLERS[(row["model"], row["reset_policy"])](self.scenario, row) or {}
                totals["processed"] += int(result.get("processed", 0))
                totals["protected"] += int(result.get("protected", 0))

            remaining = self.env["onehr.demo.reference"].search_count([
                ("scenario_id", "=", self.scenario.id),
                ("state", "=", "active"),
            ])
            if remaining:
                raise ValidationError(
                    f"Reset postcondition failed: {remaining} active provenance reference(s) remain."
                )
        return totals

