from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, build_research_graph, lint_graph_links


PAPER = """---
schema: rkf-paper-v1.1
type: paper
status: draft
topics: []
created: 2026-07-11
updated: 2026-07-11
review_stage: ai-extracted
---

# Example Paper
"""

PROJECT_SYNTHESIS = """---
type: project-synthesis
status: draft
topics: []
created: 2026-07-11
updated: 2026-07-11
review_stage: ai-extracted
paper_relations:
  - paper_id: papers/example-paper
    relation: uses-paper
---

# Project synthesis

- [Example Paper](../papers/example-paper.md) — role in this project
"""


class RKFPaperRelationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.root.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n',
            encoding="utf-8",
        )
        paper_root = self.root / "knowledge" / "papers"
        synthesis_root = self.root / "knowledge" / "synthesis"
        paper_root.mkdir(parents=True)
        synthesis_root.mkdir(parents=True)
        (paper_root / "example-paper.md").write_text(PAPER, encoding="utf-8")
        self.project_path = synthesis_root / "project.md"
        self.project_path.write_text(PROJECT_SYNTHESIS, encoding="utf-8")
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_relation_emits_directed_incoming_edge_and_passes_link_lint(self) -> None:
        graph = build_research_graph(self.workspace)
        errors = lint_graph_links(self.workspace)

        self.assertIn(
            {"from": "synthesis/project", "to": "papers/example-paper", "type": "uses-paper"},
            graph["edges"],
        )
        self.assertEqual(errors, [])

    def test_relation_without_markdown_link_is_rejected(self) -> None:
        self.project_path.write_text(
            PROJECT_SYNTHESIS.replace("- [Example Paper](../papers/example-paper.md) — role in this project\n", ""),
            encoding="utf-8",
        )

        errors = lint_graph_links(self.workspace)

        self.assertIn("knowledge/synthesis/project.md: paper relation missing body link to papers/example-paper", errors)


if __name__ == "__main__":
    unittest.main()
