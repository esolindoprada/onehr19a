
"""Whole-path OneHR source/runtime compatibility audit for MP02-MP05."""

import hashlib
import json
from pathlib import Path
from odoo import fields, release

from .contracts import (
    AUTHORITATIVE_SOURCE_LABEL,
    AUTHORITATIVE_SOURCE_SHA256,
    EXPECTED_ODOO_MAJOR,
    GENERATOR_CONTRACTS,
    GOVERNING_MASTER_PROMPT_SHA256,
    PRODUCTION_ADDON_VERSIONS,
    PRODUCTION_MANIFEST_NORMALIZED_SHA256,
    PUBLISHED_FINGERPRINT_NORMALIZED_SHA256,
    ROOT_GUARDRAIL_SHA256,
    SEQUENCE_POLICIES,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _normalized_text_sha256(path):
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class CompatibilityAudit:
    def __init__(self, env, scenario):
        self.env = env
        self.scenario = scenario
        self.checks = []

    def _check(self, key, ok, detail, required=True, blocked=False):
        if ok:
            status = "REQUIRED_AVAILABLE" if required else "OPTIONAL_AVAILABLE"
        elif blocked:
            status = "BLOCKED"
        else:
            status = "INCOMPATIBLE" if required else "OPTIONAL_UNAVAILABLE"
        self.checks.append({"key": key, "required": bool(required), "status": status, "detail": str(detail or "")})

    def _model_exists(self, model_name):
        return model_name in self.env.registry.models

    def _audit_framework(self):
        runtime = str(release.version)
        self._check("framework.odoo_major", runtime.split(".", 1)[0] == str(EXPECTED_ODOO_MAJOR),
                    f"runtime={runtime}; expected major={EXPECTED_ODOO_MAJOR}")
        pending = self.env["ir.module.module"].search(
            [("state", "in", ("to install", "to upgrade", "to remove"))], order="name"
        )
        self._check(
            "framework.module_operation_quiescence",
            not pending,
            "No pending module operations." if not pending else
            "Pending: " + ", ".join(f"{row.name}:{row.state}" for row in pending),
            blocked=bool(pending),
        )

    def _audit_guardrail(self):
        guardrail = PROJECT_ROOT / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md"
        declared = PROJECT_ROOT / "ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.sha256"
        if not guardrail.is_file() or not declared.is_file():
            self._check("governance.root_guardrail", False,
                        f"Missing root guardrail/checksum under {PROJECT_ROOT}.", blocked=True)
            return
        actual = hashlib.sha256(guardrail.read_bytes()).hexdigest().upper()
        declared_hash = declared.read_text(encoding="utf-8").strip().split()[0].upper()
        self._check(
            "governance.root_guardrail",
            actual == ROOT_GUARDRAIL_SHA256 and declared_hash == ROOT_GUARDRAIL_SHA256,
            f"actual={actual}; declared={declared_hash}; expected={ROOT_GUARDRAIL_SHA256}",
        )

    def _audit_modules_and_source(self):
        Module = self.env["ir.module.module"]
        runtime = {row.name: row for row in Module.search([("name", "in", list(PRODUCTION_ADDON_VERSIONS))])}
        for addon_name, expected_version in sorted(PRODUCTION_ADDON_VERSIONS.items()):
            row = runtime.get(addon_name)
            if not row:
                self._check(f"module.{addon_name}", False, f"Required addon missing; expected {expected_version}.")
                continue
            self._check(
                f"module.{addon_name}",
                row.state == "installed" and (row.latest_version or "") == expected_version,
                f"state={row.state}; runtime={row.latest_version or ''}; expected={expected_version}",
            )
            manifest_path = PROJECT_ROOT / addon_name / "__manifest__.py"
            if not manifest_path.is_file():
                self._check(f"source_manifest.{addon_name}", False, f"Manifest file missing: {manifest_path}")
            else:
                actual_hash = _normalized_text_sha256(manifest_path)
                expected_hash = PRODUCTION_MANIFEST_NORMALIZED_SHA256[addon_name]
                self._check(f"source_manifest.{addon_name}", actual_hash == expected_hash,
                            f"runtime={actual_hash}; expected={expected_hash}")

        for addon_name, expected_hash in sorted(PUBLISHED_FINGERPRINT_NORMALIZED_SHA256.items()):
            path = PROJECT_ROOT / addon_name / "docs" / "SOURCE_FINGERPRINT_SHA256.txt"
            if not path.is_file():
                self._check(f"source_fingerprint.{addon_name}", False, f"Published fingerprint file missing: {path}")
                continue
            actual_hash = _normalized_text_sha256(path)
            self._check(f"source_fingerprint.{addon_name}", actual_hash == expected_hash,
                        f"runtime={actual_hash}; expected={expected_hash}")

    def _literal_selection_keys(self, field):
        selection = field.selection
        if isinstance(selection, (list, tuple)):
            return {item[0] for item in selection if isinstance(item, (list, tuple)) and item}
        return None

    def _audit_generator_contracts(self):
        for contract in GENERATOR_CONTRACTS:
            prefix = contract["key"]
            for model_name, expected_fields in sorted(contract.get("models", {}).items()):
                if not self._model_exists(model_name):
                    self._check(f"{prefix}.model.{model_name}", False, "Required model missing.")
                    continue
                Model = self.env[model_name]
                self._check(f"{prefix}.model.{model_name}", True, "Model loaded in registry.")
                for field_name, expected_type in sorted(expected_fields.items()):
                    field = Model._fields.get(field_name)
                    actual_type = field.type if field else "MISSING"
                    self._check(f"{prefix}.field.{model_name}.{field_name}",
                                bool(field and field.type == expected_type),
                                f"runtime={actual_type}; expected={expected_type}")

            # Odoo-native fields used by a generator are runtime contracts. They are
            # intentionally separated from OneHR source-owned fields so static source
            # inventory does not pretend to own Odoo core.
            for model_name, expected_fields in sorted(contract.get("runtime_fields", {}).items()):
                if not self._model_exists(model_name):
                    self._check(f"{prefix}.runtime_model.{model_name}", False, "Required runtime model missing.")
                    continue
                Model = self.env[model_name]
                for field_name, expected_type in sorted(expected_fields.items()):
                    field = Model._fields.get(field_name)
                    actual_type = field.type if field else "MISSING"
                    self._check(
                        f"{prefix}.runtime_field.{model_name}.{field_name}",
                        bool(field and field.type == expected_type),
                        f"runtime={actual_type}; expected={expected_type}",
                    )

            for model_name, methods in sorted(contract.get("methods", {}).items()):
                if not self._model_exists(model_name):
                    for method_name in methods:
                        self._check(f"{prefix}.method.{model_name}.{method_name}", False, "Owning model missing.")
                    continue
                Model = self.env[model_name]
                for method_name in methods:
                    self._check(f"{prefix}.method.{model_name}.{method_name}",
                                hasattr(Model, method_name),
                                "Business method available." if hasattr(Model, method_name) else "Business method missing.")

            for field_path, expected_values in sorted(contract.get("selections", {}).items()):
                model_name, field_name = field_path.rsplit(".", 1)
                if not self._model_exists(model_name):
                    self._check(f"{prefix}.selection.{field_path}", False, "Owning model missing.")
                    continue
                field = self.env[model_name]._fields.get(field_name)
                actual_values = self._literal_selection_keys(field) if field else None
                ok = actual_values is not None and set(expected_values).issubset(actual_values)
                self._check(f"{prefix}.selection.{field_path}", ok,
                            f"runtime={sorted(actual_values) if actual_values is not None else 'MISSING/NON_LITERAL'}; "
                            f"required={expected_values}")

            for xmlid in contract.get("xmlids", []):
                record = self.env.ref(xmlid, raise_if_not_found=False)
                self._check(f"{prefix}.xmlid.{xmlid}", bool(record),
                            "Required XML ID resolved." if record else "Required XML ID missing.")

            for group_xmlid in contract.get("groups", []):
                record = self.env.ref(group_xmlid, raise_if_not_found=False)
                self._check(f"{prefix}.group.{group_xmlid}",
                            bool(record and record._name == "res.groups"),
                            "Required actor group resolved." if record and record._name == "res.groups"
                            else "Required actor group missing/invalid.")

            self._check(f"{prefix}.side_effect_contract",
                        contract.get("side_effect") not in (None, "", "UNVERIFIED"),
                        f"classification={contract.get('side_effect')}")
            self._check(f"{prefix}.reset_contract",
                        contract.get("reset_policy") not in (None, "", "UNVERIFIED"),
                        f"classification={contract.get('reset_policy')}")

    def _audit_sequences(self):
        """Audit production sequence contracts without making mutable counters a demo dependency.

        The demo orchestration identity is deliberately separate from production presentation
        sequences. Sequence XML/configuration and stable identity fields remain visible in the
        whole-path evidence, but their current database rows are NOT a required prerequisite for
        the currently implemented demo generators. This prevents a mutable production counter or
        missing sequence row from changing the demo compatibility truth.
        """
        Sequence = self.env["ir.sequence"]
        for policy in SEQUENCE_POLICIES:
            code = policy["code"]
            dependency = policy.get("demo_generation_dependency", "NONE")
            sequence = Sequence.search([("code", "=", code)], limit=1)
            required_for_demo = dependency != "NONE"
            self._check(
                f"sequence.{code}", bool(sequence),
                f"configured={bool(sequence)}; strategy={policy['strategy']}; "
                f"demo_generation_dependency={dependency}; "
                f"direct_demo_next_by_code={policy['direct_demo_next_by_code']}",
                required=required_for_demo,
            )
            model_name = policy["model"]
            if not self._model_exists(model_name):
                self._check(
                    f"sequence_identity.{code}", False,
                    f"Owning model missing: {model_name}",
                    required=required_for_demo,
                )
                continue
            Model = self.env[model_name]
            missing = [name for name in policy["stable_fields"] if name not in Model._fields]
            self._check(
                f"sequence_identity.{code}", not missing,
                "stable_fields=" + ",".join(policy["stable_fields"])
                if not missing else "Missing stable fields: " + ",".join(missing),
                required=required_for_demo,
            )

    def run(self):
        # Deliberately non-short-circuiting: one native trial exposes the complete
        # frozen structural incompatibility set instead of serial one-error repair.
        self._audit_framework()
        self._audit_guardrail()
        self._audit_modules_and_source()
        self._audit_generator_contracts()
        self._audit_sequences()

        failures = [row for row in self.checks
                    if row["required"] and row["status"] in {"INCOMPATIBLE", "BLOCKED", "UNVERIFIED"}]
        # Compatibility truth excludes execution-only metadata. In particular,
        # database name, operator, check timestamp and the human source label must not
        # make the same source/runtime/scenario contract hash differently.
        fingerprint_payload = {
            "authoritative_source_sha256": AUTHORITATIVE_SOURCE_SHA256,
            "governing_master_prompt_sha256": GOVERNING_MASTER_PROMPT_SHA256,
            "root_guardrail_sha256": ROOT_GUARDRAIL_SHA256,
            "odoo_version": str(release.version),
            "scenario": self.scenario.code,
            "scenario_version": self.scenario.scenario_version,
            "profile": self.scenario.profile,
            "profile_version": self.scenario.profile_version,
            "reference_date": str(self.scenario.reference_date or ""),
            "reference_datetime": str(self.scenario.reference_datetime or ""),
            "timezone": self.scenario.timezone,
            "seed": self.scenario.deterministic_seed,
            # Mutable production sequence rows/counters are intentionally excluded from
            # compatibility truth. The frozen policy itself remains part of the code contract.
            "checks": [
                row for row in self.checks
                if not row["key"].startswith(("sequence.", "sequence_identity."))
            ],
            "sequence_policy_contract": [
                {
                    "code": policy["code"],
                    "model": policy["model"],
                    "stable_fields": policy["stable_fields"],
                    "strategy": policy["strategy"],
                    "direct_demo_next_by_code": policy["direct_demo_next_by_code"],
                    "demo_generation_dependency": policy.get("demo_generation_dependency", "NONE"),
                }
                for policy in SEQUENCE_POLICIES
            ],
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        evidence = {
            "authoritative_source_label": AUTHORITATIVE_SOURCE_LABEL,
            "database": self.env.cr.dbname,
            **fingerprint_payload,
            "operator": self.env.user.login,
            "checked_at": str(fields.Datetime.now()),
            "compatibility_fingerprint": fingerprint,
        }
        return {
            "compatible": not failures,
            "fingerprint": fingerprint,
            "checks": self.checks,
            "failure_count": len(failures),
            "first_failure": failures[0] if failures else None,
            "evidence": evidence,
        }

