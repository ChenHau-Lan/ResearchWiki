from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, execute_action_request
from rkf.core import Workspace, create_paper_note, create_source


class RKFActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def seed_paper(self, *, doi: str = "10.1234/report.action") -> str:
        record = create_source(
            self.workspace,
            kind="doi",
            value=doi,
            title="Report Action Paper",
            topic_id="",
            note="",
        )
        create_paper_note(self.workspace, record)
        return str(record["source_id"])

    def test_execute_inbox_capture_request_writes_inbox_and_guarded_source_links(self) -> None:
        request = ActionRequest(
            action="inbox.capture",
            params={
                "title": "Codex note on aerosol paper",
                "origin": "codex",
                "clip": "Short public-safe summary for DOI 10.1234/example.",
                "reader_note": "User project relation stays separate.",
                "doi": "10.1234/example",
            },
        )

        result = execute_action_request(request, workspace=self.workspace)

        self.assertEqual(result.action, "inbox.capture")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["source_id"], "doi_10_1234_example")
        self.assertTrue((self.root / "knowledge" / "inbox").exists())
        self.assertTrue((self.root / "state" / "sources" / "doi_10_1234_example.json").exists())
        self.assertTrue((self.root / "knowledge" / "papers" / "doi_10_1234_example.md").exists())

    def test_execute_hot_record_request_refreshes_hot_dashboard(self) -> None:
        request = ActionRequest(
            action="hot.record",
            params={
                "query": "recent aerosol-cloud parameterization papers",
                "origin": "local",
                "intent": "paper-search",
                "topic_id": "aerosol-cloud",
            },
        )

        result = execute_action_request(request, workspace=self.workspace)

        self.assertEqual(result.action, "hot.record")
        self.assertEqual(result.status, "ok")
        self.assertIn("event_id", result.payload)
        hot_md = (self.root / "hot.md").read_text(encoding="utf-8")
        self.assertIn("recent aerosol-cloud parameterization papers", hot_md)
        self.assertIn("aerosol-cloud", hot_md)

    def test_report_actions_return_structured_payloads(self) -> None:
        source_id = self.seed_paper()

        world = execute_action_request(
            ActionRequest(action="world.render", params={"log_tail": 1}),
            workspace=self.workspace,
        )
        self.assertEqual(world.status, "ok")
        self.assertIn("RKF Workspace Status", world.payload["markdown"])
        self.assertEqual(world.payload["counts"]["sources"], 1)
        self.assertEqual(world.payload["counts"]["knowledge_pages"], 1)

        queue = execute_action_request(
            ActionRequest(action="paper.queue", params={"limit": 5}),
            workspace=self.workspace,
        )
        self.assertEqual(queue.status, "ok")
        self.assertEqual(queue.payload["count"], 1)
        self.assertEqual(queue.payload["items"][0]["source_id"], source_id)

        lint = execute_action_request(
            ActionRequest(action="lint.run", params={"mode": "all"}),
            workspace=self.workspace,
        )
        self.assertEqual(lint.status, "ok")
        self.assertTrue(lint.payload["passed"])
        self.assertEqual(lint.payload["errors"], [])

        graph = execute_action_request(
            ActionRequest(action="graph.export"),
            workspace=self.workspace,
        )
        self.assertEqual(graph.status, "ok")
        self.assertEqual(graph.payload["path"], "graph/research_graph.json")
        self.assertGreaterEqual(graph.payload["node_count"], 1)
        self.assertGreaterEqual(graph.payload["edge_count"], 1)

        index = execute_action_request(
            ActionRequest(action="index.generate"),
            workspace=self.workspace,
        )
        self.assertEqual(index.status, "ok")
        self.assertEqual(index.payload["path"], "index.md")
        self.assertTrue((self.root / "index.md").exists())

        handoff = execute_action_request(
            ActionRequest(action="codex_handoff.generate"),
            workspace=self.workspace,
        )
        self.assertEqual(handoff.status, "ok")
        self.assertEqual(handoff.payload["path"], "prompts/codex_handoff_context.md")
        self.assertTrue((self.root / "prompts" / "codex_handoff_context.md").exists())


if __name__ == "__main__":
    unittest.main()
