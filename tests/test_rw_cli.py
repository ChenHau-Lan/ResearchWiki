#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "rw.py"


class ResearchWikiCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env["RESEARCHWIKI_ROOT"] = str(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_rw(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"rw.py failed: {result.args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def test_source_acquisition_requires_checkpoint(self) -> None:
        doi = "https://doi.org/10.1234/ABC.Def"
        key = "10_1234_abc_def"
        sample_pdf = self.root / "sample.pdf"
        sample_pdf.write_bytes(b"%PDF-1.4\n% tiny fixture\n")

        self.run_rw("source", "add", doi)
        self.run_rw("source", "acquire", doi, "--pdf", str(sample_pdf), "--key", key)

        self.assertFalse((self.root / "raw" / "doi_pdf" / f"{key}.pdf").exists())
        checkpoint = self.root / "maintenance" / "acquisition_checkpoints" / f"{key}.md"
        self.assertTrue(checkpoint.exists())
        dashboard = (self.root / "raw" / "doi_dashboard.md").read_text(encoding="utf-8")
        self.assertIn("pdf_checkpoint_required", dashboard)

        self.run_rw("source", "acquire", doi, "--pdf", str(sample_pdf), "--key", key, "--checkpoint", "approved")
        self.assertTrue((self.root / "raw" / "doi_pdf" / f"{key}.pdf").exists())
        dashboard = (self.root / "raw" / "doi_dashboard.md").read_text(encoding="utf-8")
        self.assertIn("pdf_downloaded", dashboard)

    def test_paper_ingest_rejects_unqced_full_text(self) -> None:
        raw = self.root / "raw" / "full_text"
        raw.mkdir(parents=True)
        bad = raw / "bad.md"
        bad.write_text(
            "---\nqc_status: pending_codex_qc\nextraction_status: machine_extracted_needs_codex_qc\n---\n\nBody\n",
            encoding="utf-8",
        )
        result = self.run_rw("paper", "ingest", "bad", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not QCed", result.stderr + result.stdout)

    def test_qced_full_text_can_be_ingested(self) -> None:
        source = self.root / "qced.md"
        source.write_text("# A Test Paper\n\nReadable checked text.\n", encoding="utf-8")

        self.run_rw(
            "source",
            "qc",
            "--identifier",
            "10.1234/test.paper",
            "--key",
            "smith_2026_j",
            "--full-text",
            str(source),
            "--title",
            "A Test Paper",
        )
        self.run_rw("paper", "ingest", "smith_2026_j")

        page = self.root / "wiki" / "literature" / "smith_2026_j.md"
        self.assertTrue(page.exists())
        text = page.read_text(encoding="utf-8")
        self.assertIn("reading_status: full-read", text)
        self.assertIn("## Fan-out Candidates", text)

    def test_topic_registry_lint(self) -> None:
        self.run_rw(
            "topic",
            "add",
            "wildfire-cloud",
            "Wildfire Cloud",
            "--scope",
            "Wildfire aerosol and cloud interaction",
            "--search",
            "wildfire aerosol cloud interaction",
            "--no-page",
        )
        result = self.run_rw("topic", "lint")
        self.assertIn("topic lint passed", result.stdout)

    def test_offline_search_writes_run_without_candidates_as_evidence(self) -> None:
        self.run_rw("source", "search", "wildfire aerosol cloud interaction", "--topic-id", "wildfire-cloud")
        runs = list((self.root / "maintenance" / "search_runs").glob("*"))
        self.assertEqual(len(runs), 1)
        candidates = (runs[0] / "candidates.json").read_text(encoding="utf-8")
        self.assertIn('"candidates": []', candidates)


if __name__ == "__main__":
    unittest.main()
