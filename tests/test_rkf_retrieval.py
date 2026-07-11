from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, create_paper_note, create_source, frontmatter, write_text
from rkf.retrieval import search_central_rkf


class RKFRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)
        record = create_source(
            self.workspace,
            kind="doi",
            value="10.1234/cloud.study",
            title="Cloud Microphysics Retrieval Study",
            topic_id="cloud-microphysics",
            note="Public-safe source note.",
        )
        create_paper_note(self.workspace, record)
        self.source_id = str(record["source_id"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_exact_doi_precedes_keyword_matches(self) -> None:
        result = search_central_rkf(self.workspace, "10.1234/cloud.study")

        self.assertEqual(result["cards"][0]["source_id"], self.source_id)
        self.assertEqual(result["cards"][0]["match_reason"], "exact-doi")

    def test_result_card_exposes_maturity_and_evidence_gaps(self) -> None:
        result = search_central_rkf(self.workspace, "Cloud Microphysics Retrieval Study")

        paper = next(card for card in result["cards"] if card["type"] == "paper")
        self.assertEqual(paper["reading_maturity"], "metadata-only")
        self.assertEqual(paper["evidence_boundary"], "review-blocker")
        self.assertEqual(paper["evidence_use"], "proposal-only")
        self.assertIn("locator", paper["missing"])

    def test_search_is_read_only(self) -> None:
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())

        result = search_central_rkf(self.workspace, "cloud microphysics")

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertGreaterEqual(result["count"], 1)
        self.assertEqual(
            result["next_step"],
            "inspect-project-local-if-central-context-is-incomplete",
        )

    def test_maturity_and_type_filters_are_applied(self) -> None:
        result = search_central_rkf(
            self.workspace,
            "cloud",
            page_types=["paper"],
            reading_states=["metadata-only"],
            evidence_boundaries=["review-blocker"],
        )

        self.assertGreaterEqual(result["count"], 1)
        self.assertTrue(all(card["type"] == "paper" for card in result["cards"]))

    def test_traditional_chinese_keyword_query_matches_title(self) -> None:
        path = self.workspace.paths.knowledge / "concepts" / "taiwan-cloud.md"
        write_text(
            path,
            frontmatter(
                {
                    "type": "concept",
                    "status": "draft",
                    "evidence_boundary": "maintained",
                    "claim_readiness": "not-ready",
                }
            )
            + "# 臺灣雲微物理研究\n\n公開安全摘要。\n",
        )

        result = search_central_rkf(self.workspace, "雲微物理")

        card = next(card for card in result["cards"] if card["id"] == "concepts/taiwan-cloud")
        self.assertEqual(card["match_reason"], "keyword")

    def test_exact_page_match_expands_governed_graph_neighbor_card(self) -> None:
        paper_id = f"papers/{self.source_id}"

        result = search_central_rkf(self.workspace, paper_id)

        self.assertEqual(result["cards"][0]["id"], paper_id)
        neighbor = next(
            card
            for card in result["cards"]
            if card["id"] == "cloud-microphysics" and card["type"] == "topic"
        )
        self.assertEqual(neighbor["match_reason"], "graph-context")


if __name__ == "__main__":
    unittest.main()
