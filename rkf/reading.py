"""Deterministic scope and inference gates for the RKF v1 Read workflow."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from .core import Workspace
from .lineage import ACTIVATION_ID_RE, PROJECT_ID_RE, input_fingerprint, utc_now
from .providers import AppraisalProvider
from .research import (
    canonical_state_json_path,
    load_canonical_paper,
    read_canonical_state_json,
    record_evidence,
    write_canonical_state_json,
)
from .schema import READ_INTENTS, READING_SCOPES


@dataclass(frozen=True)
class ReadScopeBlocked(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


INFERENCE_GAP_RULES = {
    ("association", "causal"): "ASSOCIATION_TO_CAUSATION",
    ("surrogate-outcome", "hard-outcome"): "SURROGATE_TO_HARD_OUTCOME",
    ("single-study", "consistency"): "SINGLE_STUDY_TO_CONSISTENCY",
    ("subgroup", "general-benefit"): "SUBGROUP_TO_GENERAL_BENEFIT",
    ("secondary-outcome", "general-benefit"): "SECONDARY_TO_GENERAL_BENEFIT",
    ("mechanistic-plausibility", "outcome"): "MECHANISM_TO_OUTCOME",
    ("expert-opinion", "outcome"): "OPINION_TO_OUTCOME",
}
READ_RUN_ID_RE = re.compile(r"^read_[a-f0-9]{24}$")


def lint_inference_gaps(checks: list[dict[str, Any]]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("inference_checks must contain objects")
        evidence_kind = str(check.get("evidence_kind", "")).strip()
        claim_kind = str(check.get("claim_kind", "")).strip()
        code = INFERENCE_GAP_RULES.get((evidence_kind, claim_kind))
        if code:
            statement = str(check.get("statement", "")).strip()
            flags.append(
                {
                    "code": code,
                    "evidence_kind": evidence_kind,
                    "claim_kind": claim_kind,
                    "statement_fingerprint": input_fingerprint({"text": statement}) if statement else "",
                }
            )
    return flags


def validate_citation_checks(checks: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    warnings: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("citation_checks must contain objects")
        citation = str(check.get("citation", "")).strip()
        check_status = str(check.get("check_status", "ok")).strip()
        if check_status != "ok":
            raw_reason = str(check.get("reason", "external check did not complete"))
            reason_code = re.sub(r"[^A-Z0-9]+", "_", raw_reason.upper()).strip("_")[:64]
            failures.append(
                {
                    "code": "CITATION_CHECK_FAILED",
                    "citation": citation,
                    "reason_code": reason_code or "EXTERNAL_CHECK_DID_NOT_COMPLETE",
                }
            )
            continue
        if check.get("exists") is not True:
            warnings.append({"code": "CITATION_NOT_CONFIRMED", "citation": citation})
            continue
        if check.get("identity_matches") is False:
            warnings.append({"code": "CITATION_IDENTITY_MISMATCH", "citation": citation})
            continue
        if check.get("supports_claim") is not True:
            warnings.append(
                {
                    "code": "CITATION_SUPPORT_NOT_CONFIRMED",
                    "citation": citation,
                }
            )
    return warnings, failures


def run_read_pass(
    ws: Workspace,
    *,
    paper_id: str,
    intent: str,
    reading_scope: str,
    origin_project_id: str,
    activation_id: str,
    findings: list[dict[str, Any]] | None = None,
    citation_checks: list[dict[str, Any]] | None = None,
    inference_checks: list[dict[str, Any]] | None = None,
    appraisal_profile: str = "generic",
    appraisal_provider: AppraisalProvider | None = None,
) -> dict[str, Any]:
    if intent not in READ_INTENTS:
        raise ValueError("intent must be digest, appraise, or both")
    if reading_scope not in READING_SCOPES:
        raise ValueError("invalid reading_scope")
    paper_id, paper_meta = load_canonical_paper(ws, paper_id=paper_id)
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("Read requires valid project/activation lineage")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", appraisal_profile):
        raise ValueError("invalid appraisal_profile")
    if appraisal_profile != "generic" and appraisal_provider is None:
        raise ValueError("non-generic appraisal profiles require an optional provider")
    if intent in {"digest", "both"} and reading_scope != "fulltext":
        raise ReadScopeBlocked(
            "RKF_READ_NEEDS_FULLTEXT",
            "digest requires full text; record a needs-fulltext blocker instead",
        )
    scope_rank = {value: index for index, value in enumerate(READING_SCOPES)}
    paper_access_state = str(paper_meta["access_state"])
    if scope_rank[reading_scope] > scope_rank[paper_access_state]:
        if intent in {"digest", "both"}:
            raise ReadScopeBlocked(
                "RKF_READ_NEEDS_FULLTEXT",
                "digest requires a canonical Paper with full-text access",
            )
        raise ReadScopeBlocked(
            "RKF_READ_SCOPE_EXCEEDS_ACCESS",
            "reading_scope exceeds the canonical Paper access_state",
        )

    normalized_findings = findings or []
    normalized_citations = citation_checks or []
    normalized_inferences = inference_checks or []
    if not all(isinstance(item, dict) for item in normalized_findings):
        raise ValueError("findings must contain objects")
    citation_warnings, failed_checks = validate_citation_checks(normalized_citations)
    inference_flags = lint_inference_gaps(normalized_inferences)
    appraisal = {
        "status": "completed",
        "provider": "deterministic-core",
        "provider_version": "rkf-read-gates-v1",
        "profile": "generic",
        "flags": [],
        "warnings": [],
        "failures": [],
    }
    if appraisal_provider is not None and appraisal_profile != "generic":
        try:
            provider_result = appraisal_provider.appraise(
                paper_id=paper_id,
                profile=appraisal_profile,
                project_id=origin_project_id,
                activation_id=activation_id,
            )
            appraisal = provider_result.public_payload()
        except (OSError, RuntimeError, TypeError, ValueError):
            appraisal = {
                "status": "blocked",
                "provider": "optional-appraisal",
                "provider_version": "unknown",
                "profile": appraisal_profile,
                "flags": [],
                "warnings": [],
                "failures": ["APPRAISAL_PROVIDER_FAILED"],
            }
        for code in appraisal["failures"]:
            failed_checks.append({"code": code, "citation": "", "reason_code": "OPTIONAL_APPRAISAL_FAILED"})

    evidence_ids: list[str] = []
    object_fingerprints: dict[str, str] = {}
    for finding in normalized_findings:
        locator = finding.get("locator", {})
        if not isinstance(locator, dict):
            raise ValueError("each finding requires a locator object")
        verification_state = str(finding.get("verification_state", "unreviewed"))
        if reading_scope != "fulltext" and verification_state == "human-verified":
            raise ValueError("abstract/partial Read cannot create human-verified evidence")
        evidence = record_evidence(
            ws,
            paper_id=paper_id,
            summary=str(finding.get("summary", "")),
            locator_kind=str(locator.get("kind", "")),
            locator_value=str(locator.get("value", "")),
            stance=str(finding.get("stance", "contextualizes")),
            verification_state=verification_state,
            governed_reading_scope=reading_scope,
            origin_project_id=origin_project_id,
            activation_id=activation_id,
        )
        evidence_id = str(evidence["evidence_id"])
        evidence_ids.append(evidence_id)
        object_fingerprints[evidence_id] = str(evidence["content_fingerprint"])

    run_input = {
        "paper_id": paper_id,
        "intent": intent,
        "reading_scope": reading_scope,
        "findings": normalized_findings,
        "citation_checks": normalized_citations,
        "inference_checks": normalized_inferences,
        "appraisal_profile": appraisal_profile,
        "appraisal": appraisal,
    }
    fingerprint = input_fingerprint(run_input)
    read_run_id = "read_" + hashlib.sha256(
        f"{activation_id}\0{fingerprint}".encode("utf-8")
    ).hexdigest()[:24]
    argument_map = {
        "paper_id": paper_id,
        "evidence_ids": evidence_ids,
        "citation_warnings": citation_warnings,
        "inference_flags": inference_flags,
        "appraisal_flags": appraisal["flags"],
    }
    trust = "low" if reading_scope != "fulltext" or inference_flags or failed_checks or appraisal["flags"] or appraisal["status"] != "completed" else "bounded"
    payload = {
        "schema": "rkf-read-run-v1",
        "read_run_id": read_run_id,
        "paper_id": paper_id,
        "intent": intent,
        "reading_scope": reading_scope,
        "appraisal_profile": appraisal_profile,
        "evidence_ids": evidence_ids,
        "citation_warnings": citation_warnings,
        "inference_flags": inference_flags,
        "failed_checks": failed_checks,
        "argument_map": argument_map,
        "appraisal": appraisal,
        "trust": trust,
        "validator_version": "rkf-read-gates-v1",
        "input_fingerprint": fingerprint,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "created": utc_now(),
        "promotion": "none",
        "public_safe": True,
        "object_fingerprints": object_fingerprints,
    }
    path = canonical_state_json_path(
        ws,
        collection=("read_runs",),
        object_id=read_run_id,
        id_pattern=READ_RUN_ID_RE,
        label="read run",
        create_parent=True,
    )
    if path.exists():
        existing = read_canonical_state_json(path, label="read run")
        if existing.get("schema") != "rkf-read-run-v1" or existing.get("read_run_id") != read_run_id:
            raise ValueError("existing canonical Read run has invalid schema/id")
        return existing
    write_canonical_state_json(path, payload, label="read run")
    return payload
