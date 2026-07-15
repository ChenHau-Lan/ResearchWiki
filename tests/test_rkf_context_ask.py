from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf.core import Workspace, frontmatter, write_text
from rkf.providers import RetrievalHit
from rkf.retrieval import SearchResultCard, _answer_projection, search_central_rkf


PROJECT_ID = "prj_1234567890abcdef12345678"
ACTIVATION_ID = "act_1234567890abcdef12345678"


class ContextProvider:
    name = "fixture-context"
    version = "1"
    index_generation = "gen-context"
    elapsed_ms = 3

    def __init__(self, hits: list[RetrievalHit]) -> None:
        self.hits = hits

    def search(self, **_: object) -> list[RetrievalHit]:
        return list(self.hits)


class RKFContextAskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)
        self._write_paper("context", "Canonical Context Paper")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_paper(
        self,
        stem: str,
        title: str,
        *,
        public_safe: bool = True,
    ) -> None:
        path = self.workspace.paths.knowledge / "papers" / f"{stem}.md"
        write_text(
            path,
            frontmatter(
                {
                    "schema": "rkf-paper-v1.1",
                    "type": "paper",
                    "source_id": stem,
                    "access_state": "metadata",
                    "review_state": "unread",
                    "public_safe": public_safe,
                }
            )
            + f"# {title}\n\nGoverned public source context.\n",
        )

    def _search(
        self,
        *,
        hits: list[RetrievalHit],
        answer_policy: str = "context-ok",
    ) -> dict[str, object]:
        return search_central_rkf(
            self.workspace,
            "provider-only-query",
            retrieval_provider=ContextProvider(hits),
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
            persist_retrieval_run=False,
            answer_policy=answer_policy,
        )

    def test_context_ok_returns_unlocated_typed_semantic_context(self) -> None:
        hit = RetrievalHit(
            object_id="papers/context",
            score=0.9,
            match_reason="semantic",
            metadata={"object_type": "paper", "index_scope": "public-safe"},
        )

        result = self._search(hits=[hit])

        self.assertEqual(result["answer_policy"], "context-ok")
        self.assertEqual(result["answer_mode"], "context-only")
        self.assertEqual(result["answer_boundary"], "insufficient-evidence")
        self.assertEqual(result["answer_card_ids"], ["papers/context"])
        self.assertEqual(result["answer_count"], 1)
        self.assertEqual(result["next_action"], "locate-source")
        card = result["cards"][0]
        self.assertEqual(card["evidence_use"], "source-context")
        self.assertFalse(card["claim_ready"])
        self.assertIn("locator", card["missing"])

    def test_evidence_only_keeps_context_visible_but_not_answer_eligible(self) -> None:
        hit = RetrievalHit(
            object_id="papers/context",
            locator="",
            score=0.9,
            match_reason="semantic",
            metadata={"object_type": "paper", "index_scope": "public-safe"},
        )

        result = self._search(hits=[hit], answer_policy="evidence-only")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["cards"][0]["id"], "papers/context")
        self.assertEqual(result["answer_mode"], "no-results")
        self.assertEqual(result["answer_card_ids"], [])
        self.assertEqual(result["answer_count"], 0)
        self.assertEqual(result["answer_boundary"], "insufficient-evidence")
        self.assertEqual(result["next_action"], "locate-source")

    def test_provider_locator_cannot_promote_a_canonical_paper(self) -> None:
        hit = RetrievalHit(
            object_id="papers/context",
            locator="section:Results",
            score=1.0,
            match_reason="semantic",
            metadata={
                "object_type": "paper",
                "index_scope": "public-safe",
                "evidence_use": "locator-backed",
                "claim_readiness": "verified",
                "missing": [],
            },
        )

        result = self._search(hits=[hit])

        card = result["cards"][0]
        self.assertEqual(card["evidence_use"], "source-context")
        self.assertFalse(card["claim_ready"])
        self.assertIn("locator", card["missing"])
        self.assertEqual(result["answer_mode"], "context-only")
        self.assertEqual(result["answer_boundary"], "insufficient-evidence")

    def test_semantic_context_stays_fail_closed_by_scope_and_canonical_id(self) -> None:
        self._write_paper("private", "Private Scope Paper")
        self._write_paper("missing-scope", "Missing Scope Paper")
        self._write_paper(
            "not-public-safe",
            "Non-public Canonical Paper",
            public_safe=False,
        )
        hits = [
            RetrievalHit(
                object_id="papers/context",
                locator="",
                score=0.9,
                match_reason="semantic",
                metadata={"object_type": "paper", "index_scope": "public-safe"},
            ),
            RetrievalHit(
                object_id="papers/private",
                locator="",
                score=1.0,
                match_reason="semantic",
                metadata={"object_type": "paper", "index_scope": "private-fulltext"},
            ),
            RetrievalHit(
                object_id="papers/missing-scope",
                locator="",
                score=0.8,
                match_reason="semantic",
                metadata={"object_type": "paper"},
            ),
            RetrievalHit(
                object_id="papers/not-canonical",
                locator="",
                score=0.7,
                match_reason="semantic",
                metadata={"object_type": "paper", "index_scope": "public-safe"},
            ),
            RetrievalHit(
                object_id="papers/not-public-safe",
                locator="",
                score=0.6,
                match_reason="semantic",
                metadata={"object_type": "paper", "index_scope": "public-safe"},
            ),
        ]

        result = self._search(hits=hits)

        self.assertEqual([card["id"] for card in result["cards"]], ["papers/context"])

    def test_stage_timing_is_additive_and_excluded_from_result_identity(self) -> None:
        hit = RetrievalHit(
            object_id="papers/context",
            locator="",
            score=0.9,
            match_reason="semantic",
            metadata={"object_type": "paper", "index_scope": "public-safe"},
        )
        expected_timing_keys = {
            "index_ms",
            "scan_ms",
            "validation_ms",
            "graph_ms",
            "provider_ms",
            "persist_ms",
            "total_ms",
        }

        with patch("rkf.retrieval._elapsed_ms", return_value=1.0):
            first = self._search(hits=[hit])
        with patch("rkf.retrieval._elapsed_ms", return_value=99.0):
            second = self._search(hits=[hit])

        self.assertEqual(set(first["timing"]), expected_timing_keys)
        self.assertTrue(all(value >= 0 for value in first["timing"].values()))
        self.assertNotEqual(first["timing"], second["timing"])
        self.assertEqual(
            first["retrieval_result_fingerprint"],
            second["retrieval_result_fingerprint"],
        )

    def test_answer_policy_is_validated(self) -> None:
        with self.assertRaisesRegex(
            SystemExit,
            "answer_policy must be context-ok or evidence-only",
        ):
            search_central_rkf(
                self.workspace,
                "query",
                answer_policy="unsupported",
                persist_retrieval_run=False,
            )


