#!/usr/bin/env python3
"""Validate the schema-first RKF v1 data-model and paper-template boundary."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from rkf.schema import (  # noqa: E402
    ACCESS_STATES,
    APPRAISAL_STATUSES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    LEGACY_READING_MAP,
    LOCATOR_STATES,
    PROVIDER_STATUSES,
    REVIEW_STATES,
    VERIFICATION_STATES,
    canonical_enum,
    load_canonical_schema,
)
from rkf.core import Workspace  # noqa: E402
from rkf.providers import (  # noqa: E402
    FullTextProviderResult,
    register_acquisition_run,
    register_evidence_artifact,
)


REQUIRED_DEFINITIONS = {
    "paper",
    "finding",
    "evidence",
    "claim",
    "synthesis",
    "projectConnection",
    "activationEvent",
    "actionEvent",
    "fullTextProviderResult",
    "canonicalIdentifier",
    "acquisitionAttempt",
    "acquisitionRun",
    "artifactRecord",
    "argumentMap",
    "appraisalProviderResult",
    "retrievalRun",
    "readRun",
}


EXPECTED_ENUMS = {
    "accessState": ACCESS_STATES,
    "reviewState": REVIEW_STATES,
    "evidenceStance": EVIDENCE_STANCES,
    "verificationState": VERIFICATION_STATES,
    "claimStatus": CLAIM_STATUSES,
    "locatorState": LOCATOR_STATES,
    "appraisalStatus": APPRAISAL_STATUSES,
    "providerStatus": PROVIDER_STATUSES,
}


def validate_instance(
    value: Any,
    definition: dict[str, Any],
    root_schema: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    """Validate the JSON-Schema features used by representative RKF payloads."""

    findings: list[str] = []
    if "$ref" in definition:
        reference = str(definition["$ref"])
        prefix = "#/$defs/"
        if not reference.startswith(prefix):
            return [f"{label}: unsupported schema reference {reference}"]
        target = root_schema.get("$defs", {}).get(reference.removeprefix(prefix))
        if not isinstance(target, dict):
            return [f"{label}: unresolved schema reference {reference}"]
        return validate_instance(value, target, root_schema, label=label)

    all_of = definition.get("allOf")
    if isinstance(all_of, list):
        for item in all_of:
            if isinstance(item, dict):
                findings.extend(
                    validate_instance(value, item, root_schema, label=label)
                )
    condition = definition.get("if")
    if isinstance(condition, dict):
        condition_matches = not validate_instance(
            value,
            condition,
            root_schema,
            label=label,
        )
        branch = definition.get("then" if condition_matches else "else")
        if isinstance(branch, dict):
            findings.extend(
                validate_instance(value, branch, root_schema, label=label)
            )
    forbidden = definition.get("not")
    if isinstance(forbidden, dict) and not validate_instance(
        value,
        forbidden,
        root_schema,
        label=label,
    ):
        findings.append(f"{label}: value matches a forbidden schema")

    if "const" in definition and value != definition["const"]:
        findings.append(f"{label}: expected const {definition['const']!r}")
    if "enum" in definition and value not in definition["enum"]:
        findings.append(f"{label}: value {value!r} is outside enum")

    expected_type = definition.get("type")
    type_matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if isinstance(expected_type, str) and not type_matches.get(expected_type, True):
        return [f"{label}: expected {expected_type}, got {type(value).__name__}"]

    if isinstance(value, str):
        if len(value) < int(definition.get("minLength", 0)):
            findings.append(f"{label}: string is shorter than minLength")
        pattern = definition.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            findings.append(f"{label}: value does not match {pattern}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = definition.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            findings.append(f"{label}: value is below minimum {minimum}")
    if isinstance(value, list):
        item_schema = definition.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                findings.extend(
                    validate_instance(item, item_schema, root_schema, label=f"{label}[{index}]")
                )
        if definition.get("uniqueItems") is True:
            serialized = [json.dumps(item, sort_keys=True, ensure_ascii=True) for item in value]
            if len(serialized) != len(set(serialized)):
                findings.append(f"{label}: array items are not unique")
    if isinstance(value, dict):
        required = definition.get("required", [])
        for key in required if isinstance(required, list) else []:
            if key not in value:
                findings.append(f"{label}: missing required property {key}")
        properties = definition.get("properties", {})
        if isinstance(properties, dict):
            if definition.get("additionalProperties") is False:
                for key in sorted(set(value) - set(properties)):
                    findings.append(f"{label}: unexpected property {key}")
            for key, child in properties.items():
                if key in value and isinstance(child, dict):
                    findings.extend(
                        validate_instance(value[key], child, root_schema, label=f"{label}.{key}")
                    )
    return findings


def runtime_payload_findings(schema: dict[str, Any]) -> list[str]:
    """Exercise representative provider outputs against their canonical schemas."""

    findings: list[str] = []
    finding_fixture = {
        "schema": "rkf-finding-v1",
        "finding_id": "fd_1234567890abcdef1234",
        "paper_id": "papers/schema-fixture",
        "summary": "Synthetic schema-only FindingDraft.",
        "reading_scope": "abstract",
        "locator_state": "missing",
        "origin_project_id": "prj_1234567890abcdef12345678",
        "activation_id": "act_1234567890abcdef12345678",
        "content_fingerprint": "a" * 64,
        "public_safe": True,
    }
    findings.extend(
        validate_instance(
            finding_fixture,
            schema.get("$defs", {}).get("finding", {}),
            schema,
            label="FindingDraft",
        )
    )
    provider_result = FullTextProviderResult(
        status="obtained",
        provider="schema-fixture",
        provider_version="1",
        route="open-access",
        tried_routes=("open-access",),
        artifact_sha256="a" * 64,
        private_artifact_handle="private://schema-fixture",
        elapsed_ms=1,
        entitlement_state="covered",
        pdf_magic_validated=True,
        acquisition_run_id="acq_1234567890abcdef12345678",
    )
    provider_definition = schema.get("$defs", {}).get("fullTextProviderResult", {})
    findings.extend(
        validate_instance(
            provider_result.public_payload(),
            provider_definition,
            schema,
            label="FullTextProviderResult.public_payload",
        )
    )

    artifact_schema = json.loads(
        (REPO / "schemas" / "evidence_artifact.schema.json").read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory() as directory:
        workspace = Workspace(Path(directory))
        artifact = register_evidence_artifact(
            workspace,
            paper_id="papers/schema-fixture",
            result=provider_result,
            origin_project_id="prj_1234567890abcdef12345678",
            activation_id="act_1234567890abcdef12345678",
        )
        acquisition_run = register_acquisition_run(
            workspace,
            result=provider_result,
            identifier="10.1234/schema-fixture",
            source_id="schema-fixture",
            paper_id="papers/schema-fixture",
            origin_project_id="prj_1234567890abcdef12345678",
            activation_id="act_1234567890abcdef12345678",
            artifact_ids=(artifact["artifact_id"],),
        )
    findings.extend(
        validate_instance(
            artifact,
            artifact_schema,
            artifact_schema,
            label="register_evidence_artifact",
        )
    )
    findings.extend(
        validate_instance(
            acquisition_run,
            schema.get("$defs", {}).get("acquisitionRun", {}),
            schema,
            label="AcquisitionRun",
        )
    )
    findings.extend(
        validate_instance(
            artifact,
            schema.get("$defs", {}).get("artifactRecord", {}),
            schema,
            label="ArtifactRecord",
        )
    )
    legacy_artifact = {
        "schema": "rkf-evidence-artifact-v1",
        "evidence_id": "pdf_legacy-fixture",
        "source_id": "legacy-fixture",
        "artifact_type": "pdf",
        "status": "pdf_downloaded",
        "qc_status": "pending",
        "storage_path": "private_evidence/doi_pdf/legacy-fixture.pdf",
        "public_safe_pointer": "private_evidence/doi_pdf/legacy-fixture.pdf",
        "locators": [],
        "created": "2026-07-15",
        "updated": "2026-07-15",
    }
    findings.extend(
        validate_instance(
            legacy_artifact,
            artifact_schema,
            artifact_schema,
            label="legacy evidence artifact",
        )
    )
    return findings


def validate() -> list[str]:
    findings: list[str] = []
    schema = load_canonical_schema()
    definitions = schema.get("$defs", {})
    missing_definitions = sorted(REQUIRED_DEFINITIONS - set(definitions))
    if missing_definitions:
        findings.append(f"canonical schema missing definitions: {', '.join(missing_definitions)}")
    for name, runtime_values in EXPECTED_ENUMS.items():
        try:
            schema_values = canonical_enum(name)
        except (TypeError, ValueError) as exc:
            findings.append(str(exc))
            continue
        if runtime_values != schema_values:
            findings.append(
                f"runtime enum drift for {name}: {runtime_values!r} != {schema_values!r}"
            )
        if len(runtime_values) != len(set(runtime_values)):
            findings.append(f"runtime enum {name} contains duplicate values")

    access = set(ACCESS_STATES)
    review = set(REVIEW_STATES)
    for legacy, mapped in LEGACY_READING_MAP.items():
        if mapped[0] not in access or mapped[1] not in review:
            findings.append(f"legacy mapping {legacy!r} points outside canonical enums")
    template = (REPO / "templates" / "rkf" / "paper.md").read_text(encoding="utf-8")
    for field in ("access_state: metadata", "review_state: unread"):
        if field not in template:
            findings.append(f"paper template missing canonical field {field}")
    findings.extend(runtime_payload_findings(schema))
    return findings


def main() -> int:
    findings = validate()
    if findings:
        for finding in findings:
            print(f"schema validation error: {finding}", file=sys.stderr)
        return 1
    print("rkf canonical schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
