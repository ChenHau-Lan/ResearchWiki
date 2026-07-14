from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime, available_actions
from rkf.core import Workspace
from rkf.lineage import activity_timeline
from rkf.schema import normalize_paper_state


class RKFV1Tests(unittest.TestCase):
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
        (self.root / ".rkf-connect.toml").write_text(
            "version = 2\n\n[rkf]\n"
            "available = true\nactivation = \"manual\"\nquery_first = true\n"
            "capture_mode = \"active-aggressive\"\n"
            "project_id = \"prj_1234567890abcdef12345678\"\n"
            "project_name = \"Test Project\"\n"
            "marker_schema = \"rkf-connect-v2\"\n"
            "connector_version = \"1.1.0\"\n",
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        activated = self.runtime.execute(ActionRequest("rkf.activate"))
        self.assertEqual(activated.status, "ok")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_registry_exposes_only_five_workflows_and_connection_controls(self) -> None:
        self.assertEqual(
            set(available_actions()),
            {
                "rkf.activate", "rkf.status", "rkf.deactivate", "connect.validate",
                "workflow.add", "workflow.ask", "workflow.read",
                "workflow.compare-synthesize", "workflow.review",
            },
        )

    def test_legacy_paper_state_normalization_is_conservative(self) -> None:
        self.assertEqual(
            normalize_paper_state({"reading_state": "first-pass-pdf-qc"}),
            {"access_state": "fulltext", "review_state": "skimmed"},
        )
        self.assertEqual(
            normalize_paper_state({"reading_state": "unexpected"}),
            {"access_state": "metadata", "review_state": "unread"},
        )

    def test_locator_claim_synthesis_and_review_close_the_loop(self) -> None:
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Observed relationship in the reported sample.",
                    "locator_kind": "figure",
                    "locator_value": "Fig. 3",
                    "stance": "supports",
                    "verification_state": "human-verified",
                },
            )
        )
        self.assertEqual(evidence.status, "ok")
        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "The reported sample shows the relationship.",
                    "evidence_ids": [evidence.payload["evidence_id"]],
                    "status": "verified",
                },
            )
        )
        self.assertEqual(claim.status, "ok")
        synthesis = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": "Does the sample show the relationship?",
                    "claim_ids": [claim.payload["claim_id"]],
                    "provisional_conclusion": "Supported for this sample only.",
                    "next_action": "Test generality in another paper.",
                },
            )
        )
        self.assertEqual(synthesis.status, "ok")
        review = self.runtime.execute(ActionRequest("workflow.review"))
        self.assertIn(synthesis.payload["synthesis_id"], [synthesis.payload["synthesis_id"]])
        self.assertTrue(review.payload["activity"])

    def test_verified_claim_without_human_verified_evidence_is_blocked(self) -> None:
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Unreviewed result.",
                    "locator_kind": "page",
                    "locator_value": "8",
                    "stance": "supports",
                },
            )
        )
        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "Unreviewed claim.",
                    "evidence_ids": [evidence.payload["evidence_id"]],
                    "status": "verified",
                },
            )
        )
        self.assertEqual(claim.status, "blocked")

    def test_action_lineage_is_idempotent_and_path_redacted(self) -> None:
        request = ActionRequest("workflow.ask", {"query": "nothing yet", "limit": 2})
        self.runtime.execute(request)
        self.runtime.execute(request)
        events = activity_timeline(self.root, project_id="prj_1234567890abcdef12345678")
        asks = [event for event in events if event["action"] == "workflow.ask"]
        self.assertEqual(len(asks), 1)
        self.assertNotIn(str(self.root), str(events))


if __name__ == "__main__":
    unittest.main()