class RKFAnswerProjectionTests(unittest.TestCase):
    @staticmethod
    def _card(
        *,
        card_id: str,
        evidence_use: str,
        claim_readiness: str,
        missing: list[str],
    ) -> SearchResultCard:
        return SearchResultCard(
            id=card_id,
            path=f"state/{card_id}.json",
            type="evidence" if evidence_use == "locator-backed" else "paper",
            title=card_id,
            source_id="",
            match_reason="semantic",
            score=10,
            reading_maturity="canonical",
            evidence_boundary="evidence-pointer",
            evidence_use=evidence_use,
            claim_readiness=claim_readiness,
            missing=missing,
            summary=card_id,
        )

    def test_context_ok_distinguishes_mixed_and_evidence_modes(self) -> None:
        context = self._card(
            card_id="papers/context",
            evidence_use="source-context",
            claim_readiness="not-ready",
            missing=["locator"],
        )
        evidence = self._card(
            card_id="ev_valid",
            evidence_use="locator-backed",
            claim_readiness="unreviewed",
            missing=[],
        )

        mixed_mode, mixed_cards, _ = _answer_projection(
            [context, evidence],
            answer_policy="context-ok",
        )
        evidence_mode, evidence_cards, _ = _answer_projection(
            [context, evidence],
            answer_policy="evidence-only",
        )

        self.assertEqual(mixed_mode, "mixed")
        self.assertEqual([card.id for card in mixed_cards], ["papers/context", "ev_valid"])
        self.assertEqual(evidence_mode, "evidence")
        self.assertEqual([card.id for card in evidence_cards], ["ev_valid"])

    def test_rejected_evidence_is_not_answer_eligible(self) -> None:
        rejected = self._card(
            card_id="ev_rejected",
            evidence_use="locator-backed",
            claim_readiness="rejected",
            missing=[],
        )

        mode, cards, next_action = _answer_projection(
            [rejected],
            answer_policy="evidence-only",
        )

        self.assertEqual(mode, "no-results")
        self.assertEqual(cards, [])
        self.assertEqual(next_action, "review-context")


if __name__ == "__main__":
    unittest.main()
