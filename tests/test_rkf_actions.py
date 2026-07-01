from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, execute_action_request
from rkf.core import Workspace


class RKFActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

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


if __name__ == "__main__":
    unittest.main()
