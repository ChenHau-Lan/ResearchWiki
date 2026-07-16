from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime, available_actions
from rkf.core import Workspace
from rkf.lineage import activation_timeline, activity_timeline, lineage_root, object_origin_lookup
from rkf.lineage import input_fingerprint
from rkf.providers import AppraisalProviderResult, FullTextProviderResult, RetrievalHit
from rkf.research import _claim_content_fingerprint, _evidence_content_fingerprint
from rkf.schema import normalize_paper_state
from rkf.session import SessionMode


class RKFV1Tests(unittest.TestCase):
    def test_private_values_affect_fingerprint_without_being_embedded(self) -> None:
        first = input_fingerprint({"raw_prompt": "first private prompt"})
        second = input_fingerprint({"raw_prompt": "second private prompt"})

        self.assertNotEqual(first, second)
        self.assertNotIn("private", first)

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
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        activated = self.runtime.execute(ActionRequest("rkf.activate"))
        self.assertEqual(activated.status, "ok")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def set_paper_access(self, access_state: str) -> None:
        paper = self.workspace.paths.knowledge / "papers" / "example.md"
        text = paper.read_text(encoding="utf-8")
        text = text.replace("access_state: abstract", f"access_state: {access_state}")
        text = text.replace("access_state: fulltext", f"access_state: {access_state}")
        paper.write_text(text, encoding="utf-8")

    def test_registry_exposes_only_five_workflows_and_connection_controls(self) -> None:
        self.assertEqual(
            set(available_actions()),
            {
                "rkf.activate", "rkf.status", "rkf.deactivate", "connect.validate",
                "workflow.add", "workflow.ask", "workflow.read",
                "workflow.compare-synthesize", "workflow.review",
            },
        )

    def test_default_runtime_rejects_internal_legacy_actions(self) -> None:
        result = self.runtime.execute(ActionRequest("world.render"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_ACTION_NOT_AVAILABLE")

    def test_connection_can_be_validated_before_activation(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)

        result = runtime.execute(ActionRequest("connect.validate"))

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["project_id"], "prj_1234567890abcdef12345678")
        self.assertEqual(result.payload["status"], "connected")

    def test_status_lists_open_projects_without_exposing_folder_paths(self) -> None:
        second_root = self.root / "second-project"
        second_root.mkdir()
        second_root.joinpath(".rkf-connect.toml").write_text(
            "version = 2\n\n[rkf]\n"
            "available = true\nactivation = \"manual\"\nquery_first = true\n"
            "capture_mode = \"active-aggressive\"\n"
            "project_id = \"prj_abcdef1234567890abcdef12\"\n"
            "project_name = \"Second Project\"\n"
            "marker_schema = \"rkf-connect-v2\"\n"
            "connector_version = \"1.1.0\"\n"
            "connected_at = \"2026-07-15T00:00:00Z\"\n",
            encoding="utf-8",
        )
        second = RKFActionRuntime(workspace=self.workspace, project_root=second_root)
        self.assertEqual(second.execute(ActionRequest("rkf.activate")).status, "ok")

        status = self.runtime.execute(ActionRequest("rkf.status"))

        self.assertEqual(status.payload["active_project_count"], 2)
        self.assertEqual(status.payload["open_activation_count"], 2)
        self.assertEqual(
            {project["project_name"] for project in status.payload["active_projects"]},
            {"Test Project", "Second Project"},
        )
        self.assertNotIn(str(self.root), json.dumps(status.payload))

    def test_blocked_activation_with_valid_project_id_is_a_failed_event(self) -> None:
        blocked_root = self.root / "blocked-project"
        blocked_root.mkdir()
        blocked_root.joinpath(".rkf-connect.toml").write_text(
            "version = 2\n\n[rkf]\n"
            "available = true\nactivation = \"manual\"\nquery_first = true\n"
            "capture_mode = \"active-aggressive\"\n"
            "project_id = \"prj_abcdef1234567890abcdef12\"\n"
            "project_name = \"Blocked Project\"\n"
            "marker_schema = \"rkf-connect-v2\"\n"
            "connector_version = \"2.0.0\"\n"
            "connected_at = \"2026-07-15T00:00:00Z\"\n",
            encoding="utf-8",
        )
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=blocked_root)

        result = runtime.execute(ActionRequest("rkf.activate"))
        timeline = activation_timeline(
            self.root,
            project_id="prj_abcdef1234567890abcdef12",
        )

        self.assertEqual(result.status, "failed")
        self.assertRegex(result.payload["activation_id"], r"^act_[a-f0-9]{24}$")
        self.assertEqual([event["transition"] for event in timeline], ["failed"])

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
        self.set_paper_access("fulltext")
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
        self.assertEqual(
            synthesis.payload["evidence_matrix"][0]["locator"],
            {"kind": "figure", "value": "Fig. 3"},
        )
        self.assertEqual(
            evidence.payload["object_fingerprints"][evidence.payload["evidence_id"]],
            evidence.payload["content_fingerprint"],
        )
        self.assertEqual(
            claim.payload["object_fingerprints"][claim.payload["claim_id"]],
            claim.payload["content_fingerprint"],
        )
        self.assertEqual(
            synthesis.payload["object_fingerprints"][synthesis.payload["synthesis_id"]],
            synthesis.payload["content_fingerprint"],
        )
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

    def test_claim_rejects_tampered_evidence_cards_and_noncanonical_papers(self) -> None:
        self.set_paper_access("fulltext")
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Human-checked result for tamper regression.",
                    "locator_kind": "page",
                    "locator_value": "8",
                    "stance": "supports",
                    "verification_state": "human-verified",
                },
            )
        )
        self.assertEqual(evidence.status, "ok")
        evidence_id = evidence.payload["evidence_id"]
        card_path = self.workspace.paths.evidence_index / "cards" / f"{evidence_id}.json"
        original = json.loads(card_path.read_text(encoding="utf-8"))

        tampered_cards = {
            "schema": {**original, "schema": "rkf-evidence-drifted"},
            "id": {**original, "evidence_id": "ev_00000000000000000000"},
            "paper": {**original, "paper_id": "papers/missing"},
            "locator": {**original, "locator": {"kind": "url", "value": "https://example.test"}},
            "stance": {**original, "stance": "mentions"},
            "verification": {**original, "verification_state": "auto-verified"},
            "manual-copy": {key: value for key, value in original.items() if key != "content_fingerprint"},
        }
        for label, tampered in tampered_cards.items():
            with self.subTest(label=label):
                card_path.write_text(
                    json.dumps(tampered, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                claim = self.runtime.execute(
                    ActionRequest(
                        "workflow.compare-synthesize",
                        {
                            "operation": "claim",
                            "statement": f"Tampered evidence must fail closed: {label}.",
                            "evidence_ids": [evidence_id],
                            "status": "verified",
                        },
                    )
                )
                self.assertEqual(claim.status, "blocked")
                self.assertEqual(claim.payload["error_code"], "RKF_SYNTHESIS_REJECTED")

        card_path.write_text(
            json.dumps(original, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        paper_path = self.workspace.paths.knowledge / "papers" / "example.md"
        canonical_paper = paper_path.read_text(encoding="utf-8")
        paper_path.write_text(
            canonical_paper.replace("schema: rkf-paper-v1.1", "schema: legacy-paper"),
            encoding="utf-8",
        )
        noncanonical = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "Evidence with a noncanonical Paper must fail closed.",
                    "evidence_ids": [evidence_id],
                    "status": "verified",
                },
            )
        )
        self.assertEqual(noncanonical.status, "blocked")
        self.assertEqual(noncanonical.payload["error_code"], "RKF_SYNTHESIS_REJECTED")

    def test_manual_verification_edit_cannot_promote_a_verified_claim(self) -> None:
        self.set_paper_access("fulltext")
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "This evidence has not been human checked.",
                    "locator_kind": "paragraph",
                    "locator_value": "Results para. 2",
                    "stance": "supports",
                    "verification_state": "unreviewed",
                },
            )
        )
        evidence_id = evidence.payload["evidence_id"]
        card_path = self.workspace.paths.evidence_index / "cards" / f"{evidence_id}.json"
        tampered = json.loads(card_path.read_text(encoding="utf-8"))
        tampered["verification_state"] = "human-verified"
        tampered["content_fingerprint"] = _evidence_content_fingerprint(tampered)
        card_path.write_text(
            json.dumps(tampered, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "A manual card edit cannot establish verification.",
                    "evidence_ids": [evidence_id],
                    "status": "verified",
                },
            )
        )

        self.assertEqual(claim.status, "blocked")
        self.assertEqual(claim.payload["error_code"], "RKF_SYNTHESIS_REJECTED")

    def test_governed_evidence_review_can_promote_a_verified_claim(self) -> None:
        self.set_paper_access("fulltext")
        params = {
            "paper_id": "papers/example",
            "summary": "A governed review may verify this bounded result.",
            "locator_kind": "table",
            "locator_value": "Table 2",
            "stance": "supports",
        }
        unreviewed = self.runtime.execute(ActionRequest("workflow.read", params))
        reviewed = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {**params, "verification_state": "human-verified"},
            )
        )
        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "The governed human review verifies this bounded result.",
                    "evidence_ids": [reviewed.payload["evidence_id"]],
                    "status": "verified",
                },
            )
        )

        self.assertEqual(unreviewed.payload["evidence_id"], reviewed.payload["evidence_id"])
        self.assertNotEqual(
            unreviewed.payload["content_fingerprint"],
            reviewed.payload["content_fingerprint"],
        )
        self.assertEqual(claim.status, "ok")

    def test_direct_read_cannot_human_verify_above_paper_access(self) -> None:
        result = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "An abstract cannot verify a full-text locator.",
                    "locator_kind": "figure",
                    "locator_value": "Fig. 9",
                    "stance": "supports",
                    "verification_state": "human-verified",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_EVIDENCE_REJECTED")

    def test_synthesis_revalidates_verified_claim_after_evidence_downgrade(self) -> None:
        self.set_paper_access("fulltext")
        params = {
            "paper_id": "papers/example",
            "summary": "A current human review is required.",
            "locator_kind": "section",
            "locator_value": "Results",
            "stance": "supports",
        }
        verified = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {**params, "verification_state": "human-verified"},
            )
        )
        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "This claim depends on current human verification.",
                    "evidence_ids": [verified.payload["evidence_id"]],
                    "status": "verified",
                },
            )
        )
        downgraded = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {**params, "verification_state": "unreviewed"},
            )
        )
        synthesis = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": "Is the verification still current?",
                    "claim_ids": [claim.payload["claim_id"]],
                },
            )
        )

        self.assertEqual(verified.payload["evidence_id"], downgraded.payload["evidence_id"])
        self.assertEqual(synthesis.status, "blocked")
        self.assertEqual(synthesis.payload["error_code"], "RKF_SYNTHESIS_REJECTED")

    def test_synthesis_rejects_recomputed_tampered_claim_and_traversal_id(self) -> None:
        self.set_paper_access("fulltext")
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Legitimate supporting evidence.",
                    "locator_kind": "page",
                    "locator_value": "4",
                    "stance": "supports",
                    "verification_state": "human-verified",
                },
            )
        )
        claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "This claim was only supported when recorded.",
                    "evidence_ids": [evidence.payload["evidence_id"]],
                    "status": "supported",
                },
            )
        )
        claim_path = self.workspace.paths.state / "claims" / f"{claim.payload['claim_id']}.json"
        tampered = json.loads(claim_path.read_text(encoding="utf-8"))
        tampered["status"] = "verified"
        tampered["content_fingerprint"] = _claim_content_fingerprint(tampered)
        claim_path.write_text(
            json.dumps(tampered, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        drifted = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": "Can a claim status be edited manually?",
                    "claim_ids": [claim.payload["claim_id"]],
                },
            )
        )
        traversal = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": "Can a claim id escape its root?",
                    "claim_ids": ["../../crafted"],
                },
            )
        )

        self.assertEqual(drifted.status, "blocked")
        self.assertEqual(traversal.status, "blocked")
        self.assertEqual(traversal.payload["error_code"], "RKF_SYNTHESIS_REJECTED")

    def test_read_scope_and_generic_inference_gates(self) -> None:
        blocked = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "digest",
                    "reading_scope": "abstract",
                },
            )
        )
        appraised = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "abstract",
                    "citation_checks": [
                        {"citation": "Example 2026", "exists": True, "supports_claim": False},
                        {"citation": "Remote check", "check_status": "failed", "reason": "offline"},
                    ],
                    "inference_checks": [
                        {"evidence_kind": "association", "claim_kind": "causal"},
                        {"evidence_kind": "surrogate-outcome", "claim_kind": "hard-outcome"},
                        {"evidence_kind": "single-study", "claim_kind": "consistency"},
                        {"evidence_kind": "subgroup", "claim_kind": "general-benefit"},
                        {"evidence_kind": "mechanistic-plausibility", "claim_kind": "outcome"},
                    ],
                },
            )
        )

        self.assertEqual(blocked.payload["error_code"], "RKF_READ_NEEDS_FULLTEXT")
        self.assertEqual(appraised.status, "ok")
        self.assertEqual(len(appraised.payload["inference_flags"]), 5)
        self.assertEqual(appraised.payload["trust"], "low")
        self.assertTrue(appraised.payload["failed_checks"])

    def test_read_requires_existing_paper_and_cannot_overstate_fulltext_scope(self) -> None:
        missing = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/missing",
                    "intent": "appraise",
                    "reading_scope": "metadata",
                },
            )
        )
        overstated = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "digest",
                    "reading_scope": "fulltext",
                },
            )
        )
        appraisal_overstated = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "partial",
                },
            )
        )
        missing_evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/missing",
                    "summary": "This must not be recorded.",
                    "locator_kind": "page",
                    "locator_value": "1",
                },
            )
        )

        self.assertEqual(missing.status, "blocked")
        self.assertEqual(missing.payload["error_code"], "RKF_READ_REJECTED")
        self.assertEqual(overstated.status, "blocked")
        self.assertEqual(overstated.payload["error_code"], "RKF_READ_NEEDS_FULLTEXT")
        self.assertEqual(appraisal_overstated.status, "blocked")
        self.assertEqual(appraisal_overstated.payload["error_code"], "RKF_READ_SCOPE_EXCEEDS_ACCESS")
        self.assertEqual(missing_evidence.status, "blocked")
        self.assertEqual(missing_evidence.payload["error_code"], "RKF_EVIDENCE_REJECTED")

        paper = self.workspace.paths.knowledge / "papers" / "example.md"
        text = paper.read_text(encoding="utf-8").replace(
            "access_state: abstract",
            "access_state: fulltext",
        )
        paper.write_text(text, encoding="utf-8")
        allowed = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "digest",
                    "reading_scope": "fulltext",
                },
            )
        )
        self.assertEqual(allowed.status, "ok")
        self.assertEqual(allowed.payload["reading_scope"], "fulltext")
        self.assertEqual(allowed.payload["trust"], "bounded")

    def test_read_rejects_invalid_canonical_paper_access_state(self) -> None:
        paper = self.workspace.paths.knowledge / "papers" / "example.md"
        paper.write_text(
            paper.read_text(encoding="utf-8").replace(
                "access_state: abstract",
                "access_state: unknown",
            ),
            encoding="utf-8",
        )

        result = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "metadata",
                },
            )
        )
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Invalid Paper state must not back Evidence.",
                    "locator_kind": "page",
                    "locator_value": "1",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_READ_REJECTED")
        self.assertEqual(evidence.status, "blocked")
        self.assertEqual(evidence.payload["error_code"], "RKF_EVIDENCE_REJECTED")

    def test_paper_root_symlink_is_rejected_by_read_and_acquisition(self) -> None:
        paper_root = self.workspace.paths.knowledge / "papers"
        relocated = self.root / "relocated-papers"
        paper_root.rename(relocated)
        paper_root.symlink_to(relocated, target_is_directory=True)

        read = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "abstract",
                },
            )
        )
        acquisition = self.runtime.execute(
            ActionRequest(
                "workflow.add",
                {
                    "operation": "acquire",
                    "source_id": "example",
                    "identifier": "10.1234/example",
                    "paper_id": "papers/example",
                },
            )
        )

        self.assertEqual(read.status, "blocked")
        self.assertEqual(acquisition.status, "blocked")
        self.assertEqual(acquisition.payload["error_code"], "RKF_ACQUISITION_PAPER_INVALID")

    def test_state_object_roots_and_read_runs_reject_symlinks(self) -> None:
        outside_cards = self.root / "outside-cards"
        outside_read_runs = self.root / "outside-read-runs"
        outside_cards.mkdir()
        outside_read_runs.mkdir()
        cards_root = self.workspace.paths.evidence_index / "cards"
        cards_root.parent.mkdir(parents=True, exist_ok=True)
        cards_root.symlink_to(outside_cards, target_is_directory=True)
        read_runs_root = self.workspace.paths.state / "read_runs"
        read_runs_root.symlink_to(outside_read_runs, target_is_directory=True)

        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "A symlinked Evidence root must fail closed.",
                    "locator_kind": "page",
                    "locator_value": "1",
                },
            )
        )
        read_pass = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "abstract",
                },
            )
        )
        review = self.runtime.execute(ActionRequest("workflow.review"))

        self.assertEqual(evidence.status, "blocked")
        self.assertEqual(read_pass.status, "blocked")
        self.assertEqual(review.status, "blocked")
        self.assertEqual(list(outside_cards.iterdir()), [])
        self.assertEqual(list(outside_read_runs.iterdir()), [])

    def test_review_rejects_symlinked_paper_entry_without_reading_external_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "private-paper.md"
            private_text = (
                "---\ntype: paper\nreview_state: PRIVATE-EXTERNAL-MARKER\n---\n\n"
                "# Outside workspace\n"
            )
            outside.write_text(private_text, encoding="utf-8")
            linked = self.workspace.paths.knowledge / "linked-private-paper.md"
            linked.parent.mkdir(parents=True, exist_ok=True)
            linked.symlink_to(outside)

            review = self.runtime.execute(ActionRequest("workflow.review"))

            self.assertEqual(review.status, "blocked")
            self.assertEqual(review.payload["error_code"], "RKF_REVIEW_REJECTED")
            self.assertNotIn("PRIVATE-EXTERNAL-MARKER", json.dumps(review.payload))
            self.assertEqual(outside.read_text(encoding="utf-8"), private_text)

    def test_review_rejects_symlinked_papers_root(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            paper_root = self.workspace.paths.knowledge / "papers"
            local_root = self.workspace.paths.knowledge / "papers-local"
            paper_root.rename(local_root)
            paper_root.symlink_to(Path(outside_directory), target_is_directory=True)

            review = self.runtime.execute(ActionRequest("workflow.review"))

            self.assertEqual(review.status, "blocked")
            self.assertEqual(review.payload["error_code"], "RKF_REVIEW_REJECTED")

    def test_review_rejects_symlinked_retrieval_run_without_reading_external_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / ("rrun_" + "a" * 24 + ".json")
            private_payload = {
                "schema": "rkf-retrieval-run-v1",
                "retrieval_run_id": "rrun_" + "a" * 24,
                "provider": "PRIVATE-EXTERNAL-PROVIDER",
            }
            outside.write_text(json.dumps(private_payload), encoding="utf-8")
            retrieval_root = self.workspace.paths.state / "retrieval_runs"
            retrieval_root.mkdir(parents=True, exist_ok=True)
            linked = retrieval_root / outside.name
            linked.symlink_to(outside)

            review = self.runtime.execute(ActionRequest("workflow.review"))

            self.assertEqual(review.status, "blocked")
            self.assertEqual(review.payload["error_code"], "RKF_REVIEW_REJECTED")
            self.assertNotIn("PRIVATE-EXTERNAL-PROVIDER", json.dumps(review.payload))
            self.assertEqual(json.loads(outside.read_text(encoding="utf-8")), private_payload)

    def test_claim_and_synthesis_roots_reject_symlinks(self) -> None:
        evidence = self.runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "summary": "Unreviewed Evidence for path containment.",
                    "locator_kind": "section",
                    "locator_value": "Abstract",
                },
            )
        )
        outside_claims = self.root / "outside-claims"
        outside_claims.mkdir()
        claims_root = self.workspace.paths.state / "claims"
        claims_root.symlink_to(outside_claims, target_is_directory=True)
        blocked_claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "A symlinked Claim root must fail closed.",
                    "evidence_ids": [evidence.payload["evidence_id"]],
                    "status": "proposed",
                },
            )
        )
        self.assertEqual(blocked_claim.status, "blocked")
        self.assertEqual(list(outside_claims.iterdir()), [])

        claims_root.unlink()
        valid_claim = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "A valid Claim for synthesis containment.",
                    "evidence_ids": [evidence.payload["evidence_id"]],
                    "status": "proposed",
                },
            )
        )
        outside_syntheses = self.root / "outside-syntheses"
        outside_syntheses.mkdir()
        syntheses_root = self.workspace.paths.state / "syntheses"
        syntheses_root.symlink_to(outside_syntheses, target_is_directory=True)
        blocked_synthesis = self.runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": "Can synthesis escape through a symlink?",
                    "claim_ids": [valid_claim.payload["claim_id"]],
                },
            )
        )

        self.assertEqual(valid_claim.status, "ok")
        self.assertEqual(blocked_synthesis.status, "blocked")
        self.assertEqual(list(outside_syntheses.iterdir()), [])

    def test_acquisition_rejects_noncanonical_paper_before_provider_call(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            def obtain(self, **_: object) -> FullTextProviderResult:
                self.calls += 1
                return FullTextProviderResult(
                    status="obtained",
                    provider="should-not-run",
                    provider_version="1",
                    artifact_sha256="c" * 64,
                    pdf_magic_validated=True,
                )

        paper = self.workspace.paths.knowledge / "papers" / "legacy.md"
        paper.write_text(
            "---\ntype: paper\nsource_id: legacy\naccess_state: metadata\n"
            "review_state: unread\n---\n\n# Legacy\n",
            encoding="utf-8",
        )
        provider = Provider()
        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            full_text_provider=provider,
        )
        runtime.execute(ActionRequest("rkf.activate"))

        result = runtime.execute(
            ActionRequest(
                "workflow.add",
                {
                    "operation": "acquire",
                    "source_id": "legacy",
                    "identifier": "10.1234/legacy",
                    "paper_id": "papers/legacy",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_ACQUISITION_PAPER_INVALID")
        self.assertEqual(provider.calls, 0)

    def test_optional_appraisal_profile_stays_a_coded_non_promoting_pass(self) -> None:
        class Provider:
            def appraise(self, **_: object) -> AppraisalProviderResult:
                return AppraisalProviderResult(
                    status="completed",
                    provider="fixture-appraisal",
                    provider_version="1",
                    profile="domain-fixture",
                    flags=("DOMAIN_LIMITATION",),
                )

        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            appraisal_provider=Provider(),
        )
        runtime.execute(ActionRequest("rkf.activate"))

        result = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": "papers/example",
                    "intent": "appraise",
                    "reading_scope": "abstract",
                    "appraisal_profile": "domain-fixture",
                },
            )
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["appraisal"]["flags"], ["DOMAIN_LIMITATION"])
        self.assertEqual(result.payload["trust"], "low")
        self.assertEqual(result.payload["promotion"], "none")

    def test_activation_closure_is_append_only(self) -> None:
        activation_id = self.runtime.session.activation_id
        snapshot = lineage_root(self.root) / "activations" / f"{activation_id}.json"
        before = snapshot.read_bytes()

        self.runtime.execute(ActionRequest("rkf.deactivate"))

        self.assertEqual(snapshot.read_bytes(), before)
        transitions = activation_timeline(self.root, activation_id=activation_id)
        self.assertEqual([item["transition"] for item in transitions], ["started", "closed"])

    def test_fulltext_provider_result_creates_one_checksum_artifact(self) -> None:
        class Provider:
            def obtain(self, **_: object) -> FullTextProviderResult:
                return FullTextProviderResult(
                    status="obtained",
                    provider="fixture",
                    provider_version="1",
                    artifact_sha256="a" * 64,
                    pdf_magic_validated=True,
                    private_artifact_handle="private://fixture",
                )

        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            full_text_provider=Provider(),
        )
        paper_path = self.workspace.paths.knowledge / "papers" / "doi_10_example.md"
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        paper_path.write_text(
            "---\n"
            "schema: rkf-paper-v1.1\n"
            "type: paper\n"
            "source_id: doi_10_example\n"
            "access_state: metadata\n"
            "review_state: unread\n"
            "reading_state: metadata-only\n"
            "reading_status: metadata-only\n"
            "fulltext_status: needs-user-pdf\n"
            "---\n\n# Fixture Paper\n",
            encoding="utf-8",
        )
        runtime.execute(ActionRequest("rkf.activate"))
        request = ActionRequest(
            "workflow.add",
            {
                "operation": "acquire",
                "source_id": "doi_10_example",
                "identifier": "10.1234/example",
                "paper_id": "papers/doi_10_example",
            },
        )

        first = runtime.execute(request)
        second = runtime.execute(request)

        self.assertEqual(first.status, "obtained")
        self.assertEqual(first.payload["artifact"]["artifact_id"], second.payload["artifact"]["artifact_id"])
        self.assertEqual(first.payload["paper_state"]["access_state"], "fulltext")
        self.assertIn("access_state: fulltext", paper_path.read_text(encoding="utf-8"))
        self.assertIn("reading_state: fulltext-available", paper_path.read_text(encoding="utf-8"))
        self.assertNotIn("private_artifact_handle", first.payload)
        self.assertEqual(len(list((self.root / "state" / "evidence" / "artifacts").glob("*.json"))), 1)

    def test_retryable_acquisition_success_appends_transition_and_review_uses_latest(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            def obtain(self, **_: object) -> FullTextProviderResult:
                self.calls += 1
                if self.calls == 1:
                    return FullTextProviderResult(
                        status="retryable",
                        provider="fixture",
                        provider_version="1",
                        blocker_codes=("PROVIDER_TIMEOUT",),
                    )
                return FullTextProviderResult(
                    status="obtained",
                    provider="fixture",
                    provider_version="1",
                    artifact_sha256="b" * 64,
                    pdf_magic_validated=True,
                    private_artifact_handle="private://fixture-retry",
                )

        paper_id = "papers/retryable"
        paper_path = self.workspace.paths.knowledge / f"{paper_id}.md"
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        paper_path.write_text(
            "---\n"
            "schema: rkf-paper-v1.1\n"
            "type: paper\n"
            "source_id: retryable\n"
            "access_state: metadata\n"
            "review_state: unread\n"
            "fulltext_status: needs-user-pdf\n"
            "---\n\n# Retryable Paper\n",
            encoding="utf-8",
        )
        provider = Provider()
        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            full_text_provider=provider,
        )
        runtime.execute(ActionRequest("rkf.activate"))
        request = ActionRequest(
            "workflow.add",
            {
                "operation": "acquire",
                "source_id": "retryable",
                "identifier": "10.1234/retryable",
                "paper_id": paper_id,
            },
        )

        retryable = runtime.execute(request)
        obtained = runtime.execute(request)
        repeated = runtime.execute(request)

        self.assertEqual(retryable.status, "retryable")
        self.assertEqual(obtained.status, "obtained")
        self.assertNotEqual(retryable.payload["lineage_event_id"], obtained.payload["lineage_event_id"])
        self.assertEqual(repeated.payload["lineage_event_id"], obtained.payload["lineage_event_id"])

        raw_events = activity_timeline(
            self.root,
            activation_id=runtime.session.activation_id,
            action="workflow.add",
        )
        self.assertEqual([event["status"] for event in raw_events], ["retryable", "obtained"])
        self.assertEqual([event["attempt"] for event in raw_events], [1, 2])
        self.assertEqual(raw_events[1]["supersedes_event_id"], raw_events[0]["event_id"])

        raw_origin = object_origin_lookup(self.root, paper_id)
        effective_origin = object_origin_lookup(self.root, paper_id, effective_only=True)
        self.assertEqual([event["status"] for event in raw_origin], ["retryable", "obtained"])
        self.assertEqual([event["status"] for event in effective_origin], ["obtained"])

        review = runtime.execute(ActionRequest("workflow.review", {"target_object_id": paper_id}))
        retryable_review = runtime.execute(ActionRequest("workflow.review", {"status": "retryable"}))
        self.assertEqual([event["status"] for event in review.payload["activity"]], ["obtained"])
        self.assertEqual([event["status"] for event in review.payload["object_origin"]], ["obtained"])
        self.assertEqual(review.payload["acquisition_needs_attention"], [])
        self.assertEqual(retryable_review.payload["activity"], [])

    def test_missing_fulltext_provider_creates_manual_handoff_visible_in_review(self) -> None:
        paper_path = self.workspace.paths.knowledge / "papers" / "manual.md"
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        paper_path.write_text(
            "---\nschema: rkf-paper-v1.1\ntype: paper\nsource_id: manual\naccess_state: metadata\n"
            "review_state: unread\n---\n\n# Manual fixture\n",
            encoding="utf-8",
        )

        result = self.runtime.execute(
            ActionRequest(
                "workflow.add",
                {
                    "operation": "acquire",
                    "source_id": "manual",
                    "identifier": "10.1234/manual",
                    "paper_id": "papers/manual",
                },
            )
        )
        review = self.runtime.execute(ActionRequest("workflow.review", {"status": "manual-required"}))

        self.assertEqual(result.status, "manual-required")
        self.assertEqual(result.payload["resolver_handoff"], "provide-authorized-pdf-or-resolver-link")
        self.assertEqual(len(review.payload["acquisition_needs_attention"]), 1)

    def test_semantic_provider_falls_back_behind_exact_and_filters_private_hits(self) -> None:
        for stem, title, summary in (
            ("semantic-public", "Canonical Public Paper", "Governed public summary."),
            ("semantic-private", "Canonical Private Paper", "Governed private summary."),
            ("semantic-missing-scope", "Canonical Missing Scope Paper", "Governed missing-scope summary."),
        ):
            path = self.workspace.paths.knowledge / "papers" / f"{stem}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n"
                "type: paper\n"
                f"source_id: {stem}\n"
                "access_state: metadata\n"
                "review_state: unread\n"
                "---\n\n"
                f"# {title}\n\n{summary}\n",
                encoding="utf-8",
            )

        class Provider:
            name = "fixture-semantic"
            version = "1"

            def __init__(self) -> None:
                self.requested_scopes: list[str] = []

            def search(self, **params: object) -> list[RetrievalHit]:
                self.requested_scopes.append(str(params.get("index_scope", "")))
                return [
                    RetrievalHit(
                        object_id="papers/semantic-public",
                        locator="section:Results",
                        score=0.99,
                        match_reason="semantic",
                        metadata={
                            "object_type": "paper",
                            "index_scope": "public-safe",
                            "path": "/private/project/article.txt",
                            "title": "PRIVATE PROVIDER TITLE",
                            "summary": "PRIVATE PROVIDER SUMMARY",
                        },
                    ),
                    RetrievalHit(
                        object_id="papers/semantic-private",
                        locator="page:1",
                        score=1.0,
                        match_reason="semantic",
                        metadata={"object_type": "paper", "index_scope": "private-fulltext"},
                    ),
                    RetrievalHit(
                        object_id="papers/semantic-missing-scope",
                        locator="section:Methods",
                        score=0.98,
                        match_reason="semantic",
                        metadata={"object_type": "paper"},
                    ),
                    RetrievalHit(
                        object_id="papers/not-canonical",
                        locator="section:Results",
                        score=0.97,
                        match_reason="semantic",
                        metadata={"object_type": "paper", "index_scope": "public-safe"},
                    ),
                ]

        provider = Provider()
        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            retrieval_provider=provider,
        )
        runtime.execute(ActionRequest("rkf.activate"))
        result = runtime.execute(ActionRequest("workflow.ask", {"query": "unmatched query"}))

        ids = [card["id"] for card in result.payload["cards"]]
        self.assertIn("papers/semantic-public", ids)
        self.assertNotIn("papers/semantic-private", ids)
        self.assertNotIn("papers/semantic-missing-scope", ids)
        self.assertNotIn("papers/not-canonical", ids)
        public = next(card for card in result.payload["cards"] if card["id"] == "papers/semantic-public")
        self.assertEqual(public["path"], "knowledge/papers/semantic-public.md")
        self.assertEqual(public["title"], "Canonical Public Paper")
        self.assertEqual(public["summary"], "Governed public summary.")
        self.assertNotIn("PRIVATE PROVIDER", str(public))
        self.assertEqual(provider.requested_scopes, ["public-safe"])
        self.assertTrue(result.payload["retrieval_run_id"].startswith("rrun_"))
        review = runtime.execute(ActionRequest("workflow.review"))
        self.assertEqual(review.payload["retrieval_lineage"][0]["retrieval_run_id"], result.payload["retrieval_run_id"])
        self.assertEqual(review.payload["semantic_index_health"][0]["provider"], "fixture-semantic")

    def test_retrieval_result_identity_drives_run_and_lineage_successors(self) -> None:
        for stem in ("semantic-a", "semantic-b"):
            path = self.workspace.paths.knowledge / "papers" / f"{stem}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n"
                "type: paper\n"
                f"source_id: {stem}\n"
                "access_state: metadata\n"
                "review_state: unread\n"
                "---\n\n"
                f"# {stem}\n\nCanonical {stem} summary.\n",
                encoding="utf-8",
            )

        class Provider:
            name = "fixture-changing-semantic"
            version = "1"

            def __init__(self) -> None:
                self.calls = 0
                self.index_generation = "gen-1"

            def search(self, **_: object) -> list[RetrievalHit]:
                self.calls += 1
                if self.calls == 1:
                    object_id, score = "papers/semantic-a", 0.40
                else:
                    object_id = "papers/semantic-b"
                    score = 0.40 if self.calls == 2 else 0.70
                if self.calls >= 4:
                    self.index_generation = "gen-2"
                return [
                    RetrievalHit(
                        object_id=object_id,
                        locator="section:Results",
                        score=score,
                        match_reason="semantic",
                        metadata={"object_type": "paper", "index_scope": "public-safe"},
                    )
                ]

        provider = Provider()
        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            retrieval_provider=provider,
        )
        runtime.execute(ActionRequest("rkf.activate"))
        request = ActionRequest("workflow.ask", {"query": "provider-only-query"})

        results = [runtime.execute(request) for _ in range(5)]

        run_ids = [result.payload["retrieval_run_id"] for result in results]
        self.assertEqual(len(set(run_ids[:4])), 4)
        self.assertEqual(run_ids[3], run_ids[4])
        self.assertNotEqual(results[0].payload["cards"][0]["id"], results[1].payload["cards"][0]["id"])
        self.assertNotEqual(results[1].payload["cards"][0]["score"], results[2].payload["cards"][0]["score"])
        events = activity_timeline(
            self.root,
            activation_id=runtime.session.activation_id,
            action="workflow.ask",
        )
        self.assertEqual([event["attempt"] for event in events], [1, 2, 3, 4])
        self.assertEqual(
            [event["supersedes_event_id"] for event in events[1:]],
            [event["event_id"] for event in events[:-1]],
        )

    def test_read_only_ask_returns_results_without_shared_state_writes(self) -> None:
        path = self.workspace.paths.knowledge / "papers" / "read-only.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            "type: paper\n"
            "source_id: read-only\n"
            "access_state: metadata\n"
            "review_state: unread\n"
            "---\n\n"
            "# Read-only Ask\n\nread-only-token governed summary.\n",
            encoding="utf-8",
        )
        retrieval_root = self.workspace.paths.state / "retrieval_runs"
        before_retrieval = {
            item.name: item.read_bytes()
            for item in retrieval_root.glob("*.json")
        } if retrieval_root.exists() else {}
        self.runtime.session.mode = SessionMode.ACTIVE_READ_ONLY

        result = self.runtime.execute(ActionRequest("workflow.ask", {"query": "read-only-token"}))

        after_retrieval = {
            item.name: item.read_bytes()
            for item in retrieval_root.glob("*.json")
        } if retrieval_root.exists() else {}
        self.assertEqual(result.status, "ok")
        self.assertGreater(result.payload["count"], 0)
        self.assertFalse(result.payload["retrieval_persisted"])
        self.assertNotIn("retrieval_run_id", result.payload)
        self.assertRegex(result.payload["lineage_event_id"], r"^aevt_[a-f0-9]{24}$")
        self.assertEqual(after_retrieval, before_retrieval)
        events = activity_timeline(
            self.root,
            activation_id=self.runtime.session.activation_id,
            action="workflow.ask",
        )
        self.assertEqual(len(events), 1)
        self.assertIn("papers/read-only", events[0]["affected_object_ids"])

    def test_malformed_semantic_provider_hit_is_ignored(self) -> None:
        class Provider:
            name = "fixture-malformed"
            version = "1"

            def search(self, **_: object) -> list[object]:
                return [{"object_id": "not-a-typed-hit"}]

        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            retrieval_provider=Provider(),
        )
        runtime.execute(ActionRequest("rkf.activate"))

        result = runtime.execute(ActionRequest("workflow.ask", {"query": "unmatched query"}))

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["count"], 0)
        self.assertTrue(result.payload["provider"].endswith(":fallback"))

    def test_action_lineage_is_idempotent_and_path_redacted(self) -> None:
        request = ActionRequest("workflow.ask", {"query": "nothing yet", "limit": 2})
        first = self.runtime.execute(request)
        second = self.runtime.execute(request)
        events = activity_timeline(self.root, project_id="prj_1234567890abcdef12345678")
        asks = [event for event in events if event["action"] == "workflow.ask"]
        self.assertEqual(len(asks), 1)
        self.assertEqual(first.payload["lineage_event_id"], second.payload["lineage_event_id"])
        self.assertEqual(asks[0]["attempt"], 1)
        self.assertNotIn(str(self.root), str(events))


if __name__ == "__main__":
    unittest.main()
