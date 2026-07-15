from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf.core import (
    Workspace,
    create_paper_note,
    create_source,
    frontmatter,
    write_text,
)
from rkf.providers import RetrievalHit
from rkf.query_index import RetrievalQueryIndex
from rkf.research import record_evidence
from rkf.retrieval import search_central_rkf


PROJECT_ID = "prj_1234567890abcdef12345678"
ACTIVATION_ID = "act_1234567890abcdef12345678"


class _SingleHitProvider:
    name = "query-index-fixture"
    version = "1"
    index_generation = "semantic-fixture"
    elapsed_ms = 0

    def __init__(self, object_id: str) -> None:
        self.object_id = object_id

    def search(self, **_: object) -> list[RetrievalHit]:
        return [
            RetrievalHit(
                object_id=self.object_id,
                score=1.0,
                match_reason="semantic",
                metadata={
                    "object_type": "evidence",
                    "index_scope": "public-safe",
                },
            )
        ]


class RKFQueryIndexIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_public_fixture(self, *, token: str = "indexed-retrieval-token") -> Path:
        record = create_source(
            self.workspace,
            kind="doi",
            value="10.1234/index.fixture",
            title="Indexed Retrieval Fixture",
            topic_id="query-index",
            note=f"Public-safe {token} source note.",
        )
        return create_paper_note(self.workspace, record)

    def _write_raw_evidence_candidates(
        self,
        *,
        count: int,
        token: str,
    ) -> dict[str, dict[str, object]]:
        cards_root = self.workspace.paths.evidence_index / "cards"
        cards_root.mkdir(parents=True)
        records: dict[str, dict[str, object]] = {}
        for index in range(count):
            evidence_id = f"ev_{index:020x}"
            record = {
                "evidence_id": evidence_id,
                "paper_id": "papers/fixture",
                "summary": f"{token} {index:02d}",
                "locator": {"kind": "page", "value": str(index + 1)},
                "verification_state": "unreviewed",
            }
            records[evidence_id] = record
            (cards_root / f"{evidence_id}.json").write_text(
                json.dumps(record),
                encoding="utf-8",
            )
        return records

    def _search(
        self,
        query: str,
        *,
        query_index: RetrievalQueryIndex | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        return search_central_rkf(
            self.workspace,
            query,
            query_index=query_index,
            persist_retrieval_run=False,
            **kwargs,
        )

    def test_indexed_and_full_scan_results_have_parity_and_warm_hit_reads_no_corpus(self) -> None:
        self._write_public_fixture()
        full_scan = self._search("indexed-retrieval-token")
        self.assertEqual(full_scan["deterministic_index"]["state"], "disabled")
        self.assertFalse((self.root / ".rkf_private").exists())

        query_index = RetrievalQueryIndex(self.root)
        cold = self._search("indexed-retrieval-token", query_index=query_index)
        self.assertEqual(cold["deterministic_index"]["state"], "rebuilt")
        self.assertGreater(cold["deterministic_index"]["source_files_read"], 0)

        with patch(
            "rkf.retrieval._read_regular_text",
            side_effect=AssertionError("warm index must not reread corpus contents"),
        ):
            warm = self._search("indexed-retrieval-token", query_index=query_index)

        self.assertEqual(warm["deterministic_index"]["state"], "hit")
        self.assertEqual(warm["deterministic_index"]["source_files_read"], 0)
        for result in (cold, warm):
            self.assertEqual(
                result["retrieval_result_fingerprint"],
                full_scan["retrieval_result_fingerprint"],
            )
            self.assertEqual(result["cards"], full_scan["cards"])
            self.assertEqual(result["graph_context"], full_scan["graph_context"])

    def test_index_state_does_not_change_result_or_retrieval_run_identity(self) -> None:
        self._write_public_fixture()
        full_scan = search_central_rkf(
            self.workspace,
            "indexed-retrieval-token",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )
        indexed = search_central_rkf(
            self.workspace,
            "indexed-retrieval-token",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
            query_index=RetrievalQueryIndex(self.root),
        )

        self.assertEqual(
            indexed["retrieval_result_fingerprint"],
            full_scan["retrieval_result_fingerprint"],
        )
        self.assertEqual(indexed["retrieval_run_id"], full_scan["retrieval_run_id"])
        self.assertEqual(indexed["cards"], full_scan["cards"])

    def test_index_timing_excludes_the_corpus_scan_stage(self) -> None:
        self._write_public_fixture()
        with patch(
            "rkf.retrieval._elapsed_ms",
            side_effect=[40.0, 55.0, 2.0, 3.0, 4.0, 5.0, 70.0],
        ):
            result = self._search("indexed-retrieval-token")

        self.assertEqual(result["timing"]["scan_ms"], 40.0)
        self.assertEqual(result["timing"]["index_ms"], 15.0)
        self.assertGreaterEqual(result["timing"]["index_ms"], 0.0)

    def test_stale_projection_rebuilds_without_changing_canonical_files(self) -> None:
        paper_path = self._write_public_fixture(token="before-stale")
        query_index = RetrievalQueryIndex(self.root)
        self._search("before-stale", query_index=query_index)
        canonical_paths = sorted(
            path.relative_to(self.root)
            for path in self.root.rglob("*")
            if path.is_file() and ".rkf_private" not in path.parts
        )

        with paper_path.open("a", encoding="utf-8") as handle:
            handle.write("\nprojection-stale-token\n")
        stale = self._search("projection-stale-token", query_index=query_index)

        self.assertEqual(stale["deterministic_index"]["state"], "rebuilt")
        self.assertEqual(
            stale["deterministic_index"]["reason"],
            "source-fingerprint-mismatch",
        )
        self.assertGreater(stale["deterministic_index"]["source_files_read"], 0)
        self.assertTrue(
            any(card["id"].startswith("papers/") for card in stale["cards"])
        )
        self.assertEqual(
            sorted(
                path.relative_to(self.root)
                for path in self.root.rglob("*")
                if path.is_file() and ".rkf_private" not in path.parts
            ),
            canonical_paths,
        )

    def test_corrupt_and_tampered_indexes_fall_back_to_full_scan(self) -> None:
        for case in ("corrupt", "tampered"):
            with self.subTest(case=case):
                self.tmp.cleanup()
                self.tmp = tempfile.TemporaryDirectory()
                self.root = Path(self.tmp.name)
                self.workspace = Workspace(self.root)
                self._write_public_fixture()
                query_index = RetrievalQueryIndex(self.root)
                baseline = self._search(
                    "indexed-retrieval-token",
                    query_index=query_index,
                )
                if case == "corrupt":
                    query_index.path.write_bytes(b"not a sqlite database")
                    expected_reason = "corrupt-or-unreadable"
                else:
                    with sqlite3.connect(query_index.path) as connection:
                        connection.execute(
                            "UPDATE query_index_snapshot SET payload = ? WHERE singleton = 1",
                            (json.dumps({"forged": "private-token"}),),
                        )
                        connection.commit()
                    expected_reason = "payload-fingerprint-mismatch"

                fallback = self._search(
                    "indexed-retrieval-token",
                    query_index=query_index,
                )

                self.assertEqual(fallback["deterministic_index"]["state"], "fallback")
                self.assertEqual(
                    fallback["deterministic_index"]["reason"],
                    expected_reason,
                )
                self.assertGreater(
                    fallback["deterministic_index"]["source_files_read"],
                    0,
                )
                self.assertEqual(fallback["cards"], baseline["cards"])
                self.assertEqual(
                    fallback["retrieval_result_fingerprint"],
                    baseline["retrieval_result_fingerprint"],
                )

    def test_disabled_and_symlinked_index_state_never_blocks_safe_scan(self) -> None:
        self._write_public_fixture()
        write_disabled = RetrievalQueryIndex(self.root)
        no_write = self._search(
            "indexed-retrieval-token",
            query_index=write_disabled,
            write_query_index=False,
        )
        self.assertEqual(no_write["deterministic_index"]["state"], "miss")
        self.assertGreater(no_write["deterministic_index"]["source_files_read"], 0)
        self.assertFalse(write_disabled.private_root.exists())

        disabled = RetrievalQueryIndex(self.root, enabled=False)
        result = self._search("indexed-retrieval-token", query_index=disabled)
        self.assertEqual(result["deterministic_index"]["state"], "disabled")
        self.assertGreater(result["deterministic_index"]["source_files_read"], 0)
        self.assertFalse(disabled.private_root.exists())

        if not hasattr(os, "symlink"):
            return
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            unsafe = RetrievalQueryIndex(self.root)
            unsafe.private_root.symlink_to(outside, target_is_directory=True)
            fallback = self._search("indexed-retrieval-token", query_index=unsafe)

            self.assertEqual(fallback["deterministic_index"]["state"], "fallback")
            self.assertEqual(
                fallback["deterministic_index"]["reason"],
                "unsafe-private-root",
            )
            self.assertGreater(fallback["count"], 0)
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_source_manifest_excludes_symlinked_corpus_entries(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            secret = Path(outside_directory) / "secret.json"
            secret.write_text(
                json.dumps(
                    {
                        "source_id": "secret",
                        "title": "manifest-secret-token",
                    }
                ),
                encoding="utf-8",
            )
            self.workspace.paths.sources.mkdir(parents=True)
            (self.workspace.paths.sources / "secret.json").symlink_to(secret)

            result = self._search(
                "manifest-secret-token",
                query_index=RetrievalQueryIndex(self.root),
            )

            self.assertEqual(result["deterministic_index"]["source_file_count"], 0)
            self.assertEqual(result["deterministic_index"]["source_files_read"], 0)
            self.assertEqual(result["count"], 0)
            self.assertNotIn(
                "manifest-secret-token",
                json.dumps(result["cards"]),
            )
            self.assertEqual(
                json.loads(secret.read_text(encoding="utf-8"))["source_id"],
                "secret",
            )

    def test_only_oversampled_canonical_window_receives_full_validation(self) -> None:
        records = self._write_raw_evidence_candidates(
            count=40,
            token="candidate-window-token",
        )
        first_evidence_id = min(records)
        calls: list[str] = []

        def load_fixture(_: Workspace, evidence_id: str) -> dict[str, object]:
            calls.append(evidence_id)
            return records[evidence_id]

        with (
            patch("rkf.research.load_canonical_evidence", side_effect=load_fixture),
            patch("rkf.research.activation_timeline", return_value=[]) as activations,
            patch("rkf.research.activity_timeline", return_value=[]) as actions,
        ):
            result = self._search(
                "candidate-window-token",
                page_types=["evidence"],
                limit=2,
                retrieval_provider=_SingleHitProvider(first_evidence_id),
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )

        self.assertEqual(result["deterministic_index"]["candidate_window"], 12)
        self.assertEqual(result["deterministic_index"]["canonical_validated"], 12)
        self.assertFalse(result["deterministic_index"]["validation_truncated"])
        self.assertEqual(
            result["deterministic_index"]["remaining_candidate_count"],
            28,
        )
        self.assertEqual(len(calls), 12)
        activations.assert_called_once_with(self.workspace.root)
        actions.assert_called_once_with(self.workspace.root)
        self.assertEqual(result["count"], 2)

    def test_invalid_initial_window_refills_until_valid_matches_are_found(self) -> None:
        records = self._write_raw_evidence_candidates(
            count=14,
            token="refill-candidate-token",
        )
        ordered_ids = sorted(records)
        invalid_ids = set(ordered_ids[:12])
        calls: list[str] = []

        def load_fixture(_: Workspace, evidence_id: str) -> dict[str, object]:
            calls.append(evidence_id)
            if evidence_id in invalid_ids:
                raise ValueError("invalid candidate fixture")
            return records[evidence_id]

        with patch("rkf.research.load_canonical_evidence", side_effect=load_fixture):
            result = self._search(
                "refill-candidate-token",
                page_types=["evidence"],
                limit=2,
            )

        self.assertEqual(result["count"], 2)
        self.assertEqual(
            [card["id"] for card in result["cards"]],
            ordered_ids[12:14],
        )
        self.assertEqual(result["deterministic_index"]["candidate_window"], 14)
        self.assertEqual(result["deterministic_index"]["canonical_validated"], 14)
        self.assertFalse(result["deterministic_index"]["validation_truncated"])
        self.assertEqual(
            result["deterministic_index"]["remaining_candidate_count"],
            0,
        )
        self.assertEqual(calls, ordered_ids)

    def test_refill_validation_is_bounded_and_reports_truncation(self) -> None:
        records = self._write_raw_evidence_candidates(
            count=50,
            token="bounded-refill-token",
        )
        calls: list[str] = []

        def reject_fixture(_: Workspace, evidence_id: str) -> dict[str, object]:
            calls.append(evidence_id)
            raise ValueError("invalid candidate fixture")

        with patch("rkf.research.load_canonical_evidence", side_effect=reject_fixture):
            result = self._search(
                "bounded-refill-token",
                page_types=["evidence"],
                limit=2,
            )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["deterministic_index"]["candidate_window"], 24)
        self.assertEqual(result["deterministic_index"]["canonical_validated"], 24)
        self.assertTrue(result["deterministic_index"]["validation_truncated"])
        self.assertEqual(
            result["deterministic_index"]["remaining_candidate_count"],
            26,
        )
        self.assertEqual(len(calls), 24)

    def test_receiptless_canonical_candidate_is_ranked_but_rejected(self) -> None:
        paper = self.workspace.paths.knowledge / "papers" / "receiptless.md"
        write_text(
            paper,
            frontmatter(
                {
                    "schema": "rkf-paper-v1.1",
                    "type": "paper",
                    "source_id": "receiptless",
                    "access_state": "fulltext",
                    "review_state": "unread",
                    "public_safe": True,
                }
            )
            + "# Receiptless Paper\n",
        )
        record_evidence(
            self.workspace,
            paper_id="papers/receiptless",
            summary="receiptless-candidate-token",
            locator_kind="page",
            locator_value="4",
            origin_project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        result = self._search(
            "receiptless-candidate-token",
            page_types=["evidence"],
        )

        self.assertEqual(result["deterministic_index"]["candidate_window"], 1)
        self.assertEqual(result["deterministic_index"]["canonical_validated"], 1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["answer_boundary"], "insufficient-evidence")

    def test_semantic_canonical_target_outside_deterministic_window_is_validated_on_demand(self) -> None:
        cards_root = self.workspace.paths.evidence_index / "cards"
        cards_root.mkdir(parents=True)
        evidence_id = "ev_ffffffffffffffffffff"
        record = {
            "evidence_id": evidence_id,
            "paper_id": "papers/fixture",
            "summary": "semantic-only canonical result",
            "locator": {"kind": "section", "value": "Results"},
            "verification_state": "unreviewed",
        }
        (cards_root / f"{evidence_id}.json").write_text(
            json.dumps(record),
            encoding="utf-8",
        )
        calls: list[str] = []

        def load_fixture(_: Workspace, object_id: str) -> dict[str, object]:
            calls.append(object_id)
            return record

        with patch("rkf.research.load_canonical_evidence", side_effect=load_fixture):
            result = self._search(
                "providertrigger",
                query_index=RetrievalQueryIndex(self.root),
                page_types=["evidence"],
                limit=1,
                retrieval_provider=_SingleHitProvider(evidence_id),
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )

        self.assertEqual(result["deterministic_index"]["candidate_window"], 0)
        self.assertEqual(result["deterministic_index"]["canonical_validated"], 1)
        self.assertEqual(calls, [evidence_id])
        self.assertEqual(result["cards"][0]["id"], evidence_id)
        self.assertEqual(result["cards"][0]["match_reason"], "semantic")


if __name__ == "__main__":
    unittest.main()
