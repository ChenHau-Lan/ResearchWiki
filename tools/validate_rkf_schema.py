#!/usr/bin/env python3
"""Validate the schema-first RKF v1 enum boundary.

This gate intentionally checks the canonical core only.  Legacy paper fields
remain compatibility inputs until the Phase 1 migration report and backup
window are complete.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from rkf.schema import (  # noqa: E402
    ACCESS_STATES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    LEGACY_READING_MAP,
    REVIEW_STATES,
    VERIFICATION_STATES,
    canonical_enum,
)


EXPECTED_ENUMS = {
    "accessState": ACCESS_STATES,
    "reviewState": REVIEW_STATES,
    "evidenceStance": EVIDENCE_STANCES,
    "verificationState": VERIFICATION_STATES,
    "claimStatus": CLAIM_STATUSES,
}


def validate() -> list[str]:
    findings: list[str] = []
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
