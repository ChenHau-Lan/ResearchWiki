"""Canonical RKF v1 enums and conservative legacy normalization."""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "rkf-v1.1"
ACCESS_STATES = ("metadata", "abstract", "partial", "fulltext")
REVIEW_STATES = ("unread", "skimmed", "read", "annotated", "reproduced")
EVIDENCE_STANCES = ("supports", "opposes", "contextualizes")
VERIFICATION_STATES = ("unreviewed", "human-verified", "rejected")
CLAIM_STATUSES = ("proposed", "supported", "disputed", "verified", "retired")


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
