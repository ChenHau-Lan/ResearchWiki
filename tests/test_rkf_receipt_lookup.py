from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf import research
from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace


class RKFQueryReceiptLookupTests(unittest.TestCase):
    def test_query_context_loads_each_lineage_collection_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            raw.mkdir()
            (root / "rkf.workspace.toml").write_text(
                "[storage]\n"
                f'wiki_root = "{root.as_posix()}"\n'
                f'raw_root = "{raw.as_posix()}"\n',
                encoding="utf-8",
            )
            (root / ".rkf-connect.toml").write_text(
                "version = 2\n\n[rkf]\n"
                "available = true\nactivation = \"manual\"\nquery_first = true\n"
                "capture_mode = \"active-aggressive\"\n"
                "project_id = \"prj_1234567890abcdef12345678\"\n"
                "project_name = \"Receipt Lookup Test\"\n"
                "marker_schema = \"rkf-connect-v2\"\n"
                "connector_version = \"1.1.0\"\n"
                "connected_at = \"2026-07-15T00:00:00Z\"\n",
                encoding="utf-8",
            )
            workspace = Workspace(root)
            paper = workspace.paths.knowledge / "papers" / "receipt-test.md"
            paper.parent.mkdir(parents=True, exist_ok=True)
            paper.write_text(
                "---\n"
                "schema: rkf-paper-v1.1\n"
                "type: paper\n"
                "source_id: receipt-test\n"
                "access_state: fulltext\n"
                "review_state: unread\n"
                "---\n\n# Receipt Test\n",
                encoding="utf-8",
            )
            runtime = RKFActionRuntime(workspace=workspace, project_root=root)
            self.assertEqual(runtime.execute(ActionRequest("rkf.activate")).status, "ok")
            evidence = runtime.execute(
                ActionRequest(
                    "workflow.read",
                    {
                        "paper_id": "papers/receipt-test",
                        "summary": "A locator-backed test observation.",
                        "locator_kind": "page",
                        "locator_value": "5",
                        "stance": "supports",
                    },
                )
            )
            self.assertEqual(evidence.status, "ok")
            evidence_id = evidence.payload["evidence_id"]

            with (
                patch(
                    "rkf.research.activation_timeline",
                    wraps=research.activation_timeline,
                ) as activation_scan,
                patch(
                    "rkf.research.activity_timeline",
                    wraps=research.activity_timeline,
                ) as action_scan,
            ):
                with research.query_local_receipt_lookup(workspace):
                    first = research.load_canonical_evidence(workspace, evidence_id)
                    second = research.load_canonical_evidence(workspace, evidence_id)

            self.assertEqual(first, second)
            self.assertEqual(activation_scan.call_count, 1)
            self.assertEqual(action_scan.call_count, 1)


if __name__ == "__main__":
    unittest.main()
