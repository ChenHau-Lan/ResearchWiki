from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace, load_toml
from tools import bootstrap_rkf, check_install
from tools import rkf_auto_connect as auto_connect


def tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    snapshot: dict[str, tuple[str, bytes | str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            snapshot[relative] = ("directory", b"")
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


class RKFOnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "ResearchWiki"
        self.repo.mkdir()
        self.skill_source = self.repo / "skills" / "rkf-auto-connect"
        (self.skill_source / "agents").mkdir(parents=True)
        (self.skill_source / "SKILL.md").write_text(
            "---\nname: rkf-auto-connect\ndescription: Test connector skill.\n---\n\n# Test\n",
            encoding="utf-8",
        )
        (self.skill_source / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "RKF Auto-Connect"\n',
            encoding="utf-8",
        )
        self.installed_skill = self.root / "codex-skills" / "rkf-auto-connect"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_relative_storage_paths_resolve_from_checkout_not_process_cwd(self) -> None:
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            'wiki_root = ".rkf_data/wiki"\n'
            'raw_root = ".rkf_data/raw"\n'
            'private_evidence_root = ".rkf_private/evidence"\n',
            encoding="utf-8",
        )
        original_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            workspace = Workspace(self.repo)
        finally:
            os.chdir(original_cwd)

        self.assertEqual(workspace.paths.wiki_root, (self.repo / ".rkf_data/wiki").resolve())
        self.assertEqual(workspace.paths.raw_root, (self.repo / ".rkf_data/raw").resolve())
        self.assertEqual(
            workspace.paths.private_evidence,
            (self.repo / ".rkf_private/evidence").resolve(),
        )

    def test_explicit_workspace_root_takes_precedence_over_rkf_root_environment(self) -> None:
        other = self.root / "OtherWiki"
        other.mkdir()
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            'wiki_root = ".rkf_data/wiki"\n'
            'raw_root = ".rkf_data/raw"\n',
            encoding="utf-8",
        )
        previous = os.environ.get("RKF_ROOT")
        os.environ["RKF_ROOT"] = str(other)
        try:
            workspace = Workspace(self.repo)
        finally:
            if previous is None:
                os.environ.pop("RKF_ROOT", None)
            else:
                os.environ["RKF_ROOT"] = previous

        self.assertEqual(workspace.root, self.repo.resolve())
        self.assertEqual(workspace.paths.wiki_root, (self.repo / ".rkf_data/wiki").resolve())

    def test_bootstrap_preview_is_non_mutating_and_redacted(self) -> None:
        before = tree_snapshot(self.root)

        result = bootstrap_rkf.bootstrap_local(self.repo)

        self.assertEqual(tree_snapshot(self.root), before)
        self.assertEqual(result["mode"], "preview")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["workspace_config"], "would-create")
        rendered = json.dumps(result)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn("machine-", rendered)

    def test_bootstrap_apply_creates_portable_workspace_and_writer_registry(self) -> None:
        connector = self.root / "connector.toml"

        result = bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(result["workspace_config"], "created")
        self.assertEqual(result["connector"], "created")
        self.assertEqual(result["codex_skill"], "created")
        self.assertEqual(
            (self.installed_skill / "SKILL.md").read_bytes(),
            (self.skill_source / "SKILL.md").read_bytes(),
        )
        self.assertEqual(
            (self.installed_skill / "agents" / "openai.yaml").read_bytes(),
            (self.skill_source / "agents" / "openai.yaml").read_bytes(),
        )
        self.assertEqual(
            list(self.installed_skill.parent.glob(".rkf-auto-connect.rkf-stage-*")),
            [],
        )
        config = (self.repo / "rkf.workspace.toml").read_text(encoding="utf-8")
        self.assertIn('wiki_root = ".rkf_data/wiki"', config)
        self.assertNotIn(str(self.root), config)
        workspace = Workspace(self.repo)
        registry = json.loads(
            (workspace.paths.sync_state / "maintenance-writer.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(registry["schema"], "rkf-writer-registry-v1")
        self.assertRegex(registry["machine_id"], r"^machine-[a-f0-9]{8}$")
        self.assertTrue(workspace.paths.raw_root.is_dir())
        self.assertTrue(workspace.paths.private_evidence.is_dir())
        rendered = json.dumps(result)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn(registry["machine_id"], rendered)

    def test_clean_bootstrap_can_preview_discovery_with_an_explicit_query(self) -> None:
        bootstrap_rkf.bootstrap_local(self.repo, apply=True)
        workspace = Workspace(self.repo)
        runtime = RKFActionRuntime(workspace=workspace, project_root=self.repo)

        activated = runtime.execute(ActionRequest(action="rkf.activate"))
        preview = runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={
                    "query": "aerosol ice-phase cloud observations",
                    "providers": ["paper-radar"],
                    "paper_radar_records": [
                        {
                            "id": "clean-install-fixture",
                            "title": "Clean Install Discovery Candidate",
                            "authors": ["Public Researcher"],
                            "year": 2026,
                            "doi": "10.1234/clean-install-discovery",
                            "url": "https://doi.org/10.1234/clean-install-discovery",
                        }
                    ],
                },
            )
        )

        self.assertEqual(activated.status, "ok")
        self.assertEqual(preview.status, "ok")
        self.assertEqual(preview.payload["candidate_count"], 1)
        self.assertEqual(list(workspace.paths.search_runs.iterdir()), [])

    def test_bootstrap_preserves_existing_workspace_and_connector(self) -> None:
        (self.repo / "rkf.workspace.toml").write_text("custom = true\n", encoding="utf-8")
        connector = self.root / "connector.toml"
        connector.write_text("custom connector\n", encoding="utf-8")

        result = bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(result["workspace_config"], "existing")
        self.assertEqual(result["connector"], "existing")
        self.assertEqual(result["status"], "existing-unverified")
        self.assertEqual(result["storage"], "existing-unverified")
        self.assertEqual(result["writer_registry"], "existing-unverified")
        self.assertEqual(
            (self.repo / "rkf.workspace.toml").read_text(encoding="utf-8"),
            "custom = true\n",
        )
        self.assertEqual(connector.read_text(encoding="utf-8"), "custom connector\n")

    def test_bootstrap_reports_existing_connector_as_unverified_before_new_workspace_apply(self) -> None:
        connector = self.root / "connector.toml"
        connector.write_text("user-owned connector\n", encoding="utf-8")

        preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        result = bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(preview["status"], "existing-unverified")
        self.assertEqual(result["status"], "existing-unverified")
        self.assertEqual(connector.read_text(encoding="utf-8"), "user-owned connector\n")

    def test_bootstrap_blocks_partial_manifest_and_reports_exact_stale_bundle(self) -> None:
        self.installed_skill.mkdir(parents=True)
        (self.installed_skill / "SKILL.md").write_bytes(
            (self.skill_source / "SKILL.md").read_bytes()
        )

        partial = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=self.root / "connector.toml",
            codex_skill_dir=self.installed_skill,
        )
        (self.installed_skill / "agents").mkdir()
        (self.installed_skill / "agents" / "openai.yaml").write_text(
            "stale interface\n", encoding="utf-8"
        )
        stale = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=self.root / "connector.toml",
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(partial["codex_skill"], "blocked")
        self.assertEqual(partial["status"], "blocked")
        self.assertIn(
            "CODEX_SKILL_TARGET_MANIFEST_INVALID",
            partial["blocker_codes"],
        )
        self.assertEqual(stale["codex_skill"], "existing-unverified")
        self.assertEqual(stale["status"], "existing-unverified")

    def test_bootstrap_blocks_invalid_integration_parent_before_any_write(self) -> None:
        invalid_parent = self.root / "not-a-directory"
        invalid_parent.write_text("owned\n", encoding="utf-8")
        connector = invalid_parent / "connector.toml"
        before = tree_snapshot(self.root)

        preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(preview["status"], "blocked")
        self.assertIn("CONNECTOR_PARENT_INVALID", preview["blocker_codes"])
        with self.assertRaises(SystemExit):
            bootstrap_rkf.bootstrap_local(
                self.repo,
                apply=True,
                install_connector=True,
                connector_path=connector,
                codex_skill_dir=self.installed_skill,
            )
        self.assertEqual(tree_snapshot(self.root), before)

    def test_bootstrap_blocks_non_file_workspace_or_connector_target_before_any_write(self) -> None:
        connector = self.root / "connector-target"
        connector.mkdir()
        before_connector = tree_snapshot(self.root)

        connector_preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(connector_preview["status"], "blocked")
        self.assertIn("CONNECTOR_TARGET_INVALID", connector_preview["blocker_codes"])
        with self.assertRaises(SystemExit):
            bootstrap_rkf.bootstrap_local(
                self.repo,
                apply=True,
                install_connector=True,
                connector_path=connector,
                codex_skill_dir=self.installed_skill,
            )
        self.assertEqual(tree_snapshot(self.root), before_connector)

        workspace = self.repo / "rkf.workspace.toml"
        workspace.mkdir()
        before_workspace = tree_snapshot(self.root)
        workspace_preview = bootstrap_rkf.bootstrap_local(self.repo)

        self.assertEqual(workspace_preview["status"], "blocked")
        self.assertIn("WORKSPACE_CONFIG_INVALID", workspace_preview["blocker_codes"])
        with self.assertRaises(SystemExit):
            bootstrap_rkf.bootstrap_local(self.repo, apply=True)
        self.assertEqual(tree_snapshot(self.root), before_workspace)

    def test_bootstrap_refuses_nonempty_existing_storage_before_writing_config(self) -> None:
        existing_wiki = self.root / "existing-wiki"
        registry = existing_wiki / "state" / "sync" / "maintenance-writer.json"
        registry.parent.mkdir(parents=True)
        registry.write_text("user-owned registry\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            bootstrap_rkf.bootstrap_local(
                self.repo,
                apply=True,
                wiki_root=str(existing_wiki),
            )

        self.assertFalse((self.repo / "rkf.workspace.toml").exists())
        self.assertEqual(registry.read_text(encoding="utf-8"), "user-owned registry\n")

    def test_bootstrap_preview_and_apply_reject_overlapping_storage_roots(self) -> None:
        before = tree_snapshot(self.root)

        preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            wiki_root=".rkf_data",
            raw_root=".rkf_data/raw",
        )

        self.assertEqual(preview["status"], "blocked")
        self.assertIn("STORAGE_ROOT_OVERLAP", preview["blocker_codes"])
        self.assertEqual(tree_snapshot(self.root), before)
        with self.assertRaises(SystemExit):
            bootstrap_rkf.bootstrap_local(
                self.repo,
                apply=True,
                wiki_root=".rkf_data",
                raw_root=".rkf_data/raw",
            )
        self.assertEqual(tree_snapshot(self.root), before)

    def test_bootstrap_rejects_storage_symlink_and_relative_parent_traversal(self) -> None:
        outside = self.root / "outside-wiki"
        outside.mkdir()
        link = self.repo / "wiki-link"
        link.symlink_to(outside, target_is_directory=True)
        before = tree_snapshot(self.root)

        symlink_preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            wiki_root="wiki-link",
            raw_root=".local/raw",
            private_evidence_root=".private/evidence",
        )
        traversal_preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            wiki_root="../sibling-wiki",
            raw_root=".local/raw",
            private_evidence_root=".private/evidence",
        )

        self.assertEqual(symlink_preview["status"], "blocked")
        self.assertIn("STORAGE_TARGET_SYMLINK", symlink_preview["blocker_codes"])
        self.assertEqual(traversal_preview["status"], "blocked")
        self.assertIn(
            "STORAGE_RELATIVE_TRAVERSAL",
            traversal_preview["blocker_codes"],
        )
        for wiki_root in ("wiki-link", "../sibling-wiki"):
            with self.assertRaises(SystemExit):
                bootstrap_rkf.bootstrap_local(
                    self.repo,
                    apply=True,
                    wiki_root=wiki_root,
                    raw_root=".local/raw",
                    private_evidence_root=".private/evidence",
                )
        self.assertEqual(tree_snapshot(self.root), before)
        self.assertFalse((self.root / "sibling-wiki").exists())

    def test_bootstrap_allows_explicit_absolute_external_storage(self) -> None:
        wiki = self.root / "external" / "wiki"
        raw = self.root / "external" / "raw"
        private = self.root / "external" / "private"

        preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            wiki_root=str(wiki),
            raw_root=str(raw),
            private_evidence_root=str(private),
        )
        result = bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            wiki_root=str(wiki),
            raw_root=str(raw),
            private_evidence_root=str(private),
        )

        self.assertEqual(preview["status"], "ready")
        self.assertEqual(result["status"], "configured")
        self.assertTrue((wiki / "state" / "sync" / "maintenance-writer.json").is_file())
        self.assertTrue(raw.is_dir())
        self.assertTrue(private.is_dir())

    def test_bootstrap_preflight_rejects_nonwritable_storage_and_skill_parents(self) -> None:
        readonly_storage = self.root / "readonly-storage"
        readonly_storage.mkdir()
        readonly_storage.chmod(0o555)
        try:
            storage_preview = bootstrap_rkf.bootstrap_local(
                self.repo,
                wiki_root=str(readonly_storage / "wiki"),
                raw_root=".local/raw",
                private_evidence_root=".private/evidence",
            )
            self.assertEqual(storage_preview["status"], "blocked")
            self.assertIn("STORAGE_PARENT_INVALID", storage_preview["blocker_codes"])
            with self.assertRaises(SystemExit):
                bootstrap_rkf.bootstrap_local(
                    self.repo,
                    apply=True,
                    wiki_root=str(readonly_storage / "wiki"),
                    raw_root=".local/raw",
                    private_evidence_root=".private/evidence",
                )
        finally:
            readonly_storage.chmod(0o755)

        readonly_skill = self.root / "readonly-skill"
        readonly_skill.mkdir()
        readonly_skill.chmod(0o555)
        try:
            skill_preview = bootstrap_rkf.bootstrap_local(
                self.repo,
                install_connector=True,
                connector_path=self.root / "connector.toml",
                codex_skill_dir=readonly_skill / "rkf-auto-connect",
            )
            self.assertEqual(skill_preview["status"], "blocked")
            self.assertIn("CODEX_SKILL_PARENT_INVALID", skill_preview["blocker_codes"])
        finally:
            readonly_skill.chmod(0o755)

        readonly_connector = self.root / "readonly-connector"
        readonly_connector.mkdir()
        readonly_connector.chmod(0o555)
        try:
            connector_preview = bootstrap_rkf.bootstrap_local(
                self.repo,
                install_connector=True,
                connector_path=readonly_connector / "connector.toml",
                codex_skill_dir=self.installed_skill,
            )
            self.assertEqual(connector_preview["status"], "blocked")
            self.assertIn(
                "CONNECTOR_PARENT_INVALID",
                connector_preview["blocker_codes"],
            )
        finally:
            readonly_connector.chmod(0o755)
        self.assertFalse((self.repo / "rkf.workspace.toml").exists())

    def test_bootstrap_apply_rolls_back_workspace_after_injected_storage_failure(self) -> None:
        before = tree_snapshot(self.root)
        original = bootstrap_rkf._mkdir_tracked
        call_count = 0

        def fail_after_config(path: Path, created_dirs: list[Path]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise OSError("injected storage failure")
            original(path, created_dirs)

        with mock.patch.object(
            bootstrap_rkf,
            "_mkdir_tracked",
            side_effect=fail_after_config,
        ):
            with self.assertRaisesRegex(SystemExit, "rolled back"):
                bootstrap_rkf.bootstrap_local(self.repo, apply=True)

        self.assertEqual(tree_snapshot(self.root), before)
        self.assertFalse((self.repo / "rkf.workspace.toml").exists())

    def test_bootstrap_apply_rolls_back_skill_and_workspace_when_connector_fails(self) -> None:
        connector = self.root / "connector.toml"
        before = tree_snapshot(self.root)
        original = bootstrap_rkf._write_new_text

        def fail_connector(
            path: Path,
            text: str,
            *,
            created_dirs: list[Path] | None = None,
        ) -> bytes:
            if path == connector:
                raise OSError("injected connector failure")
            return original(path, text, created_dirs=created_dirs)

        with mock.patch.object(
            bootstrap_rkf,
            "_write_new_text",
            side_effect=fail_connector,
        ):
            with self.assertRaisesRegex(SystemExit, "rolled back"):
                bootstrap_rkf.bootstrap_local(
                    self.repo,
                    apply=True,
                    install_connector=True,
                    connector_path=connector,
                    codex_skill_dir=self.installed_skill,
                )

        self.assertEqual(tree_snapshot(self.root), before)
        self.assertFalse(connector.exists())
        self.assertFalse(self.installed_skill.exists())
        self.assertEqual(
            list(self.installed_skill.parent.glob(".rkf-auto-connect.rkf-stage-*")),
            [],
        )

    def test_staged_skill_install_removes_partial_stage_on_write_failure(self) -> None:
        target = self.root / "staged-skills" / "rkf-auto-connect"

        with mock.patch.object(
            bootstrap_rkf.os,
            "fsync",
            side_effect=OSError("injected staged write failure"),
        ):
            with self.assertRaises(OSError):
                bootstrap_rkf._install_skill_bundle(self.skill_source, target)

        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())

    def test_bootstrap_never_creates_connector_before_skill_install_succeeds(self) -> None:
        connector = self.root / "connector.toml"
        before = tree_snapshot(self.root)

        with mock.patch.object(
            bootstrap_rkf,
            "_install_skill_bundle",
            side_effect=OSError("injected skill failure"),
        ):
            with self.assertRaisesRegex(SystemExit, "rolled back"):
                bootstrap_rkf.bootstrap_local(
                    self.repo,
                    apply=True,
                    install_connector=True,
                    connector_path=connector,
                    codex_skill_dir=self.installed_skill,
                )

        self.assertFalse(connector.exists())
        self.assertEqual(tree_snapshot(self.root), before)

    def test_bootstrap_toml_escapes_untrusted_path_strings(self) -> None:
        injected = 'wiki"\n[machine]\nid = "attacker'
        rendered = bootstrap_rkf.render_workspace_config(
            machine_id="machine-safe",
            wiki_root=injected,
        )
        config = self.repo / "escaped.toml"
        config.write_text(rendered, encoding="utf-8")

        parsed = load_toml(config)

        self.assertEqual(parsed["storage"]["wiki_root"], injected)
        self.assertEqual(parsed["machine"]["id"], "machine-safe")

    def test_bootstrap_expands_environment_before_nonempty_storage_preflight(self) -> None:
        existing_wiki = self.root / "environment-wiki"
        registry = existing_wiki / "state" / "sync" / "maintenance-writer.json"
        registry.parent.mkdir(parents=True)
        registry.write_text("user-owned registry\n", encoding="utf-8")
        previous = os.environ.get("TEST_RKF_WIKI")
        os.environ["TEST_RKF_WIKI"] = str(existing_wiki)
        try:
            preview = bootstrap_rkf.bootstrap_local(
                self.repo,
                wiki_root="$TEST_RKF_WIKI",
            )
            with self.assertRaises(SystemExit):
                bootstrap_rkf.bootstrap_local(
                    self.repo,
                    apply=True,
                    wiki_root="$TEST_RKF_WIKI",
                )
        finally:
            if previous is None:
                os.environ.pop("TEST_RKF_WIKI", None)
            else:
                os.environ["TEST_RKF_WIKI"] = previous

        self.assertIn("STORAGE_TARGET_NOT_EMPTY", preview["blocker_codes"])
        self.assertFalse((self.repo / "rkf.workspace.toml").exists())
        self.assertEqual(registry.read_text(encoding="utf-8"), "user-owned registry\n")

    def test_bootstrap_requires_exact_no_symlink_skill_manifests(self) -> None:
        shutil.copytree(self.skill_source, self.installed_skill)
        (self.installed_skill / "stale-extra.py").write_text(
            "stale\n", encoding="utf-8"
        )

        extra_preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=self.root / "connector.toml",
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(extra_preview["status"], "blocked")
        self.assertIn(
            "CODEX_SKILL_TARGET_MANIFEST_INVALID",
            extra_preview["blocker_codes"],
        )

        source_agents = self.skill_source / "agents"
        outside_agents = self.root / "outside-agents"
        source_agents.rename(outside_agents)
        source_agents.symlink_to(outside_agents, target_is_directory=True)
        source_preview = bootstrap_rkf.bootstrap_local(
            self.repo,
            install_connector=True,
            connector_path=self.root / "connector.toml",
            codex_skill_dir=self.root / "different-skill-target",
        )

        self.assertEqual(source_preview["status"], "blocked")
        self.assertIn("CODEX_SKILL_SOURCE_INVALID", source_preview["blocker_codes"])

    def test_install_diagnostic_rejects_extra_skill_files_and_invalid_policy(self) -> None:
        connector = self.root / "connector.toml"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        for relative in ("AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"):
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
        (self.installed_skill / "stale-extra.py").write_text(
            "stale\n", encoding="utf-8"
        )

        extra_result = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        extra_checks = {item["name"]: item for item in extra_result["checks"]}
        self.assertEqual(extra_checks["codex_auto_connect_skill"]["status"], "fail")

        (self.installed_skill / "stale-extra.py").unlink()
        connector.write_text(
            bootstrap_rkf.render_connector_config(self.repo).replace(
                'mode = "active-aggressive"', 'mode = "invalid-mode"'
            ),
            encoding="utf-8",
        )
        policy_result = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        policy_checks = {item["name"]: item for item in policy_result["checks"]}
        self.assertEqual(policy_checks["cross_project_connector"]["status"], "fail")

    def test_install_diagnostic_redacts_runtime_path_resolution_failures(self) -> None:
        loop = self.root / "private-loop"
        loop.symlink_to(loop)
        (self.repo / "rkf.workspace.toml").write_text(
            f'[storage]\nwiki_root = "{loop.as_posix()}"\n',
            encoding="utf-8",
        )

        result = check_install.inspect_install(
            self.repo,
            connector_path=self.root / "missing-connector.toml",
            codex_skill_dir=self.root / "missing-skill",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = check_install.main(
                [
                    "--repo-root",
                    str(self.repo),
                    "--connector-path",
                    str(self.root / "missing-connector.toml"),
                    "--codex-skill-dir",
                    str(self.root / "missing-skill"),
                    "--json",
                    "--strict",
                ]
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(status, 1)
        self.assertTrue(result["paths_redacted"])
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn(str(self.root), stdout.getvalue())

    def test_install_diagnostic_is_read_only_and_path_redacted(self) -> None:
        connector = self.root / "connector.toml"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        for relative in ("AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"):
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
        (self.repo / "site").mkdir()
        (self.repo / "site/index.html").write_text("<!doctype html>\n", encoding="utf-8")
        before = tree_snapshot(self.root)

        result = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        self.assertEqual(tree_snapshot(self.root), before)
        self.assertEqual(result["status"], "ready")
        rendered = json.dumps(result)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn("machine-", rendered)

    def test_install_diagnostic_blocks_stale_auto_connect_skill_when_connector_is_present(self) -> None:
        connector = self.root / "connector.toml"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        (self.installed_skill / "SKILL.md").write_text("stale skill\n", encoding="utf-8")
        for relative in ("AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"):
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")

        result = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(checks["codex_auto_connect_skill"]["status"], "fail")
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_install_diagnostic_blocks_missing_or_stale_skill_interface(self) -> None:
        connector = self.root / "connector.toml"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        interface = self.installed_skill / "agents" / "openai.yaml"
        interface.unlink()
        missing = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )
        interface.write_text("stale interface\n", encoding="utf-8")
        stale = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=self.installed_skill,
        )

        for result in (missing, stale):
            checks = {item["name"]: item for item in result["checks"]}
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(checks["codex_auto_connect_skill"]["status"], "fail")
            self.assertNotIn(str(self.root), json.dumps(result))

    def test_install_diagnostic_rejects_symlinked_connector_and_workspace(self) -> None:
        connector_target = self.root / "connector-target.toml"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector_target,
            codex_skill_dir=self.installed_skill,
        )
        connector_link = self.root / "connector-link.toml"
        connector_link.symlink_to(connector_target)
        workspace_target = self.root / "workspace-target.toml"
        workspace = self.repo / "rkf.workspace.toml"
        workspace.replace(workspace_target)
        workspace.symlink_to(workspace_target)

        result = check_install.inspect_install(
            self.repo,
            connector_path=connector_link,
            codex_skill_dir=self.installed_skill,
        )

        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(checks["cross_project_connector"]["status"], "fail")
        self.assertEqual(checks["workspace_config"]["status"], "fail")
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_install_diagnostic_handles_malformed_workspace_and_connector_without_paths(self) -> None:
        (self.repo / "rkf.workspace.toml").write_text('[storage\nroot = "broken"\n', encoding="utf-8")
        connector = self.root / "connector.toml"
        connector.write_text('[researchwiki\nroot = "broken"\n', encoding="utf-8")

        result = check_install.inspect_install(self.repo, connector_path=connector)

        self.assertEqual(result["status"], "blocked")
        rendered = json.dumps(result)
        self.assertNotIn(str(self.root), rendered)
        self.assertIn("unreadable or invalid", rendered)

    def test_install_diagnostic_rejects_file_storage_handles(self) -> None:
        wiki = self.root / "wiki-file"
        raw = self.root / "raw-file"
        private = self.root / "private-file"
        for path in (wiki, raw, private):
            path.write_text("not a directory\n", encoding="utf-8")
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{wiki.as_posix()}"\n'
            f'raw_root = "{raw.as_posix()}"\n'
            f'private_evidence_root = "{private.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-files"\n'
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )

        result = check_install.inspect_install(
            self.repo,
            connector_path=self.root / "missing-connector.toml",
        )

        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(checks["storage_handles"]["status"], "fail")
        self.assertEqual(checks["connection_doctor"]["status"], "fail")
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_connect_project_preview_is_non_mutating_and_apply_preserves_notes(self) -> None:
        project = self.root / "ResearchProject"
        bridge = project / "RKF"
        bridge.mkdir(parents=True)
        memory = bridge / "memory.md"
        memory.write_text("user-owned memory\n", encoding="utf-8")
        before = tree_snapshot(project)

        preview = auto_connect.preview_project_connection(project)

        self.assertEqual(tree_snapshot(project), before)
        self.assertTrue(preview["marker"]["would_change"])
        self.assertFalse(preview["bridge"]["would_overwrite"])
        self.assertNotIn(str(project), json.dumps(preview))

        result = auto_connect.connect_project(project, project_name="ResearchProject")

        self.assertEqual(result["status"], "connected")
        self.assertEqual(memory.read_text(encoding="utf-8"), "user-owned memory\n")
        self.assertTrue((project / ".rkf-connect.toml").exists())
        self.assertTrue((bridge / "README.md").exists())
        self.assertNotIn(str(project), json.dumps(result))


if __name__ == "__main__":
    unittest.main()
