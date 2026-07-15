from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace
from rkf.providers import (
    ExternalCommandFullTextProvider,
    ExternalCommandRetrievalProvider,
    FullTextProviderResult,
    register_evidence_artifact,
)
from rkf.retrieval import search_central_rkf
from tools.validate_rkf_schema import validate_instance


PROJECT_ID = "prj_1234567890abcdef12345678"
ACTIVATION_ID = "act_1234567890abcdef12345678"


class RKFProviderTests(unittest.TestCase):
    def test_external_command_preserves_retryable_status(self) -> None:
        adapter = ExternalCommandFullTextProvider(
            [
                sys.executable,
                "-c",
                "import json; print(json.dumps({'status':'retryable','tried_routes':['open-access'],'blocker_codes':['BUSY']}))",
            ],
            provider="paper-fetch-smoke",
            provider_version="fixture",
        )

        result = adapter.obtain(
            source_id="doi_fixture",
            identifier="10.1234/fixture",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "retryable")
        self.assertNotEqual(result.status, "unavailable")
        self.assertEqual(result.tried_routes, ("open-access",))

    def test_nonzero_obtained_result_fails_closed(self) -> None:
        adapter = ExternalCommandFullTextProvider(
            [
                sys.executable,
                "-c",
                "import json,sys; print(json.dumps({'status':'obtained','artifact_sha256':'a'*64,'pdf_magic_validated':True})); sys.exit(2)",
            ],
            provider="paper-fetch-smoke",
            provider_version="fixture",
        )

        result = adapter.obtain(
            source_id="doi_fixture",
            identifier="10.1234/fixture",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "blocked")
        self.assertIn("PROVIDER_EXIT_NONZERO", result.blocker_codes)

    def test_public_route_rejects_absolute_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute paths"):
            FullTextProviderResult(
                status="manual-required",
                provider="fixture",
                provider_version="1",
                route="/private/provider/route",
            )

    def test_external_semantic_adapter_returns_locator_backed_typed_hits(self) -> None:
        payload = (
            "{'index_generation':'gen-1','elapsed_ms':7,'hits':["
            "{'object_id':'ev_fixture','locator':'section:Results','score':0.8,"
            "'metadata':{'object_type':'evidence','index_scope':'public-safe'}}]}"
        )
        adapter = ExternalCommandRetrievalProvider(
            [sys.executable, "-c", f"import ast,json; print(json.dumps(ast.literal_eval(\"{payload}\")))"],
            name="vault-search-smoke",
            version="fixture",
        )

        hits = adapter.search(
            query="fixture",
            limit=5,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(hits[0].object_id, "ev_fixture")
        self.assertEqual(hits[0].locator, "section:Results")
        self.assertEqual(adapter.index_generation, "gen-1")

    def test_external_semantic_adapter_receives_scope_and_rejects_missing_hit_scope(self) -> None:
        adapter = ExternalCommandRetrievalProvider(
            [sys.executable, "-c", "raise SystemExit(0)"],
            name="vault-search-scope",
            version="fixture",
        )
        scoped_output = {
            "index_generation": "gen-private",
            "hits": [
                {
                    "object_id": "ev_fixture",
                    "locator": "section:Results",
                    "score": 0.8,
                    "metadata": {
                        "object_type": "evidence",
                        "index_scope": "private-fulltext",
                    },
                }
            ],
        }
        completed = subprocess.CompletedProcess(
            adapter.command,
            0,
            stdout=json.dumps(scoped_output),
            stderr="",
        )
        with patch("rkf.providers.subprocess.run", return_value=completed) as run:
            adapter.search(
                query="fixture",
                limit=5,
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
                index_scope="private-fulltext",
            )

        request = json.loads(run.call_args.kwargs["input"])
        self.assertEqual(request["index_scope"], "private-fulltext")

        missing_scope = {
            "hits": [
                {
                    "object_id": "ev_fixture",
                    "locator": "section:Results",
                    "score": 0.8,
                    "metadata": {"object_type": "evidence"},
                }
            ]
        }
        completed = subprocess.CompletedProcess(
            adapter.command,
            0,
            stdout=json.dumps(missing_scope),
            stderr="",
        )
        with patch("rkf.providers.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(ValueError, "index scope"):
                adapter.search(
                    query="fixture",
                    limit=5,
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                    index_scope="public-safe",
                )

    def test_external_semantic_timeout_falls_back_to_deterministic_ask(self) -> None:
        adapter = ExternalCommandRetrievalProvider(
            [sys.executable, "-c", "raise SystemExit(0)"],
            name="vault-search-timeout",
            version="fixture",
            timeout_seconds=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            with patch(
                "rkf.providers.subprocess.run",
                side_effect=subprocess.TimeoutExpired(adapter.command, adapter.timeout_seconds),
            ):
                result = search_central_rkf(
                    workspace,
                    "unmatched fixture query",
                    retrieval_provider=adapter,
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["provider"], "vault-search-timeout:fallback")
        self.assertEqual(result["index_generation"], "timeout")

    def test_registered_provider_artifact_matches_the_single_v1_artifact_schema(self) -> None:
        result = FullTextProviderResult(
            status="obtained",
            provider="paper-fetch-smoke",
            provider_version="fixture",
            route="open-access",
            artifact_sha256="a" * 64,
            pdf_magic_validated=True,
            private_artifact_handle="private://fixture",
        )
        with tempfile.TemporaryDirectory() as directory:
            artifact = register_evidence_artifact(
                Workspace(Path(directory)),
                paper_id="papers/doi_fixture",
                result=result,
                origin_project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "evidence_artifact.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(validate_instance(artifact, schema, schema, label="artifact"), [])
        self.assertEqual(artifact["schema"], "rkf-evidence-artifact-v1")
        self.assertEqual(artifact["evidence_id"], artifact["artifact_id"])
        self.assertEqual(artifact["source_id"], "doi_fixture")
        self.assertEqual(artifact["source_ids"], ["doi_fixture"])
        self.assertEqual(artifact["paper_ids"], ["papers/doi_fixture"])
        self.assertNotIn("private_artifact_handle", artifact)

    def test_checksum_dedupe_accumulates_relations_and_returns_the_current_paper(self) -> None:
        class Provider:
            def obtain(self, **_: object) -> FullTextProviderResult:
                return FullTextProviderResult(
                    status="obtained",
                    provider="fixture",
                    provider_version="1",
                    artifact_sha256="b" * 64,
                    pdf_magic_validated=True,
                    private_artifact_handle="private://shared-fixture",
                )

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
                f'project_id = "{PROJECT_ID}"\n'
                "project_name = \"Artifact Relation Test\"\n"
                "marker_schema = \"rkf-connect-v2\"\n"
                "connector_version = \"1.1.0\"\n"
                "connected_at = \"2026-07-15T00:00:00Z\"\n",
                encoding="utf-8",
            )
            workspace = Workspace(root)
            paper_root = workspace.paths.knowledge / "papers"
            paper_root.mkdir(parents=True, exist_ok=True)
            for slug in ("paper_a", "paper_b"):
                (paper_root / f"{slug}.md").write_text(
                    "---\n"
                    "schema: rkf-paper-v1.1\n"
                    "type: paper\n"
                    f"source_id: {slug}\n"
                    "access_state: metadata\n"
                    "review_state: unread\n"
                    "fulltext_status: needs-user-pdf\n"
                    "---\n\n# Fixture Paper\n",
                    encoding="utf-8",
                )
            runtime = RKFActionRuntime(
                workspace=workspace,
                project_root=root,
                full_text_provider=Provider(),
            )
            self.assertEqual(runtime.execute(ActionRequest("rkf.activate")).status, "ok")

            def acquire(slug: str):
                return runtime.execute(
                    ActionRequest(
                        "workflow.add",
                        {
                            "operation": "acquire",
                            "source_id": slug,
                            "identifier": f"10.1234/{slug}",
                            "paper_id": f"papers/{slug}",
                        },
                    )
                )

            first = acquire("paper_a")
            second = acquire("paper_b")
            artifact_files = list((workspace.paths.evidence_index / "artifacts").glob("*.json"))
            persisted = json.loads(artifact_files[0].read_text(encoding="utf-8"))

            self.assertEqual(first.status, "obtained")
            self.assertEqual(second.status, "obtained")
            self.assertEqual(first.payload["artifact"]["artifact_id"], second.payload["artifact"]["artifact_id"])
            self.assertEqual(second.payload["artifact"]["paper_id"], "papers/paper_b")
            self.assertEqual(second.payload["artifact"]["source_id"], "paper_b")
            self.assertEqual(second.payload["artifact"]["paper_ids"], ["papers/paper_a", "papers/paper_b"])
            self.assertEqual(second.payload["artifact"]["source_ids"], ["paper_a", "paper_b"])
            self.assertEqual(second.payload["paper_state"]["paper_id"], "papers/paper_b")
            self.assertEqual(len(artifact_files), 1)
            self.assertEqual(persisted, second.payload["artifact"])
            for slug in ("paper_a", "paper_b"):
                self.assertIn("access_state: fulltext", (paper_root / f"{slug}.md").read_text(encoding="utf-8"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_private_artifact_handle_rejects_root_parent_and_target_symlinks(self) -> None:
        digest = "c" * 64
        artifact_id = "art_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
        result = FullTextProviderResult(
            status="obtained",
            provider="fixture",
            provider_version="1",
            artifact_sha256=digest,
            pdf_magic_validated=True,
            private_artifact_handle="private://must-not-escape",
        )

        for component in ("root", "parent", "target"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as directory:
                workspace = Workspace(Path(directory))
                public_root = workspace.paths.evidence_index
                public_root.mkdir(parents=True, exist_ok=True)
                private_root = workspace.root / ".rkf_private"
                private_parent = private_root / "artifacts"
                private_target = private_parent / f"{artifact_id}.json"
                if component == "root":
                    private_root.symlink_to(public_root, target_is_directory=True)
                    escaped_target = public_root / "artifacts" / f"{artifact_id}.json"
                elif component == "parent":
                    private_root.mkdir()
                    private_parent.symlink_to(public_root, target_is_directory=True)
                    escaped_target = public_root / f"{artifact_id}.json"
                else:
                    private_parent.mkdir(parents=True)
                    escaped_target = public_root / "exposed-private-handle.json"
                    escaped_target.write_text("public sentinel\n", encoding="utf-8")
                    private_target.symlink_to(escaped_target)

                with self.assertRaisesRegex(ValueError, rf"private artifact {component} cannot be a symlink"):
                    register_evidence_artifact(
                        workspace,
                        paper_id="papers/symlink-fixture",
                        result=result,
                        origin_project_id=PROJECT_ID,
                        activation_id=ACTIVATION_ID,
                    )

                if component == "target":
                    self.assertEqual(escaped_target.read_text(encoding="utf-8"), "public sentinel\n")
                else:
                    self.assertFalse(escaped_target.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_public_artifact_rejects_root_parent_and_target_symlinks_on_relation_update(self) -> None:
        result = FullTextProviderResult(
            status="obtained",
            provider="fixture",
            provider_version="1",
            artifact_sha256="d" * 64,
            pdf_magic_validated=True,
        )

        for component in ("root", "parent", "target"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as directory:
                workspace = Workspace(Path(directory))
                first = register_evidence_artifact(
                    workspace,
                    paper_id="papers/first",
                    result=result,
                    origin_project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )
                public_root = workspace.paths.evidence_index
                public_parent = public_root / "artifacts"
                public_target = public_parent / f"{first['artifact_id']}.json"
                outside = workspace.root / f"outside-{component}"
                if component == "root":
                    public_root.replace(outside)
                    public_root.symlink_to(outside, target_is_directory=True)
                    escaped_target = outside / "artifacts" / public_target.name
                elif component == "parent":
                    public_parent.replace(outside)
                    public_parent.symlink_to(outside, target_is_directory=True)
                    escaped_target = outside / public_target.name
                else:
                    outside.parent.mkdir(parents=True, exist_ok=True)
                    public_target.replace(outside)
                    public_target.symlink_to(outside)
                    escaped_target = outside
                before = escaped_target.read_bytes()

                with self.assertRaisesRegex(
                    ValueError,
                    rf"public artifact {component} cannot be a symlink",
                ):
                    register_evidence_artifact(
                        workspace,
                        paper_id="papers/second",
                        result=result,
                        origin_project_id=PROJECT_ID,
                        activation_id=ACTIVATION_ID,
                    )

                self.assertEqual(escaped_target.read_bytes(), before)
                persisted = json.loads(before)
                self.assertEqual(persisted["paper_ids"], ["papers/first"])

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are required")
    def test_private_artifact_handle_uses_and_restores_owner_only_permissions(self) -> None:
        result = FullTextProviderResult(
            status="obtained",
            provider="fixture",
            provider_version="1",
            artifact_sha256="e" * 64,
            pdf_magic_validated=True,
            private_artifact_handle="private://owner-only",
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            artifact = register_evidence_artifact(
                workspace,
                paper_id="papers/permission-fixture",
                result=result,
                origin_project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
            private_root = workspace.root / ".rkf_private"
            private_parent = private_root / "artifacts"
            private_target = private_parent / f"{artifact['artifact_id']}.json"

            self.assertEqual(stat.S_IMODE(private_root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_target.stat().st_mode), 0o600)

            private_root.chmod(0o755)
            private_parent.chmod(0o755)
            private_target.chmod(0o644)
            register_evidence_artifact(
                workspace,
                paper_id="papers/permission-fixture",
                result=result,
                origin_project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )

            self.assertEqual(stat.S_IMODE(private_root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(private_target.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
