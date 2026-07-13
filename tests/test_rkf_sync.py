from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from rkf.core import Workspace
from rkf.sync import atomic_write_text, run_connect_doctor, sha256_file


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class RKFDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.repo.mkdir()
        self.wiki.mkdir()
        self.raw.mkdir()
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.wiki.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-sync"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        self.sync_root = self.wiki / "state" / "sync"
        self.sync_root.mkdir(parents=True)
        (self.sync_root / "maintenance-writer.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-writer-registry-v1",
                    "machine_id": "machine-sync",
                    "assigned_at": "2026-07-11T12:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        self.workspace = Workspace(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_doctor_is_read_only_and_masks_paths(self) -> None:
        before = file_snapshot(self.root)

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))

        self.assertEqual(file_snapshot(self.root), before)
        self.assertEqual(report.status, "ok")
        payload = report.as_payload()
        self.assertNotIn(str(self.root), json.dumps(payload))
        self.assertEqual(payload["roots"]["wiki_root"], {"exists": True, "readable": True})
        self.assertEqual(payload["writer"]["role"], "designated")

    def test_conflict_copy_and_writer_mismatch_are_blockers(self) -> None:
        (self.wiki / "paper.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
        (self.sync_root / "maintenance-writer.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-writer-registry-v1",
                    "machine_id": "other-machine",
                    "assigned_at": "2026-07-11T12:00:00Z",
                }
            ),
            encoding="utf-8",
        )

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))

        self.assertEqual(report.status, "blocked")
        self.assertEqual({finding.code for finding in report.findings}, {"SYNC_CONFLICT", "WRITER_REGISTRY_MISMATCH"})

    def test_divergent_pdf_checksums_are_blockers(self) -> None:
        doi_pdf = self.raw / "doi_pdf"
        files = self.raw / "files"
        doi_pdf.mkdir()
        files.mkdir()
        first = doi_pdf / "download-one.pdf"
        second = files / "download-two.pdf"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        self._write_pdf_evidence("pdf_one", "doi_example", "doi_pdf/download-one.pdf")
        self._write_pdf_evidence("pdf_two", "doi_example", "files/download-two.pdf")

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))

        self.assertEqual(report.status, "blocked")
        finding = next(item for item in report.findings if item.code == "PDF_CHECKSUM_CONFLICT")
        self.assertEqual(finding.details["identity"], "doi_example")

    def test_same_filename_stem_for_different_governed_sources_is_not_a_conflict(self) -> None:
        first = self.raw / "source-a" / "shared.pdf"
        second = self.raw / "source-b" / "shared.pdf"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        self._write_pdf_evidence("pdf_a", "doi_source_a", "source-a/shared.pdf")
        self._write_pdf_evidence("pdf_b", "doi_source_b", "source-b/shared.pdf")

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))

        self.assertEqual(report.status, "ok")
        self.assertFalse(any(item.code == "PDF_CHECKSUM_CONFLICT" for item in report.findings))

    def test_raw_conflict_copy_is_a_blocker_even_when_pdf_identity_is_unverified(self) -> None:
        (self.raw / "same-doi.pdf").write_bytes(b"first")
        (self.raw / "same-doi (conflicted copy).pdf").write_bytes(b"second")

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))

        self.assertEqual(report.status, "blocked")
        self.assertTrue(any(item.code == "SYNC_CONFLICT" for item in report.findings))

    def test_stale_aggregate_uses_injected_clock(self) -> None:
        (self.sync_root / "aggregate-status.json").write_text(
            json.dumps(
                {
                    "aggregates": [
                        {"logical_id": "index.md", "generated_at": "2026-07-09T08:00:00Z"}
                    ]
                }
            ),
            encoding="utf-8",
        )

        report = run_connect_doctor(
            self.workspace,
            now=datetime(2026, 7, 11, 9, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report.status, "warning")
        finding = next(item for item in report.findings if item.code == "STALE_AGGREGATE")
        self.assertEqual(finding.details["logical_id"], "index.md")

    def test_untrusted_aggregate_logical_id_is_redacted(self) -> None:
        (self.sync_root / "aggregate-status.json").write_text(
            json.dumps(
                {
                    "aggregates": [
                        {
                            "logical_id": str(self.root / "private" / "aggregate.md"),
                            "generated_at": "2026-07-09T08:00:00Z",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        report = run_connect_doctor(
            self.workspace,
            now=datetime(2026, 7, 11, 9, 0, 0, tzinfo=timezone.utc),
        )
        payload = report.as_payload()

        finding = next(item for item in payload["findings"] if item["code"] == "STALE_AGGREGATE")
        self.assertEqual(finding["details"]["logical_id"], "redacted")
        self.assertNotIn(str(self.root), json.dumps(payload))

    def test_unverified_pdf_findings_are_aggregated(self) -> None:
        for index in range(3):
            (self.raw / f"unmapped-{index}.pdf").write_bytes(f"pdf-{index}".encode())

        report = run_connect_doctor(self.workspace, now=datetime(2026, 7, 11, 9, 0, 0))
        findings = [item for item in report.findings if item.code == "PDF_IDENTITY_UNVERIFIED"]

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].details["count"], 3)

    def _write_pdf_evidence(self, evidence_id: str, source_id: str, storage_path: str) -> None:
        evidence_root = self.wiki / "state" / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / f"{evidence_id}.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-evidence-artifact-v1",
                    "evidence_id": evidence_id,
                    "source_id": source_id,
                    "artifact_type": "pdf",
                    "storage_path": storage_path,
                    "status": "pdf_downloaded",
                    "qc_status": "pending",
                    "public_safe_pointer": "private reference",
                }
            ),
            encoding="utf-8",
        )


class RKFAtomicWriteTests(unittest.TestCase):
    def test_checksum_mismatch_preserves_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            target = Path(tmp_name) / "named-file.txt"
            target.write_text("before\n", encoding="utf-8")

            result = atomic_write_text(target, "next\n", expected_checksum="not-the-current-checksum")

            self.assertFalse(result.written)
            self.assertEqual(result.reason, "checksum-mismatch")
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

    def test_atomic_write_verifies_output_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            target = Path(tmp_name) / "named-file.txt"
            target.write_text("before\n", encoding="utf-8")
            before = sha256_file(target)

            result = atomic_write_text(target, "next\n", expected_checksum=before)

            self.assertTrue(result.written)
            self.assertEqual(result.reason, "ok")
            self.assertEqual(result.output_checksum, sha256_file(target))
            self.assertEqual(target.read_text(encoding="utf-8"), "next\n")


if __name__ == "__main__":
    unittest.main()
