from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import test_paper_acquisition as tool


class PaperAcquisitionToolTests(unittest.TestCase):
    def test_main_reruns_old_json_and_writes_the_layered_summary(self) -> None:
        class Result:
            @staticmethod
            def public_payload():
                return {
                    "status": "obtained",
                    "provider": "fixture-provider",
                    "provider_version": "1",
                    "route": "fixture-route",
                    "artifact_sha256": "b" * 64,
                    "pdf_magic_validated": True,
                    "private_artifact_available": True,
                    "quality_state": "readable",
                    "identity_state": "verified",
                    "text_layer_state": "available",
                    "locator_readiness": "ready",
                    "page_count": 4,
                    "blocker_codes": [],
                }

        class Provider:
            name = "fixture-provider"
            version = "1"
            requests = []

            def __init__(self, **_: object) -> None:
                type(self).requests = []

            def acquire(self, request):
                type(self).requests.append(request)
                return Result()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_report = root / "old.json"
            citation = "Detailed atmospheric model evaluation https://example.org/paper.pdf"
            old_report.write_text(
                json.dumps(
                    {
                        "schema": tool.REPORT_SCHEMA,
                        "results": [{"index": 7, "citation": citation}],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "new-run"
            stdout = io.StringIO()

            with patch.object(tool, "PortableScientificAcquisitionProvider", Provider):
                with contextlib.redirect_stdout(stdout):
                    status = tool.main(
                        [
                            str(old_report),
                            "--output-dir",
                            str(output),
                            "--workers",
                            "1",
                        ]
                    )

            summary = json.loads(
                (output / tool.JSON_REPORT_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(status, 0)
            self.assertEqual(summary["input_kind"], "smoke-report-json")
            self.assertEqual(summary["downloaded_count"], 1)
            self.assertEqual(summary["research_ready_verified_count"], 1)
            self.assertEqual(summary["route_counts"], {"fixture-route": 1})
            self.assertEqual(
                summary["provider_status_counts"],
                {"fixture-provider": {"obtained": 1}},
            )
            self.assertEqual(summary["promotion"], "none")
            self.assertEqual(
                Provider.requests[0].expected_title,
                "Detailed atmospheric model evaluation",
            )
            self.assertNotIn(str(output), stdout.getvalue())

    def test_output_directory_rejects_repo_symlinks_and_existing_targets(self) -> None:
        repo_target = tool.REPO / ".unsafe-acquisition-smoke-output"
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            tool.prepare_output_directory(repo_target)
        self.assertFalse(repo_target.exists())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "actual"
            actual.mkdir()
            linked = root / "linked"
            linked.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "cannot contain symlinks"):
                tool.prepare_output_directory(linked / "run")

            output = root / "existing"
            output.mkdir()
            (output / tool.JSON_REPORT_NAME).write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                tool.prepare_output_directory(output)

    def test_private_report_write_is_owner_only_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = tool.prepare_output_directory(Path(directory) / "run")
            report = output / "fixture.json"

            tool.write_private_text(report, "private\n")

            self.assertEqual(report.read_text(encoding="utf-8"), "private\n")
            self.assertEqual(report.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(FileExistsError):
                tool.write_private_text(report, "replacement\n")
            self.assertEqual(report.read_text(encoding="utf-8"), "private\n")

    def test_old_smoke_json_can_be_loaded_for_a_new_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "old-results.json"
            report.write_text(
                json.dumps(
                    {
                        "schema": tool.REPORT_SCHEMA,
                        "source_count": 2,
                        "status_counts": {"manual-required": 2},
                        "results": [
                            {"index": 9, "citation": "Second citation https://example.org/two.pdf"},
                            {"index": 3, "citation": "First citation https://example.org/one.pdf"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            indexed, input_kind = tool.load_indexed_citations(report)

            self.assertEqual(input_kind, "smoke-report-json")
            self.assertEqual([item[0] for item in indexed], [3, 9])
            self.assertEqual(
                tool.select_indexed_citations(indexed, indices="9", limit=0),
                [indexed[1]],
            )

    def test_public_atmospheric_corpus_can_be_loaded_for_live_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "atmospheric-corpus.json"
            corpus.write_text(
                json.dumps(
                    {
                        "corpus_id": tool.ATMOSPHERIC_CORPUS_ID,
                        "cases": [
                            {
                                "doi": "10.1029/2020AV000350",
                                "alternate_identifiers": ["NOAA:71054"],
                            },
                            {
                                "doi": "https://doi.org/10.5194/amt-17-5619-2024"
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            indexed, input_kind = tool.load_indexed_citations(corpus)

            self.assertEqual(input_kind, "atmospheric-journal-corpus")
            self.assertEqual(
                indexed,
                [
                    (1, "10.1029/2020av000350 NOAA:71054"),
                    (2, "10.5194/amt-17-5619-2024"),
                ],
            )

    def test_public_atmospheric_corpus_rejects_duplicate_or_non_doi_cases(self) -> None:
        payloads = (
            {
                "corpus_id": tool.ATMOSPHERIC_CORPUS_ID,
                "cases": [{"doi": "10.5194/example"}, {"doi": "10.5194/example"}],
            },
            {
                "corpus_id": tool.ATMOSPHERIC_CORPUS_ID,
                "cases": [{"doi": "https://example.org/article.pdf"}],
            },
            {
                "corpus_id": tool.ATMOSPHERIC_CORPUS_ID,
                "cases": [
                    {
                        "doi": "10.5194/example",
                        "alternate_identifiers": "NOAA:71054",
                    }
                ],
            },
        )
        for payload in payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                corpus = Path(directory) / "invalid-corpus.json"
                corpus.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    tool.load_indexed_citations(corpus)

    def test_public_atmospheric_corpus_quotes_url_spaces_without_losing_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "atmospheric-corpus.json"
            corpus.write_text(
                json.dumps(
                    {
                        "corpus_id": tool.ATMOSPHERIC_CORPUS_ID,
                        "cases": [
                            {
                                "doi": "10.1080/example",
                                "alternate_identifiers": [
                                    "https://repository.example/accepted manuscript.pdf"
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            indexed, _input_kind = tool.load_indexed_citations(corpus)

            self.assertEqual(
                indexed,
                [
                    (
                        1,
                        "10.1080/example "
                        "https://repository.example/accepted%20manuscript.pdf",
                    )
                ],
            )

    def test_selection_and_runtime_arguments_fail_closed(self) -> None:
        indexed = [(1, "one"), (2, "two")]
        for invalid in ("0", "1,x", "1,", "-1"):
            with self.subTest(indices=invalid):
                with self.assertRaisesRegex(ValueError, "positive integers"):
                    tool.select_indexed_citations(indexed, indices=invalid, limit=0)
        with self.assertRaisesRegex(ValueError, "not present"):
            tool.select_indexed_citations(indexed, indices="3", limit=0)
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            tool.select_indexed_citations(indexed, indices="", limit=-1)

        args = argparse.Namespace(
            workers=5,
            limit=0,
            artifact_timeout=35.0,
            metadata_timeout=12.0,
        )
        with self.assertRaisesRegex(ValueError, "workers"):
            tool.validate_runtime_arguments(args)
        args.workers = 1
        args.metadata_timeout = float("nan")
        with self.assertRaisesRegex(ValueError, "positive finite"):
            tool.validate_runtime_arguments(args)

    def test_expected_title_removes_every_identifier(self) -> None:
        url = "https://example.org/report.pdf"
        typed = "NOAA:55689"
        citation = f"Tewari and colleagues WRF model technical report {url} {typed}"

        expected = tool.expected_title_from_citation(citation, [url, typed])

        self.assertEqual(expected, "Tewari and colleagues WRF model technical report")
        self.assertNotEqual(expected, citation)
        self.assertNotIn(url, expected)
        self.assertNotIn(typed, expected)

    def test_summary_separates_downloaded_from_research_ready_verified(self) -> None:
        digest = "a" * 64
        ready = {
            "index": 1,
            "citation": "Ready citation",
            "identifier": "10.1234/ready",
            "status": "obtained",
            "provider": "fixture",
            "route": "oa-pdf",
            "artifact_sha256": digest,
            "pdf_magic_validated": True,
            "private_artifact_available": True,
            "quality_state": "readable",
            "identity_state": "verified",
            "text_layer_state": "available",
            "locator_readiness": "ready",
            "page_count": 10,
        }
        downloaded_unverified = {
            **ready,
            "index": 2,
            "citation": "Unverified citation",
            "identifier": "NOAA:55689",
            "route": "noaa-ir-main-pdf",
            "identity_state": "unverified",
        }
        manual = {
            "index": 3,
            "citation": "Manual citation",
            "identifier": "10.1234/manual",
            "status": "manual-required",
        }

        summary = tool.build_summary(
            [ready, downloaded_unverified, manual],
            input_kind="citation-lines",
            input_source_count=3,
            contact_email_configured=False,
            external_qc_tools=True,
        )

        self.assertEqual(summary["downloaded_count"], 2)
        self.assertEqual(summary["research_ready_verified_count"], 1)
        self.assertEqual(summary["status_counts"], {"manual-required": 1, "obtained": 2})
        self.assertEqual(
            summary["route_counts"],
            {"noaa-ir-main-pdf": 1, "oa-pdf": 1},
        )
        self.assertEqual(
            summary["provider_status_counts"],
            {
                "fixture": {"obtained": 2},
                "not-run": {"manual-required": 1},
            },
        )
        self.assertEqual(summary["promotion"], "none")
        self.assertTrue(summary["results"][0]["research_ready_verified"])
        self.assertFalse(summary["results"][1]["research_ready_verified"])


if __name__ == "__main__":
    unittest.main()
