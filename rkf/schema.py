"""Canonical RKF v1 enums and conservative legacy normalization.

The JSON schema is the source of truth for canonical enum values.  This module
only exposes typed Python views of those values plus the explicit compatibility
mapping for legacy paper metadata.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CANONICAL_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "schemas" / "rkf_v1.schema.json"
)
SCHEMA_VERSION = "rkf-v1.1"


@lru_cache(maxsize=1)
def load_canonical_schema() -> dict[str, Any]:
    """Load the repository's canonical JSON schema exactly once."""

    return json.loads(CANONICAL_SCHEMA_PATH.read_text(encoding="utf-8"))


def canonical_enum(name: str) -> tuple[str, ...]:
    """Return one ordered enum from the canonical schema."""

    definition = load_canonical_schema().get("$defs", {}).get(name, {})
    values = definition.get("enum")
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError(f"canonical schema definition {name!r} must contain a string enum")
    if len(values) != len(set(values)):
        raise ValueError(f"canonical schema definition {name!r} contains duplicate values")
    return tuple(values)


ACCESS_STATES = canonical_enum("accessState")
REVIEW_STATES = canonical_enum("reviewState")
EVIDENCE_STANCES = canonical_enum("evidenceStance")
VERIFICATION_STATES = canonical_enum("verificationState")
CLAIM_STATUSES = canonical_enum("claimStatus")


LEGACY_READING_MAP: dict[str, tuple[str, str]] = {
    "metadata-only": ("metadata", "unread"),
    "abstract-only": ("abstract", "unread"),
    "abstract-read": ("abstract", "read"),
    "skimmed": ("partial", "skimmed"),
    "partial-fulltext": ("partial", "read"),
    "fulltext-available": ("fulltext", "unread"),
    "first-pass-pdf-qc": ("fulltext", "skimmed"),
    "ocr-qc": ("fulltext", "skimmed"),
    "visual-qc": ("fulltext", "skimmed"),
    "fulltext-read": ("fulltext", "read"),
    "full-read": ("fulltext", "read"),
    "human-reviewed": ("fulltext", "annotated"),
    "synthesis-ready": ("fulltext", "annotated"),
    "reproduced": ("fulltext", "reproduced"),
}


def normalize_paper_state(meta: dict[str, Any]) -> dict[str, str]:
    """Return canonical paper states without inventing unsupported maturity."""

    access = str(meta.get("access_state", "")).strip()
    review = str(meta.get("review_state", "")).strip()
    if access in ACCESS_STATES and review in REVIEW_STATES:
        return {"access_state": access, "review_state": review}
    legacy = str(meta.get("reading_state", meta.get("reading_status", "metadata-only")))
    mapped = LEGACY_READING_MAP.get(legacy)
    if mapped is None:
        return {"access_state": "metadata", "review_state": "unread"}
    return {"access_state": mapped[0], "review_state": mapped[1]}


def enum_findings(meta: dict[str, Any]) -> list[str]:
    normalized = normalize_paper_state(meta)
    findings: list[str] = []
    if meta.get("access_state") and meta.get("access_state") not in ACCESS_STATES:
        findings.append(f"unknown access_state: {meta['access_state']}")
    if meta.get("review_state") and meta.get("review_state") not in REVIEW_STATES:
        findings.append(f"unknown review_state: {meta['review_state']}")
    legacy = meta.get("reading_state", meta.get("reading_status"))
    if legacy and legacy not in LEGACY_READING_MAP and not (
        meta.get("access_state") in ACCESS_STATES and meta.get("review_state") in REVIEW_STATES
    ):
        findings.append(f"unmapped legacy reading state: {legacy}")
    if normalized["access_state"] not in ACCESS_STATES or normalized["review_state"] not in REVIEW_STATES:
        findings.append("paper state normalization failed")
    return findings
