from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from rkf.schema import (
    ACCESS_STATES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    LEGACY_READING_MAP,
    REVIEW_STATES,
    VERIFICATION_STATES,
)


REPO = Path(__file__).resolve().parents[1]


class RKFSchemaTests(unittest.TestCase):
    def test_runtime_enums_are_derived_from_the_canonical_schema(self) -> None:
        schema = json.loads(
            (REPO / "schemas" / "rkf_v1.schema.json").read_text(encoding="utf-8")
        )
        expected = {
            "accessState": ACCESS_STATES,
            "reviewState": REVIEW_STATES,
            "evidenceStance": EVIDENCE_STANCES,
            "verificationState": VERIFICATION_STATES,
            "claimStatus": CLAIM_STATUSES,
        }
        for name, runtime_values in expected.items():
            self.assertEqual(tuple(schema["$defs"][name]["enum"]), runtime_values)

    def test_legacy_mapping_targets_canonical_values(self) -> None:
        for access_state, review_state in LEGACY_READING_MAP.values():
            self.assertIn(access_state, ACCESS_STATES)
            self.assertIn(review_state, REVIEW_STATES)

    def test_schema_validation_gate_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/validate_rkf_schema.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("canonical schema validation passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
