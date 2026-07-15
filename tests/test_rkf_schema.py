from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, approved_pdf_acquisition, verify_pdf
from rkf.schema import (
    ACCESS_STATES,
    APPRAISAL_STATUSES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    LEGACY_READING_MAP,
    REVIEW_STATES,
    VERIFICATION_STATES,
)
from rkf.providers import FullTextProviderResult
from tools.validate_rkf_schema import validate_instance


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
            "appraisalStatus": APPRAISAL_STATUSES,
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

    def test_fulltext_runtime_payload_matches_closed_canonical_schema(self) -> None:
        schema = json.loads(
            (REPO / "schemas" / "rkf_v1.schema.json").read_text(encoding="utf-8")
        )
        payload = FullTextProviderResult(
            status="obtained",
            provider="fixture",
            provider_version="1",
            artifact_sha256="a" * 64,
            private_artifact_handle="private://fixture",
            pdf_magic_validated=True,
        ).public_payload()
        definition = schema["$defs"]["fullTextProviderResult"]

        self.assertEqual(
            validate_instance(payload, definition, schema, label="fulltext provider"),
            [],
        )
        self.assertIs(payload["private_artifact_available"], True)
        drifted = {**payload, "unexpected_runtime_field": True}
        self.assertIn(
            "fulltext provider: unexpected property unexpected_runtime_field",
            validate_instance(drifted, definition, schema, label="fulltext provider"),
        )

    def test_evidence_artifact_relations_are_backward_compatible(self) -> None:
        schema = json.loads(
            (REPO / "schemas" / "evidence_artifact.schema.json").read_text(encoding="utf-8")
        )
        legacy = {
            "schema": "rkf-evidence-artifact-v1",
            "evidence_id": "pdf_legacy",
            "source_id": "legacy",
            "artifact_type": "pdf",
            "status": "pdf_downloaded",
            "qc_status": "pending",
            "public_safe_pointer": "private_evidence/doi_pdf/legacy.pdf",
        }
        canonical = {
            **legacy,
            "artifact_id": "art_1234567890abcdef12345678",
            "paper_id": "papers/current",
            "source_id": "current",
            "paper_ids": ["papers/legacy", "papers/current"],
            "source_ids": ["legacy", "current"],
        }

        self.assertEqual(validate_instance(legacy, schema, schema, label="legacy artifact"), [])
        self.assertEqual(validate_instance(canonical, schema, schema, label="canonical artifact"), [])
        duplicate = {**canonical, "paper_ids": ["papers/current", "papers/current"]}
        self.assertIn(
            "duplicate artifact.paper_ids: array items are not unique",
            validate_instance(duplicate, schema, schema, label="duplicate artifact"),
        )

    def test_core_verify_pdf_qc_notes_match_the_closed_artifact_schema(self) -> None:
        schema = json.loads(
            (REPO / "schemas" / "evidence_artifact.schema.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            source = {"source_id": "qc_fixture", "status": "new"}
            pdf = Path(directory) / "fixture.pdf"
            pdf.write_bytes(b"%PDF-1.4\nfixture\n")
            approved_pdf_acquisition(workspace, source, pdf)
            artifact = verify_pdf(
                workspace,
                source,
                locator="p. 1",
                note="Identity and locator checked.",
            )

        self.assertEqual(validate_instance(artifact, schema, schema, label="verify_pdf artifact"), [])
        self.assertEqual(artifact["qc_notes"][0]["note"], "Identity and locator checked.")


if __name__ == "__main__":
    unittest.main()
