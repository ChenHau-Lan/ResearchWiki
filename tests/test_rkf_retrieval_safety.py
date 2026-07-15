from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace
from rkf.retrieval import search_central_rkf
from rkf.session import SessionMode


PROJECT_ID = "prj_1234567890abcdef12345678"
ACTIVATION_ID = "act_1234567890abcdef12345678"


class StableEmptyProvider:
    name = "stable-empty"
    version = "1"
    index_generation = "gen-1"
    elapsed_ms = 0

    def __init__(self) -> None:
        self.calls = 0
        self.before_second_search = None

    def search(self, **_: object) -> list[object]:
        self.calls += 1
        if self.calls == 2 and self.before_second_search is not None:
            self.before_second_search()
        return []


class RKFRetrievalSafetyTests(unittest.TestCase):
    def test_existing_deterministic_run_is_read_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            first = search_central_rkf(
                workspace,
                "stable query",
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
            run_path = (
                workspace.paths.state
                / "retrieval_runs"
                / f"{first['retrieval_run_id']}.json"
            )
            before = run_path.read_bytes()

            second = search_central_rkf(
                workspace,
                "stable query",
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )

            self.assertEqual(second["retrieval_run_id"], first["retrieval_run_id"])
            self.assertEqual(run_path.read_bytes(), before)
            self.assertEqual(list(run_path.parent.glob(f".{run_path.name}.*.tmp")), [])

    def test_existing_run_with_mismatched_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            first = search_central_rkf(
                workspace,
                "stable query",
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
            run_path = (
                workspace.paths.state
                / "retrieval_runs"
                / f"{first['retrieval_run_id']}.json"
            )
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            payload["result_fingerprint"] = "sha256:" + "0" * 64
            run_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "existing retrieval run does not match its deterministic identity",
            ):
                search_central_rkf(
                    workspace,
                    "stable query",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

    def test_tampered_canonical_objects_cannot_upgrade_answer_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".rkf-connect.toml").write_text(
                "version = 2\n\n[rkf]\n"
                "available = true\nactivation = \"manual\"\nquery_first = true\n"
                "capture_mode = \"active-aggressive\"\n"
                f'project_id = "{PROJECT_ID}"\n'
                "project_name = \"Canonical Retrieval Safety\"\n"
                "marker_schema = \"rkf-connect-v2\"\n"
                "connector_version = \"1.1.0\"\n"
                "connected_at = \"2026-07-15T00:00:00Z\"\n",
                encoding="utf-8",
            )
            workspace = Workspace(root)
            workspace.paths.raw_root.mkdir(parents=True, exist_ok=True)
            paper = workspace.paths.knowledge / "papers" / "canonical.md"
            paper.parent.mkdir(parents=True, exist_ok=True)
            paper.write_text(
                "---\n"
                "schema: rkf-paper-v1.1\n"
                "type: paper\n"
                "source_id: canonical\n"
                "access_state: fulltext\n"
                "review_state: unread\n"
                "---\n\n# Canonical Paper\n",
                encoding="utf-8",
            )
            runtime = RKFActionRuntime(workspace=workspace, project_root=root)
            self.assertEqual(runtime.execute(ActionRequest("rkf.activate")).status, "ok")
            evidence = runtime.execute(
                ActionRequest(
                    "workflow.read",
                    {
                        "paper_id": "papers/canonical",
                        "summary": "Canonical locator-backed result.",
                        "locator_kind": "page",
                        "locator_value": "4",
                        "stance": "supports",
                    },
                )
            )
            claim = runtime.execute(
                ActionRequest(
                    "workflow.compare-synthesize",
                    {
                        "operation": "claim",
                        "statement": "Canonical evidence supports this claim.",
                        "evidence_ids": [evidence.payload["evidence_id"]],
                        "status": "supported",
                    },
                )
            )
            self.assertEqual(evidence.status, "ok")
            self.assertEqual(claim.status, "ok")
            evidence_path = (
                workspace.paths.evidence_index
                / "cards"
                / f"{evidence.payload['evidence_id']}.json"
            )
            claim_path = (
                workspace.paths.state / "claims" / f"{claim.payload['claim_id']}.json"
            )
            original_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            original_claim = json.loads(claim_path.read_text(encoding="utf-8"))

            legitimate = search_central_rkf(
                workspace,
                "Canonical locator-backed result.",
                page_types=["evidence"],
                persist_retrieval_run=False,
            )
            self.assertEqual(legitimate["answer_boundary"], "locator-backed")

            cases = (
                (
                    "tampered-evidence",
                    evidence_path,
                    {**original_evidence, "summary": "TAMPERED-EVIDENCE-TOKEN"},
                    "TAMPERED-EVIDENCE-TOKEN",
                    "evidence",
                ),
                (
                    "tampered-claim",
                    claim_path,
                    {**original_claim, "statement": "TAMPERED-CLAIM-TOKEN"},
                    "TAMPERED-CLAIM-TOKEN",
                    "claim",
                ),
                (
                    "not-public-safe",
                    evidence_path,
                    {**original_evidence, "public_safe": False},
                    "Canonical locator-backed result.",
                    "evidence",
                ),
            )
            for label, target, payload, query, object_type in cases:
                with self.subTest(label=label):
                    evidence_path.write_text(
                        json.dumps(original_evidence, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    claim_path.write_text(
                        json.dumps(original_claim, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    target.write_text(
                        json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )

                    result = search_central_rkf(
                        workspace,
                        query,
                        page_types=[object_type],
                        index_scope="public-safe",
                        persist_retrieval_run=False,
                    )

                    self.assertEqual(result["count"], 0)
                    self.assertEqual(result["answer_boundary"], "insufficient-evidence")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_retrieval_run_rejects_root_parent_and_target_symlinks(self) -> None:
        for component in ("root", "parent", "target"):
            with (
                self.subTest(component=component),
                tempfile.TemporaryDirectory() as directory,
                tempfile.TemporaryDirectory() as outside_directory,
            ):
                workspace = Workspace(Path(directory))
                outside_root = Path(outside_directory)
                provider = StableEmptyProvider()
                first = search_central_rkf(
                    workspace,
                    "fixed identity query",
                    retrieval_provider=provider,
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )
                state_root = workspace.paths.state
                run_parent = state_root / "retrieval_runs"
                run_target = run_parent / f"{first['retrieval_run_id']}.json"

                if component == "root":
                    escaped_root = outside_root / "escaped-state"

                    def replace_root() -> None:
                        state_root.replace(escaped_root)
                        state_root.symlink_to(escaped_root, target_is_directory=True)

                    provider.before_second_search = replace_root
                    escaped_target = escaped_root / "retrieval_runs" / run_target.name
                    before = run_target.read_bytes()
                elif component == "parent":
                    escaped_parent = outside_root / "escaped-runs"
                    run_parent.replace(escaped_parent)
                    run_parent.symlink_to(escaped_parent, target_is_directory=True)
                    escaped_target = escaped_parent / run_target.name
                    before = escaped_target.read_bytes()
                else:
                    escaped_target = outside_root / "escaped-run.json"
                    run_target.replace(escaped_target)
                    run_target.symlink_to(escaped_target)
                    before = escaped_target.read_bytes()

                with self.assertRaisesRegex(
                    ValueError,
                    rf"retrieval run {component} cannot be a symlink",
                ):
                    search_central_rkf(
                        workspace,
                        "fixed identity query",
                        retrieval_provider=provider,
                        project_id=PROJECT_ID,
                        activation_id=ACTIVATION_ID,
                    )

                self.assertEqual(escaped_target.read_bytes(), before)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_public_safe_search_never_reads_symlinked_entries(self) -> None:
        fixtures = {
            "paper": (
                "knowledge/papers/private.md",
                "---\ntype: paper\nsource_id: private\n---\n\n# Private\n\nSECRET-PAPER-TOKEN\n",
                "SECRET-PAPER-TOKEN",
            ),
            "source": (
                "state/sources/private.json",
                json.dumps({"source_id": "private", "title": "SECRET-SOURCE-TOKEN"}),
                "SECRET-SOURCE-TOKEN",
            ),
            "claim": (
                "state/claims/private.json",
                json.dumps({"claim_id": "clm_private", "statement": "SECRET-CLAIM-TOKEN"}),
                "SECRET-CLAIM-TOKEN",
            ),
            "synthesis": (
                "state/syntheses/private.json",
                json.dumps(
                    {
                        "synthesis_id": "syn_private",
                        "research_question": "SECRET-SYNTHESIS-TOKEN",
                    }
                ),
                "SECRET-SYNTHESIS-TOKEN",
            ),
        }
        for object_type, (relative_link, contents, secret) in fixtures.items():
            with (
                self.subTest(object_type=object_type),
                tempfile.TemporaryDirectory() as directory,
                tempfile.TemporaryDirectory() as outside_directory,
            ):
                workspace = Workspace(Path(directory))
                outside = Path(outside_directory) / f"{object_type}.fixture"
                outside.write_text(contents, encoding="utf-8")
                link = workspace.paths.wiki_root / relative_link
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside)

                result = search_central_rkf(
                    workspace,
                    secret,
                    page_types=[object_type],
                    index_scope="public-safe",
                    persist_retrieval_run=False,
                )

                self.assertEqual(result["count"], 0)
                self.assertNotIn(secret, json.dumps(result["cards"], ensure_ascii=False))
                self.assertEqual(outside.read_text(encoding="utf-8"), contents)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_public_safe_search_rejects_symlinked_collection_roots(self) -> None:
        fixtures = {
            "knowledge": ("knowledge", "paper"),
            "source": ("state/sources", "source"),
            "claim": ("state/claims", "claim"),
            "synthesis": ("state/syntheses", "synthesis"),
        }
        for label, (relative_root, object_type) in fixtures.items():
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory() as directory,
                tempfile.TemporaryDirectory() as outside_directory,
            ):
                workspace = Workspace(Path(directory))
                outside = Path(outside_directory)
                root = workspace.paths.wiki_root / relative_root
                root.parent.mkdir(parents=True, exist_ok=True)
                root.symlink_to(outside, target_is_directory=True)

                with self.assertRaisesRegex(
                    ValueError,
                    rf"retrieval {label} root cannot be a symlink",
                ):
                    search_central_rkf(
                        workspace,
                        "private token",
                        page_types=[object_type],
                        index_scope="public-safe",
                        persist_retrieval_run=False,
                    )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_read_only_ask_skips_symlinked_retrieval_parent(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            tempfile.TemporaryDirectory() as outside_directory,
        ):
            root = Path(directory)
            (root / ".rkf-connect.toml").write_text(
                "version = 2\n\n[rkf]\n"
                "available = true\nactivation = \"manual\"\nquery_first = true\n"
                "capture_mode = \"active-aggressive\"\n"
                f'project_id = "{PROJECT_ID}"\n'
                "project_name = \"Read Only Safety\"\n"
                "marker_schema = \"rkf-connect-v2\"\n"
                "connector_version = \"1.1.0\"\n"
                "connected_at = \"2026-07-15T00:00:00Z\"\n",
                encoding="utf-8",
            )
            workspace = Workspace(root)
            workspace.paths.raw_root.mkdir(parents=True, exist_ok=True)
            paper = workspace.paths.knowledge / "papers" / "read-only.md"
            paper.parent.mkdir(parents=True, exist_ok=True)
            paper.write_text(
                "---\ntype: paper\nsource_id: read-only\n---\n\n"
                "# Read Only\n\nread-only-safe-token\n",
                encoding="utf-8",
            )
            runtime = RKFActionRuntime(workspace=workspace, project_root=root)
            self.assertEqual(runtime.execute(ActionRequest("rkf.activate")).status, "ok")
            retrieval_parent = workspace.paths.state / "retrieval_runs"
            retrieval_parent.parent.mkdir(parents=True, exist_ok=True)
            retrieval_parent.symlink_to(Path(outside_directory), target_is_directory=True)
            runtime.session.mode = SessionMode.ACTIVE_READ_ONLY

            result = runtime.execute(
                ActionRequest("workflow.ask", {"query": "read-only-safe-token"})
            )

            self.assertEqual(result.status, "ok")
            self.assertFalse(result.payload["retrieval_persisted"])
            self.assertNotIn("retrieval_run_id", result.payload)
            self.assertEqual(list(Path(outside_directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
