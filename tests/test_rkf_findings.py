from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf import research
from rkf.actions import ActionRequest, RKFActionRuntime, available_actions
from rkf.core import Workspace
from rkf.research import _finding_content_fingerprint, load_canonical_evidence


class RKFFindingDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        raw = self.root / "raw"
        raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.root.as_posix()}"\n'
            f'raw_root = "{raw.as_posix()}"\n',
            encoding="utf-8",
        )
        (self.root / ".rkf-connect.toml").write_text(
            "version = 2\n\n[rkf]\n"
            "available = true\nactivation = \"manual\"\nquery_first = true\n"
            "capture_mode = \"active-aggressive\"\n"
            "project_id = \"prj_1234567890abcdef12345678\"\n"
            "project_name = \"Finding Test\"\n"
            "marker_schema = \"rkf-connect-v2\"\n"
            "connector_version = \"1.1.0\"\n"
            "connected_at = \"2026-07-15T00:00:00Z\"\n",
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        paper = self.workspace.paths.knowledge / "papers" / "example.md"
        paper.parent.mkdir(parents=True, exist_ok=True)
        paper.write_text(
            "---\n"
            "schema: rkf-paper-v1.1\n"
            "type: paper\n"
            "source_id: example\n"
            "access_state: abstract\n"
            "review_state: unread\n"
            "---\n\n# Example Paper\n",
            encoding="utf-8",
        )
        self.runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
        )
        self.assertEqual(
            self.runtime.execute(ActionRequest("rkf.activate")).status,
            "ok",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def set_paper_access(self, access_state: str) -> None:
        path = self.workspace.paths.knowledge / "papers" / "example.md"
        text = path.read_text(encoding="utf-8")
        for current in ("metadata", "abstract", "partial", "fulltext"):
            text = text.replace(
                f"access_state: {current}",
                f"access_state: {access_state}",
            )
        path.write_text(text, encoding="utf-8")

    def capture(
        self,
        *,
        summary: str,
        locator_state: str = "missing",
        locator: dict[str, str] | None = None,
        reading_scope: str = "abstract",
    ):
        params: dict[str, object] = {
            "operation": "capture-finding",
            "paper_id": "papers/example",
            "summary": summary,
            "reading_scope": reading_scope,
            "locator_state": locator_state,
        }
        if locator is not None:
            params["locator"] = locator
        return self.runtime.execute(ActionRequest("workflow.read", params))

    def test_missing_finding_is_canonical_and_review_reports_locator_debt(self) -> None:
        captured = self.capture(summary="Useful abstract-level observation.")

        self.assertEqual(captured.status, "ok")
        self.assertEqual(captured.payload["schema"], "rkf-finding-v1")
        self.assertEqual(captured.payload["locator_state"], "missing")
        self.assertNotIn("locator", captured.payload)
        self.assertRegex(captured.payload["finding_id"], r"^fd_[a-f0-9]{20}$")
        self.assertEqual(set(available_actions()) & {"capture-finding"}, set())

        review = self.runtime.execute(ActionRequest("workflow.review"))
        self.assertEqual(review.status, "ok")
        self.assertEqual(
            review.payload["finding_locator_debt"],
            [
                {
                    "finding_id": captured.payload["finding_id"],
                    "paper_id": "papers/example",
                    "reading_scope": "abstract",
                    "locator_state": "missing",
                    "missing": ["locator"],
                    "next_action": "add-locator",
                }
            ],
        )

    def test_missing_and_coarse_findings_cannot_promote(self) -> None:
        missing = self.capture(summary="Missing locator finding.")
        coarse = self.capture(
            summary="Coarse locator finding.",
            locator_state="coarse",
            locator={"kind": "section", "value": "Results area"},
        )

        for captured in (missing, coarse):
            promoted = self.runtime.execute(
                ActionRequest(
                    "workflow.read",
                    {
                        "operation": "promote-evidence",
                        "finding_id": captured.payload["finding_id"],
                    },
                )
            )
            self.assertEqual(promoted.status, "blocked")
            self.assertEqual(
                promoted.payload["error_code"],
                "RKF_FINDING_PROMOTION_REJECTED",
            )

    def test_finding_can_be_resolved_to_exact_and_promoted_through_existing_evidence_gate(self) -> None:
        captured = self.capture(summary="Finding that will be located exactly.")
        finding_id = captured.payload["finding_id"]
        resolved = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "finding_id": finding_id,
                    "locator_state": "exact",
                    "locator": {"kind": "page", "value": "8"},
                },
            )
        )
        promoted = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "promote-evidence",
                    "finding_id": finding_id,
                    "stance": "supports",
                },
            )
        )

        self.assertEqual(resolved.status, "ok")
        self.assertEqual(resolved.payload["finding_id"], finding_id)
        self.assertEqual(resolved.payload["locator_state"], "exact")
        self.assertEqual(promoted.status, "ok")
        self.assertEqual(promoted.payload["schema"], "rkf-evidence-v1")
        self.assertEqual(promoted.payload["source_finding_id"], finding_id)
        self.assertEqual(promoted.payload["promotion"], "evidence")
        evidence = load_canonical_evidence(
            self.workspace,
            promoted.payload["evidence_id"],
        )
        self.assertEqual(evidence["locator"], {"kind": "page", "value": "8"})
        review = self.runtime.execute(ActionRequest("workflow.review"))
        self.assertEqual(review.payload["finding_locator_debt"], [])

    def test_implicit_semantic_match_is_idempotent_and_preserves_lineage(self) -> None:
        summary = "An exact finding captured once across activations."
        captured = self.capture(
            summary=summary,
            locator_state="exact",
            locator={"kind": "page", "value": "8"},
        )
        finding_id = captured.payload["finding_id"]
        path = self.workspace.paths.state / "findings" / f"{finding_id}.json"
        original = path.read_bytes()
        original_activation_id = captured.payload["activation_id"]

        self.assertEqual(
            self.runtime.execute(ActionRequest("rkf.deactivate")).status,
            "ok",
        )
        self.assertEqual(
            self.runtime.execute(ActionRequest("rkf.activate")).status,
            "ok",
        )
        self.assertNotEqual(self.runtime.session.activation_id, original_activation_id)

        repeated = self.capture(
            summary=summary,
            locator_state="exact",
            locator={"kind": "page", "value": "8"},
        )

        self.assertEqual(repeated.status, "ok")
        self.assertEqual(repeated.payload["finding_id"], finding_id)
        self.assertEqual(
            repeated.payload["findings"][0]["activation_id"],
            original_activation_id,
        )
        self.assertEqual(path.read_bytes(), original)

    def test_implicit_missing_capture_cannot_downgrade_exact_finding_or_lineage(self) -> None:
        summary = "An exact finding must not be implicitly downgraded."
        captured = self.capture(
            summary=summary,
            locator_state="exact",
            locator={"kind": "figure", "value": "Figure 2"},
        )
        finding_id = captured.payload["finding_id"]
        path = self.workspace.paths.state / "findings" / f"{finding_id}.json"
        original = path.read_bytes()
        original_record = json.loads(original)

        self.assertEqual(
            self.runtime.execute(ActionRequest("rkf.deactivate")).status,
            "ok",
        )
        self.assertEqual(
            self.runtime.execute(ActionRequest("rkf.activate")).status,
            "ok",
        )
        self.assertNotEqual(
            self.runtime.session.activation_id,
            original_record["activation_id"],
        )

        collision = self.capture(summary=summary)

        self.assertEqual(collision.status, "blocked")
        self.assertEqual(collision.payload["error_code"], "RKF_FINDING_REJECTED")
        self.assertIn("explicit finding_id", collision.message)
        self.assertEqual(path.read_bytes(), original)
        preserved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(preserved["locator_state"], "exact")
        self.assertEqual(preserved["locator"], {"kind": "figure", "value": "Figure 2"})
        self.assertEqual(
            preserved["activation_id"],
            original_record["activation_id"],
        )

    def test_scope_and_locator_changes_require_explicit_finding_id(self) -> None:
        summary = "A finding updated only through its explicit identifier."
        captured = self.capture(summary=summary)
        finding_id = captured.payload["finding_id"]
        self.set_paper_access("fulltext")

        implicit_scope_change = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "paper_id": "papers/example",
                    "summary": summary,
                    "reading_scope": "partial",
                    "locator_state": "missing",
                },
            )
        )
        self.assertEqual(implicit_scope_change.status, "blocked")
        self.assertIn("explicit finding_id", implicit_scope_change.message)

        explicit_scope_change = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "finding_id": finding_id,
                    "reading_scope": "partial",
                },
            )
        )
        self.assertEqual(explicit_scope_change.status, "ok")
        self.assertEqual(explicit_scope_change.payload["reading_scope"], "partial")

        implicit_locator_change = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "paper_id": "papers/example",
                    "summary": summary,
                    "reading_scope": "partial",
                    "locator_state": "exact",
                    "locator": {"kind": "table", "value": "Table 4"},
                },
            )
        )
        self.assertEqual(implicit_locator_change.status, "blocked")
        self.assertIn("explicit finding_id", implicit_locator_change.message)

        explicit_locator_change = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "finding_id": finding_id,
                    "locator_state": "exact",
                    "locator": {"kind": "table", "value": "Table 4"},
                },
            )
        )
        self.assertEqual(explicit_locator_change.status, "ok")
        self.assertEqual(explicit_locator_change.payload["locator_state"], "exact")
        self.assertEqual(
            explicit_locator_change.payload["locator"],
            {"kind": "table", "value": "Table 4"},
        )

    def test_direct_exact_locator_evidence_route_remains_compatible(self) -> None:
        direct = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Existing direct Evidence route.",
                    "locator_kind": "section",
                    "locator_value": "Abstract",
                    "stance": "contextualizes",
                },
            )
        )

        self.assertEqual(direct.status, "ok")
        self.assertEqual(direct.payload["schema"], "rkf-evidence-v1")
        self.assertNotIn("source_finding_id", direct.payload)

    def test_batch_prevalidation_prevents_partial_canonical_writes(self) -> None:
        result = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "paper_id": "papers/example",
                    "reading_scope": "abstract",
                    "findings": [
                        {
                            "summary": "This first item is valid.",
                            "locator_state": "missing",
                        },
                        {
                            "summary": "This second item lacks its exact locator.",
                            "locator_state": "exact",
                        },
                    ],
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_FINDING_REJECTED")
        root = self.workspace.paths.state / "findings"
        self.assertEqual(list(root.glob("*.json")) if root.exists() else [], [])

    def test_batch_write_failure_rolls_back_and_retry_succeeds(self) -> None:
        params = {
            "operation": "capture-finding",
            "paper_id": "papers/example",
            "reading_scope": "abstract",
            "findings": [
                {"summary": "First atomic finding.", "locator_state": "missing"},
                {"summary": "Second atomic finding.", "locator_state": "missing"},
            ],
        }
        original_write = research.write_canonical_state_json
        write_count = 0

        def fail_second_write(path, payload, *, label):
            nonlocal write_count
            if label == "finding":
                write_count += 1
                if write_count == 2:
                    raise OSError("injected second finding write failure")
            return original_write(path, payload, label=label)

        with patch(
            "rkf.research.write_canonical_state_json",
            side_effect=fail_second_write,
        ):
            failed = self.runtime.execute(ActionRequest("workflow.read", params))

        root = self.workspace.paths.state / "findings"
        self.assertEqual(failed.status, "blocked")
        self.assertEqual(failed.payload["error_code"], "RKF_FINDING_REJECTED")
        self.assertEqual(list(root.glob("*.json")) if root.exists() else [], [])

        retried = self.runtime.execute(ActionRequest("workflow.read", params))

        self.assertEqual(retried.status, "ok")
        self.assertEqual(retried.payload["count"], 2)
        self.assertEqual(len(list(root.glob("*.json"))), 2)

    def test_batch_receipt_failure_rolls_back_and_retry_succeeds(self) -> None:
        params = {
            "operation": "capture-finding",
            "paper_id": "papers/example",
            "reading_scope": "abstract",
            "findings": [
                {"summary": "First receipt finding.", "locator_state": "missing"},
                {"summary": "Second receipt finding.", "locator_state": "missing"},
            ],
        }
        with patch(
            "rkf.actions.record_action",
            side_effect=OSError("injected ActionEvent write failure"),
        ):
            with self.assertRaisesRegex(OSError, "ActionEvent write failure"):
                self.runtime.execute(ActionRequest("workflow.read", params))

        root = self.workspace.paths.state / "findings"
        self.assertEqual(list(root.glob("*.json")) if root.exists() else [], [])

        retried = self.runtime.execute(ActionRequest("workflow.read", params))

        self.assertEqual(retried.status, "ok")
        self.assertEqual(retried.payload["count"], 2)
        self.assertEqual(len(list(root.glob("*.json"))), 2)

    def test_promotion_rejects_a_recomputed_manual_edit_without_matching_receipt(self) -> None:
        captured = self.capture(
            summary="Receipt-backed exact finding.",
            locator_state="exact",
            locator={"kind": "page", "value": "4"},
        )
        finding_id = captured.payload["finding_id"]
        path = self.workspace.paths.state / "findings" / f"{finding_id}.json"
        tampered = json.loads(path.read_text(encoding="utf-8"))
        tampered["locator"] = {"kind": "page", "value": "999"}
        tampered["content_fingerprint"] = _finding_content_fingerprint(tampered)
        path.write_text(
            json.dumps(tampered, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        promoted = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "promote-evidence",
                    "finding_id": finding_id,
                },
            )
        )

        self.assertEqual(promoted.status, "blocked")
        self.assertEqual(
            promoted.payload["error_code"],
            "RKF_FINDING_PROMOTION_REJECTED",
        )
        self.assertIn("receipt", promoted.message)

    def test_proposed_claim_may_remain_evidence_free_but_supported_cannot(self) -> None:
        proposed = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "A proposal still needs Evidence.",
                    "evidence_ids": [],
                    "status": "proposed",
                },
            )
        )
        supported = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "Unsupported promotion must remain blocked.",
                    "evidence_ids": [],
                    "status": "supported",
                },
            )
        )

        self.assertEqual(proposed.status, "ok")
        self.assertEqual(supported.status, "blocked")
        self.assertEqual(supported.payload["error_code"], "RKF_SYNTHESIS_REJECTED")


if __name__ == "__main__":
    unittest.main()
