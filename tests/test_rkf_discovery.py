from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace
from rkf.discovery import (
    DiscoveryError,
    discovery_status,
    fetch_arxiv,
    fetch_crossref,
    fetch_openalex,
    load_acceptance_state,
    load_discovery_run,
    mark_candidates_accepted,
    preview_discovery,
    record_discovery_run,
    select_run_candidates,
)


FIXED_TIME = "2026-07-13T12:00:00Z"


class RKFDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            'wiki_root = ".rkf_data/wiki"\n'
            'raw_root = ".rkf_data/raw"\n\n'
            "[machine]\n"
            'id = "machine-discovery"\n'
            "maintenance_writer = true\n",
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def crossref_records(_query: str, _limit: int):
        return [
            {
                "title": "Aerosol Cloud Interactions",
                "authors": ["Ada Researcher", "Bo Scientist"],
                "year": 2025,
                "venue": "Journal of Cloud Studies",
                "doi": "10.1234/Cloud.Example",
                "url": "https://publisher.example/article",
                "provider_id": "crossref-1",
                "score": 12.5,
                "abstract": "This text must never enter RKF discovery state.",
                "pdf_url": "https://private.example/paper.pdf",
                "private_key": "do-not-persist",
            }
        ]

    @staticmethod
    def arxiv_records(_query: str, _limit: int):
        return [
            {
                "title": "Aerosol Cloud Interactions",
                "authors": ["Ada Researcher", "Bo Scientist"],
                "year": "2025-01-02",
                "venue": "arXiv",
                "doi": "https://doi.org/10.1234/cloud.example",
                "url": "https://arxiv.org/abs/2501.00001",
                "provider_id": "2501.00001",
                "score": 7,
                "deepread": "private reading state",
            }
        ]

    def preview(self, **overrides):
        params = {
            "query": "aerosol cloud interactions",
            "topic_id": "cloud-microphysics",
            "provider_clients": {
                "crossref": self.crossref_records,
                "arxiv": self.arxiv_records,
            },
            "generated_at": FIXED_TIME,
        }
        params.update(overrides)
        return preview_discovery(self.workspace, **params)

    def test_preview_is_non_mutating_and_deterministic(self) -> None:
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))

        first = self.preview()
        second = self.preview()

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertEqual(after, before)
        self.assertEqual(first, second)
        self.assertEqual(first["persistence"], "none")
        self.assertEqual(first["evidence_boundary"], "candidate-only")
        self.assertEqual(first["promotion"], "none")
        self.assertFalse(self.workspace.paths.search_runs.exists())

    def test_preview_rejects_non_integer_limit_and_string_provider_list(self) -> None:
        with self.assertRaisesRegex(DiscoveryError, "max_results must be an integer"):
            self.preview(max_results="20")
        with self.assertRaisesRegex(DiscoveryError, "provider names must be a list"):
            self.preview(provider_names="crossref")

    def test_cross_provider_dedupe_and_strict_field_stripping(self) -> None:
        preview = self.preview()

        self.assertEqual(preview["candidate_count"], 1)
        candidate = preview["candidates"][0]
        self.assertEqual(candidate["doi"], "10.1234/cloud.example")
        self.assertEqual(candidate["providers"], ["arxiv", "crossref"])
        self.assertRegex(candidate["candidate_id"], r"^cand_[0-9a-f]{20}$")
        serialized = json.dumps(preview, sort_keys=True).lower()
        for forbidden in (
            "abstract",
            "pdf_url",
            "private_key",
            "deepread",
            "do-not-persist",
            "private reading state",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_public_landing_urls_drop_all_query_parameters(self) -> None:
        def provider(_query: str, _limit: int):
            return [
                {
                    "title": "Public Landing Page Candidate",
                    "authors": ["Ada Researcher"],
                    "year": 2025,
                    "url": "https://www.nature.com/articles/rkf-synthetic?reader_id=private-reader&utm_source=test",
                }
            ]

        preview = self.preview(provider_clients={"crossref": provider})

        self.assertEqual(
            preview["candidates"][0]["url"],
            "https://www.nature.com/articles/rkf-synthetic",
        )
        self.assertNotIn("private-reader", json.dumps(preview))

    def test_nonpublic_landing_urls_are_stripped(self) -> None:
        unsafe_urls = {
            "IPv4 Loopback": "http://127.0.0.1/internal",
            "IPv4 Shorthand": "https://127.1/internal",
            "IPv4 Hex Shorthand": "https://0x7f.0.0.1/internal",
            "IPv6 Loopback": "http://[::1]/internal",
            "Localhost": "https://localhost/article",
            "User Info": "https://user:pass@www.nature.com/article",
            "Reserved Host": "https://journal.invalid/article",
            "Single Label": "https://intranet/article",
        }

        def provider(_query: str, _limit: int):
            return [
                {
                    "title": title,
                    "authors": ["Ada Researcher"],
                    "year": 2025,
                    "url": url,
                }
                for title, url in unsafe_urls.items()
            ]

        preview = self.preview(provider_clients={"fixture": provider})

        self.assertEqual(preview["candidate_count"], len(unsafe_urls))
        by_title = {candidate["title"]: candidate for candidate in preview["candidates"]}
        self.assertEqual(set(by_title), set(unsafe_urls))
        self.assertTrue(all(not candidate["url"] for candidate in by_title.values()))

    def test_personal_metadata_is_stripped_without_banning_research_terms(self) -> None:
        def provider(_query: str, _limit: int):
            return [
                {
                    "title": "Secret Sharing and Password Security",
                    "authors": ["person@example.invalid", "Ada Researcher"],
                    "year": 2025,
                    "venue": "Security Research Letters",
                    "url": "https://www.nature.com/articles/rkf-secret-sharing",
                }
            ]

        preview = self.preview(
            query="secret sharing and password security",
            provider_clients={"fixture": provider},
        )

        self.assertEqual(preview["candidate_count"], 1)
        candidate = preview["candidates"][0]
        self.assertEqual(candidate["title"], "Secret Sharing and Password Security")
        self.assertEqual(candidate["authors"], ["Ada Researcher"])
        self.assertNotIn("person@example.invalid", json.dumps(preview))
        with self.assertRaisesRegex(DiscoveryError, "private or sensitive"):
            self.preview(query="person@example.invalid cloud metadata")
        with self.assertRaisesRegex(DiscoveryError, "private or sensitive"):
            self.preview(query="secret=synthetic-value cloud metadata")

    def test_same_bibliography_with_conflicting_dois_stays_ambiguous(self) -> None:
        def first(_query: str, _limit: int):
            return [{
                "title": "Shared Bibliographic Identity",
                "authors": ["Same Author"],
                "year": 2024,
                "doi": "10.1000/identity.one",
            }]

        def second(_query: str, _limit: int):
            return [{
                "title": "Shared Bibliographic Identity",
                "authors": ["Same Author"],
                "year": 2024,
                "doi": "10.1000/identity.two",
            }]

        preview = self.preview(provider_clients={"first": first, "second": second})

        self.assertEqual(preview["candidate_count"], 2)
        self.assertEqual(
            {candidate["doi"] for candidate in preview["candidates"]},
            {"10.1000/identity.one", "10.1000/identity.two"},
        )
        self.assertEqual(
            {candidate["dedupe_status"] for candidate in preview["candidates"]},
            {"ambiguous"},
        )

    def test_paper_radar_adapter_uses_only_allowlisted_metadata(self) -> None:
        preview = self.preview(
            provider_clients={},
            paper_radar_records={
                "papers": [{
                    "id": "radar-1",
                    "title": "Paper Radar Candidate",
                    "authors": ["Public Author"],
                    "published": "2024-03-01",
                    "journal": "Public Journal",
                    "doi": "10.5678/radar.candidate",
                    "interest_score": 0.9,
                    "abstract": "copyrighted abstract",
                    "oa_pdf_url": "https://example.org/fulltext.pdf",
                    "pdf_key": "/private/paper.pdf",
                    "D1": {"vote": "up"},
                    "content": "private deep-reading content",
                }]
            },
        )

        self.assertEqual(preview["requested_providers"], ["paper-radar"])
        self.assertEqual(preview["candidate_count"], 1)
        candidate = preview["candidates"][0]
        self.assertEqual(candidate["provider"], "paper-radar")
        self.assertEqual(candidate["doi"], "10.5678/radar.candidate")
        serialized = json.dumps(preview, sort_keys=True)
        for forbidden in ("abstract", "oa_pdf_url", "pdf_key", "D1", "content", "/private/paper.pdf"):
            self.assertNotIn(forbidden, serialized)

    def test_provider_failure_is_redacted_and_partial(self) -> None:
        def broken_provider(_query: str, _limit: int):
            private_path = "/" + "Users/private/provider"
            raise RuntimeError(f"api_key=secret at {private_path}")

        preview = self.preview(
            provider_clients={
                "crossref": self.crossref_records,
                "broken": broken_provider,
            }
        )

        self.assertEqual(preview["status"], "partial")
        broken = next(item for item in preview["provider_status"] if item["provider"] == "broken")
        self.assertEqual(broken, {
            "provider": "broken",
            "status": "error",
            "count": 0,
            "error_code": "PROVIDER_UNAVAILABLE",
        })
        serialized = json.dumps(preview)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("/" + "Users", serialized)

    def test_missing_optional_openalex_key_is_reported_without_network(self) -> None:
        preview = preview_discovery(
            self.workspace,
            query="cloud feedback",
            provider_names=["openalex"],
            openalex_api_key="",
            generated_at=FIXED_TIME,
        )

        self.assertEqual(preview["status"], "failed")
        self.assertEqual(
            preview["provider_status"][0]["error_code"],
            "OPENALEX_API_KEY_REQUIRED",
        )

    def test_record_rejects_hash_mismatch_before_writing(self) -> None:
        preview = self.preview()

        with self.assertRaisesRegex(DiscoveryError, "hash mismatch"):
            record_discovery_run(
                self.workspace,
                preview=preview,
                expected_hash="0" * 64,
                recorded_at=FIXED_TIME,
            )

        self.assertFalse(self.workspace.paths.search_runs.exists())

    def test_record_uses_unique_paths_and_loads_exact_run(self) -> None:
        preview = self.preview()

        first = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )
        second = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )

        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertTrue(first["run_path"].endswith("/candidates.json"))
        loaded = load_discovery_run(self.workspace, first["run_id"])
        self.assertEqual(loaded["schema"], "rkf-discovery-run-v2")
        self.assertEqual(loaded["preview_hash"], preview["preview_hash"])
        self.assertEqual(loaded["candidates"], preview["candidates"])
        self.assertEqual(len(list(self.workspace.paths.search_runs.glob("run_*/candidates.json"))), 2)

    def test_acceptance_state_is_separate_and_idempotent(self) -> None:
        preview = self.preview()
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )
        run_path = self.workspace.paths.search_runs / recorded["run_id"] / "candidates.json"
        immutable_before = run_path.read_bytes()
        candidate_id = preview["candidates"][0]["candidate_id"]

        first = mark_candidates_accepted(
            self.workspace,
            run_id=recorded["run_id"],
            candidate_ids=[candidate_id],
            actor="human",
            accepted_at="2026-07-13T13:00:00Z",
        )
        second = mark_candidates_accepted(
            self.workspace,
            run_id=recorded["run_id"],
            candidate_ids=[candidate_id],
            actor="codex",
            accepted_at="2026-07-13T14:00:00Z",
        )

        self.assertEqual(first["added_count"], 1)
        self.assertEqual(second["added_count"], 0)
        self.assertEqual(second["accepted_count"], 1)
        self.assertEqual(run_path.read_bytes(), immutable_before)
        state = load_acceptance_state(self.workspace, recorded["run_id"])
        self.assertEqual(state["accepted"][0]["actor"], "human")
        selected = select_run_candidates(
            load_discovery_run(self.workspace, recorded["run_id"]),
            [candidate_id],
        )
        self.assertEqual(
            selected[0]["candidate_id"],
            candidate_id,
        )

    def test_status_is_aggregate_only(self) -> None:
        preview = self.preview()
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )
        candidate_id = preview["candidates"][0]["candidate_id"]
        mark_candidates_accepted(
            self.workspace,
            run_id=recorded["run_id"],
            candidate_ids=[candidate_id],
            accepted_at="2026-07-13T13:00:00Z",
        )

        status = discovery_status(self.workspace)

        self.assertEqual(status["run_count"], 1)
        self.assertEqual(status["candidate_count"], 1)
        self.assertEqual(status["accepted_count"], 1)
        serialized = json.dumps(status)
        self.assertNotIn("Aerosol Cloud Interactions", serialized)
        self.assertNotIn("10.1234", serialized)
        self.assertNotIn("cand_", serialized)

    def test_status_counts_schema_marker_only_run_as_malformed(self) -> None:
        invalid_dir = self.workspace.paths.search_runs / "run_invalid_status_probe"
        invalid_dir.mkdir(parents=True)
        (invalid_dir / "candidates.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-discovery-run-v2",
                    "candidate_count": 999999,
                    "status": "ok",
                    "recorded_at": "9999-12-31T23:59:59Z",
                    "requested_providers": ["INVALID PROVIDER"],
                }
            ),
            encoding="utf-8",
        )

        status = discovery_status(self.workspace)

        self.assertEqual(status["run_count"], 0)
        self.assertEqual(status["candidate_count"], 0)
        self.assertEqual(status["malformed_run_count"], 1)
        self.assertEqual(status["provider_run_counts"], {})
        self.assertNotIn("INVALID PROVIDER", json.dumps(status))

    def test_acceptance_state_rejects_unknown_ids_invalid_actor_and_extra_fields(self) -> None:
        preview = self.preview()
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )
        run_id = recorded["run_id"]
        candidate_id = preview["candidates"][0]["candidate_id"]
        path = self.workspace.paths.search_runs / run_id / "acceptance.json"
        base = {
            "schema": "rkf-discovery-acceptance-v1",
            "run_id": run_id,
            "preview_hash": preview["preview_hash"],
            "updated_at": "2026-07-13T13:00:00Z",
            "accepted": [
                {
                    "candidate_id": candidate_id,
                    "accepted_at": "2026-07-13T13:00:00Z",
                    "actor": "human",
                }
            ],
        }
        cases = {
            "extra top-level field": {**base, "extra": "field"},
            "unknown candidate": {
                **base,
                "accepted": [
                    {
                        **base["accepted"][0],
                        "candidate_id": "cand_00000000000000000000",
                    }
                ],
            },
            "invalid actor": {
                **base,
                "accepted": [{**base["accepted"][0], "actor": "untrusted"}],
            },
            "invalid timestamp": {**base, "updated_at": "not-a-time"},
        }
        for label, payload in cases.items():
            with self.subTest(label=label):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(DiscoveryError):
                    load_acceptance_state(self.workspace, run_id)

        path.unlink()
        with self.assertRaisesRegex(DiscoveryError, "accepted_at"):
            mark_candidates_accepted(
                self.workspace,
                run_id=run_id,
                candidate_ids=[candidate_id],
                accepted_at="not-a-time",
            )
        self.assertFalse(path.exists())

    def test_builtin_provider_parsers_need_no_third_party_packages(self) -> None:
        crossref_payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/crossref.test",
                        "title": ["Crossref Test"],
                        "author": [{"given": "Cora", "family": "Researcher"}],
                        "published": {"date-parts": [[2023, 2, 1]]},
                        "container-title": ["Metadata Journal"],
                        "URL": "https://doi.org/10.1000/crossref.test",
                        "score": 5.1,
                        "abstract": "must be ignored",
                    }
                ]
            }
        }

        def crossref_get(_url: str, _headers):
            return json.dumps(crossref_payload).encode("utf-8")

        atom = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>https://arxiv.org/abs/2607.01234v1</id>
            <title>arXiv Test</title>
            <summary>must be ignored</summary>
            <published>2026-07-10T00:00:00Z</published>
            <author><name>Ari Xiv</name></author>
            <arxiv:doi>10.1000/arxiv.test</arxiv:doi>
            <arxiv:journal_ref>Example Letters</arxiv:journal_ref>
            <link title="pdf" href="https://arxiv.org/pdf/2607.01234" />
          </entry>
        </feed>""".encode("utf-8")

        def arxiv_get(_url: str, _headers):
            return atom

        openalex_payload = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "OpenAlex Test",
                    "doi": "https://doi.org/10.1000/openalex.test",
                    "publication_year": 2022,
                    "relevance_score": 4,
                    "authorships": [{"author": {"display_name": "Alex Author"}}],
                    "primary_location": {
                        "landing_page_url": "https://example.org/article",
                        "pdf_url": "https://example.org/private.pdf",
                        "source": {"display_name": "Open Metadata"},
                    },
                    "abstract_inverted_index": {"private": [0]},
                }
            ]
        }

        def openalex_get(_url: str, _headers):
            return json.dumps(openalex_payload).encode("utf-8")

        crossref = fetch_crossref("test", http_get=crossref_get)
        arxiv = fetch_arxiv("test", http_get=arxiv_get)
        openalex = fetch_openalex("test", api_key="test-only-key", http_get=openalex_get)

        self.assertEqual(crossref[0]["doi"], "10.1000/crossref.test")
        self.assertEqual(crossref[0]["year"], 2023)
        self.assertEqual(arxiv[0]["provider_id"], "2607.01234v1")
        self.assertEqual(arxiv[0]["venue"], "Example Letters")
        self.assertEqual(openalex[0]["title"], "OpenAlex Test")
        serialized = json.dumps([crossref, arxiv, openalex])
        self.assertNotIn("abstract", serialized)
        self.assertNotIn("pdf_url", serialized)

    def test_sensitive_query_and_unknown_candidate_are_rejected(self) -> None:
        with self.assertRaisesRegex(DiscoveryError, "sensitive"):
            self.preview(query="api_key=secret")

        preview = self.preview()
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at=FIXED_TIME,
        )
        with self.assertRaisesRegex(DiscoveryError, "unknown candidate"):
            mark_candidates_accepted(
                self.workspace,
                run_id=recorded["run_id"],
                candidate_ids=["cand_00000000000000000000"],
            )


if __name__ == "__main__":
    unittest.main()
