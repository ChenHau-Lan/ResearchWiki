"""The five RKF v1 research workflows built on canonical objects."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .core import Workspace, knowledge_page_records, read_json, slugify, write_json
from .lineage import activity_timeline, utc_now
from .schema import (
    ACCESS_STATES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    REVIEW_STATES,
    VERIFICATION_STATES,
    enum_findings,
    normalize_paper_state,
)


LOCATOR_KINDS = {"page", "section", "figure", "table", "paragraph"}


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def record_evidence(
    ws: Workspace,
    *,
    paper_id: str,
    summary: str,
    locator_kind: str,
    locator_value: str,
    stance: str = "contextualizes",
    verification_state: str = "unreviewed",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    if locator_kind not in LOCATOR_KINDS or not locator_value.strip():
        raise ValueError("evidence requires an exact page/section/figure/table/paragraph locator")
    if stance not in EVIDENCE_STANCES:
        raise ValueError("invalid evidence stance")
    if verification_state not in VERIFICATION_STATES:
        raise ValueError("invalid evidence verification state")
    evidence_id = _stable_id("ev", paper_id, locator_kind, locator_value, summary)
    payload = {
        "schema": "rkf-evidence-v1",
        "evidence_id": evidence_id,
        "paper_id": paper_id,
        "locator": {"kind": locator_kind, "value": locator_value.strip()},
        "summary": summary.strip(),
        "stance": stance,
        "verification_state": verification_state,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "created": utc_now(),
        "public_safe": True,
    }
    path = ws.paths.evidence_index / "cards" / f"{evidence_id}.json"
    if path.exists():
        existing = read_json(path)
        if existing != payload:
            payload["created"] = existing.get("created", payload["created"])
            payload["updated"] = utc_now()
    write_json(path, payload)
    return payload


def record_claim(
    ws: Workspace,
    *,
    statement: str,
    evidence_ids: list[str],
    status: str = "proposed",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    if status not in CLAIM_STATUSES:
        raise ValueError("invalid claim status")
    evidence: list[dict[str, Any]] = []
    for evidence_id in evidence_ids:
        path = ws.paths.evidence_index / "cards" / f"{evidence_id}.json"
        if not path.exists():
            raise ValueError(f"unknown evidence: {evidence_id}")
        evidence.append(read_json(path))
    if status in {"supported", "disputed", "verified"} and not evidence:
        raise ValueError(f"{status} claim requires locator-backed evidence")
    if status == "verified" and not any(item.get("verification_state") == "human-verified" for item in evidence):
        raise ValueError("verified claim requires human-verified evidence")
    claim_id = _stable_id("clm", statement)
    payload = {
        "schema": "rkf-claim-v1",
        "claim_id": claim_id,
        "statement": statement.strip(),
        "supporting_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "supports"],
        "opposing_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "opposes"],
        "context_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "contextualizes"],
        "status": status,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "updated": utc_now(),
        "public_safe": True,
    }
    write_json(ws.paths.state / "claims" / f"{claim_id}.json", payload)
    return payload


def synthesize(
    ws: Workspace,
    *,
    research_question: str,
    claim_ids: list[str],
    provisional_conclusion: str = "",
    next_action: str = "",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    for claim_id in claim_ids:
        path = ws.paths.state / "claims" / f"{claim_id}.json"
        if not path.exists():
            raise ValueError(f"unknown claim: {claim_id}")
        claims.append(read_json(path))
    synthesis_id = _stable_id("syn", research_question)
    payload = {
        "schema": "rkf-synthesis-v1",
        "synthesis_id": synthesis_id,
        "research_question": research_question.strip(),
        "included_claim_ids": claim_ids,
        "agreements": [item["claim_id"] for item in claims if item.get("status") in {"supported", "verified"}],
        "contradictions": [item["claim_id"] for item in claims if item.get("status") == "disputed"],
        "evidence_gaps": [item["claim_id"] for item in claims if item.get("status") == "proposed"],
        "provisional_conclusion": provisional_conclusion.strip(),
        "next_action": next_action.strip(),
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "updated": utc_now(),
        "public_safe": True,
    }
    write_json(ws.paths.state / "syntheses" / f"{synthesis_id}.json", payload)
    return payload


def review_home(ws: Workspace, *, project_id: str = "", activation_id: str = "") -> dict[str, Any]:
    evidence = [read_json(path) for path in sorted((ws.paths.evidence_index / "cards").glob("*.json"))] if (ws.paths.evidence_index / "cards").exists() else []
    claims = [read_json(path) for path in sorted((ws.paths.state / "claims").glob("*.json"))] if (ws.paths.state / "claims").exists() else []
    syntheses = [read_json(path) for path in sorted((ws.paths.state / "syntheses").glob("*.json"))] if (ws.paths.state / "syntheses").exists() else []
    paper_findings: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    for path, meta, _ in knowledge_page_records(ws):
        if meta.get("type") != "paper":
            continue
        state = normalize_paper_state(meta)
        state_counts[f"{state['access_state']}:{state['review_state']}"] += 1
        findings = enum_findings(meta)
        if findings:
            paper_findings.append({"paper": path.stem, "findings": findings})
    return {
        "schema": "rkf-review-home-v1",
        "paper_state_counts": dict(state_counts),
        "paper_schema_findings": paper_findings,
        "evidence_pending_verification": [item["evidence_id"] for item in evidence if item.get("verification_state") == "unreviewed"],
        "claims_missing_locator": [item["claim_id"] for item in claims if item.get("status") == "proposed" and not any(item.get(key) for key in ("supporting_evidence_ids", "opposing_evidence_ids", "context_evidence_ids"))],
        "disputed_claims": [item["claim_id"] for item in claims if item.get("status") == "disputed"],
        "syntheses_with_gaps": [item["synthesis_id"] for item in syntheses if item.get("evidence_gaps")],
        "activity": activity_timeline(ws.root, project_id=project_id, activation_id=activation_id),
        "public_safe": True,
    }
