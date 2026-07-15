from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tools import rkf_auto_connect as auto


REPO = Path(__file__).resolve().parents[1]


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


class RKFAutoConnectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.researchwiki = self.root / "ResearchWiki"
        self.researchwiki.mkdir()
        (self.researchwiki / "rkf.workspace.toml").write_text(
            f"[storage]\nwiki_root = \"{self.researchwiki.as_posix()}\"\n",
            encoding="utf-8",
        )
        self.config = self.root / "rkf_connector.toml"
        self.old_env = os.environ.copy()
        os.environ["RKF_CONNECTOR_CONFIG"] = str(self.config)
        self.config.write_text(
            "[researchwiki]\n"
            f"root = \"{self.researchwiki.as_posix()}\"\n\n"
            "[policy]\n"
            "mode = \"active-aggressive\"\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        self.tmp.cleanup()

    def test_load_config_resolves_researchwiki_root(self) -> None:
        config = auto.load_connector_config()

        self.assertEqual(config.researchwiki_root, self.researchwiki.resolve())
        self.assertEqual(config.mode, "active-aggressive")

    def test_resolve_command_masks_private_paths(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(["resolve"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["researchwiki"], "configured")
        self.assertTrue(payload["workspace_config"])
        self.assertNotIn(str(self.researchwiki), stdout.getvalue())

    def test_classify_active_doi_source_material(self) -> None:
        decision = auto.classify_capture(
            text="Find papers related to DOI 10.1234/example and summarize the source.",
            source_url="",
            project_name="AnyProject",
        )

        self.assertEqual(decision.level, "active")
        self.assertIn("doi", decision.reasons)
        self.assertIn("inbox", decision.targets)
        self.assertIn("hot", decision.targets)

    def test_classify_aggressive_research_discussion_without_doi(self) -> None:
        decision = auto.classify_capture(
            text="This WRF microphysics calibration idea may change the experiment design and manuscript argument.",
            source_url="",
            project_name="QUACS",
        )

        self.assertEqual(decision.level, "aggressive")
        self.assertIn("research-discussion", decision.reasons)
        self.assertIn("inbox", decision.targets)

    def test_classify_ordinary_coding_debug_as_none(self) -> None:
        decision = auto.classify_capture(
            text="Fix this CSS padding issue in the dashboard button.",
            source_url="",
            project_name="WebApp",
        )

        self.assertEqual(decision.level, "none")
        self.assertEqual(decision.targets, [])

    def test_helper_script_runs_from_an_external_project_cwd(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "rkf_auto_connect.py"),
                "classify",
                "Find papers related to DOI 10.1234/example.",
            ],
            cwd=self.root,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"level": "active"', result.stdout)

    def test_block_private_paths_and_long_transcripts(self) -> None:
        private_path = "/" + "Users/example/private.txt"
        private_decision = auto.classify_capture(
            text=f"Read {private_path} and save it.",
            source_url="",
            project_name="AnyProject",
        )
        long_decision = auto.classify_capture(
            text="chat transcript\n" * 900,
            source_url="",
            project_name="AnyProject",
        )

        self.assertEqual(private_decision.level, "blocked")
        self.assertIn("private-path", private_decision.reasons)
        self.assertEqual(long_decision.level, "blocked")
        self.assertIn("too-long", long_decision.reasons)

    def test_load_config_does_not_require_legacy_cli(self) -> None:
        config = auto.load_connector_config()

        self.assertEqual(config.researchwiki_root, self.researchwiki.resolve())
        self.assertFalse((self.researchwiki / "tools" / "rk.py").exists())

    def test_build_requests_use_only_control_query_and_capture_actions(self) -> None:
        config = auto.load_connector_config()
        activate = auto.build_activate_request(config=config)
        query = auto.build_query_request(config=config, query="cloud papers")
        capture = auto.build_capture_request(
            config=config,
            title="Cloud paper lead",
            text="Find DOI 10.1234/cloud.lead",
            origin="project:QUACS",
            doi="10.1234/cloud.lead",
            intent="paper-search",
        )

        self.assertEqual(activate.action, "rkf.activate")
        self.assertEqual(query.action, "workflow.ask")
        self.assertEqual(capture.action, "workflow.add")
        self.assertEqual(capture.params["doi"], "10.1234/cloud.lead")
        self.assertNotIn("/" + "Users/", repr(capture.params))

    def test_execute_action_request_is_blocked_without_shared_runtime(self) -> None:
        config = auto.load_connector_config()
        request = auto.build_capture_request(
            config=config,
            title="Blocked lead",
            text="Find DOI 10.1234/blocked",
            origin="project:Demo",
            doi="10.1234/blocked",
            intent="paper-search",
        )

        before = sorted(
            path.relative_to(self.researchwiki)
            for path in self.researchwiki.rglob("*")
            if path.is_file()
        )

        result = auto.execute_action_request(config=config, request=request)

        after = sorted(
            path.relative_to(self.researchwiki)
            for path in self.researchwiki.rglob("*")
            if path.is_file()
        )
        self.assertEqual(after, before)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_NOT_ACTIVE")

    def test_connected_project_reuses_one_runtime_for_app_actions(self) -> None:
        raw = self.root / "raw"
        raw.mkdir()
        (self.researchwiki / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.researchwiki.as_posix()}"\n'
            f'raw_root = "{raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-connected-e2e"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        registry = self.researchwiki / "state" / "sync" / "maintenance-writer.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            '{"schema":"rkf-writer-registry-v1",'
            '"machine_id":"machine-connected-e2e",'
            '"assigned_at":"2026-07-13T12:00:00Z"}\n',
            encoding="utf-8",
        )
        project = self.root / "ExternalResearchProject"
        project.mkdir()
        connected = auto.connect_project(
            project,
            project_name="External Research Project",
        )
        config = auto.load_connector_config()
        runtime = auto.open_action_runtime(config=config, project_root=project)

        activated = auto.execute_action_request(
            config=config,
            request=auto.build_activate_request(config=config),
            runtime=runtime,
        )
        queried = auto.execute_action_request(
            config=config,
            request=auto.build_query_request(config=config, query="cloud evidence"),
            runtime=runtime,
        )
        validated = auto.execute_action_request(
            config=config,
            request=auto.ActionRequest(action="connect.validate"),
            runtime=runtime,
        )
        review = auto.execute_action_request(
            config=config,
            request=auto.ActionRequest(action="workflow.review"),
            runtime=runtime,
        )

        self.assertEqual(connected["status"], "connected")
        self.assertEqual(activated.status, "ok")
        self.assertEqual(queried.status, "ok")
        self.assertEqual(validated.status, "ok")
        self.assertEqual(validated.payload["status"], "connected")
        self.assertEqual(review.status, "ok")
        self.assertEqual(runtime.project_root, project.resolve())

    def test_action_runtime_refuses_an_unconnected_external_project(self) -> None:
        project = self.root / "UnconnectedProject"
        project.mkdir()
        config = auto.load_connector_config()

        with self.assertRaisesRegex(SystemExit, "not connected or available"):
            auto.open_action_runtime(config=config, project_root=project)

    def test_write_project_marker_uses_v2_manual_activation(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")
        policy = auto.read_project_marker(project)

        self.assertEqual(marker, project.resolve() / ".rkf-connect.toml")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("version = 2", text)
        self.assertIn("available = true", text)
        self.assertIn('activation = "manual"', text)
        self.assertNotIn("enabled = true", text)
        self.assertTrue(policy["available"])
        self.assertEqual(policy["activation"], "manual")
        self.assertNotIn(str(self.researchwiki), text)

    def test_bridge_rejects_project_name_markup_injection(self) -> None:
        project = self.root / "UnsafeNameProject"
        project.mkdir()

        with self.assertRaisesRegex(SystemExit, "project name"):
            auto.write_bridge_folder(project, project_name="unsafe`\n# injected")

        self.assertFalse((project / "RKF" / "README.md").exists())

    def test_v1_marker_upgrade_requires_preview_and_explicit_apply(self) -> None:
        project = self.root / "LegacyProject"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = '[rkf_auto_connect]\nenabled = true\nmode = "active-aggressive"\n'
        marker.write_text(original, encoding="utf-8")

        preview = auto.preview_project_marker(project, mode="active-aggressive")

        self.assertTrue(preview["would_change"])
        self.assertEqual(preview["from_version"], 1)
        self.assertEqual(marker.read_text(encoding="utf-8"), original)
        with self.assertRaises(SystemExit):
            auto.write_project_marker(project, mode="active-aggressive")
        with self.assertRaises(SystemExit):
            auto.connect_project(project, mode="active-aggressive")
        self.assertFalse((project / "RKF").exists())
        auto.write_project_marker(
            project,
            mode="active-aggressive",
            approve_upgrade=True,
        )
        self.assertIn("version = 2", marker.read_text(encoding="utf-8"))

    def test_future_marker_version_is_refused_and_preserved(self) -> None:
        project = self.root / "FutureProject"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = 'version = 3\n\n[rkf]\navailable = true\n'
        marker.write_text(original, encoding="utf-8")

        with self.assertRaises(SystemExit):
            auto.preview_project_connection(project)
        with self.assertRaises(SystemExit):
            auto.connect_project(project)

        self.assertEqual(marker.read_text(encoding="utf-8"), original)
        self.assertFalse((project / "RKF").exists())

    def test_non_integer_and_unsupported_marker_versions_are_refused(self) -> None:
        for index, raw_version in enumerate(('2.9', '"2"', "true", "0", "-1")):
            project = self.root / f"InvalidVersion{index}"
            project.mkdir()
            marker = project / ".rkf-connect.toml"
            original = (
                f"version = {raw_version}\n\n"
                "[rkf]\n"
                "available = true\n"
                'activation = "manual"\n'
                "query_first = true\n"
                'capture_mode = "active-aggressive"\n'
            )
            marker.write_text(original, encoding="utf-8")

            with self.assertRaises(SystemExit):
                auto.preview_project_connection(project)
            with self.assertRaises(SystemExit):
                auto.connect_project(project)

            self.assertEqual(marker.read_text(encoding="utf-8"), original)
            self.assertFalse((project / "RKF").exists())

    def test_v1_atomic_upgrade_preserves_original_when_replace_fails(self) -> None:
        project = self.root / "AtomicUpgrade"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = '[rkf_auto_connect]\nenabled = true\nmode = "active"\n'
        marker.write_text(original, encoding="utf-8")

        with mock.patch.object(auto.os, "replace", side_effect=OSError("injected")):
            with self.assertRaisesRegex(SystemExit, "without a partial"):
                auto.write_project_marker(
                    project,
                    mode="active-aggressive",
                    approve_upgrade=True,
                )

        self.assertEqual(marker.read_text(encoding="utf-8"), original)
        self.assertEqual(list(project.glob(".rkf-connect.*.tmp")), [])

    def test_connect_project_rolls_back_bridge_and_preserves_v1_on_upgrade_failure(self) -> None:
        project = self.root / "AtomicConnectionUpgrade"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = '[rkf_auto_connect]\nenabled = true\nmode = "active"\n'
        marker.write_text(original, encoding="utf-8")

        with mock.patch.object(auto.os, "replace", side_effect=OSError("injected")):
            with self.assertRaisesRegex(SystemExit, "without a partial"):
                auto.connect_project(
                    project,
                    mode="active-aggressive",
                    approve_upgrade=True,
                    project_name="AtomicConnectionUpgrade",
                )

        self.assertEqual(marker.read_text(encoding="utf-8"), original)
        self.assertFalse((project / "RKF").exists())
        self.assertEqual(list(project.glob(".rkf-connect.*.tmp")), [])

    def test_legacy_v2_marker_without_project_id_requires_manual_upgrade(self) -> None:
        project = self.root / "CommentedProject"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = (
            "# user-owned comment\n"
            "version = 2\n\n"
            "[rkf]\n"
            "available = true\n"
            'activation = "manual"\n'
            "query_first = true\n"
            'capture_mode = "active-aggressive"\n'
            'project_hint = "keep-me"\n'
        )
        marker.write_text(original, encoding="utf-8")

        preview = auto.preview_project_connection(project)
        with self.assertRaises(SystemExit):
            auto.connect_project(project)

        self.assertTrue(preview["marker"]["would_change"])
        self.assertTrue(preview["marker"]["requires_manual_edit"])
        self.assertEqual(marker.read_text(encoding="utf-8"), original)

    def test_existing_v2_policy_change_requires_manual_edit(self) -> None:
        project = self.root / "PolicyProject"
        project.mkdir()
        marker = auto.write_project_marker(project, mode="active")
        original = marker.read_bytes()

        preview = auto.preview_project_connection(project, mode="active-aggressive")
        with self.assertRaises(SystemExit):
            auto.connect_project(project, mode="active-aggressive")

        self.assertTrue(preview["marker"]["requires_manual_edit"])
        self.assertEqual(marker.read_bytes(), original)
        self.assertFalse((project / "RKF").exists())

    def test_invalid_mode_is_rejected_before_marker_or_bridge_write(self) -> None:
        project = self.root / "ModeProject"
        project.mkdir()

        with self.assertRaises(SystemExit):
            auto.preview_project_connection(project, mode='active"\nsecret = "x')
        with self.assertRaises(SystemExit):
            auto.connect_project(project, mode="unsupported")

        self.assertEqual(list(project.iterdir()), [])

    def test_write_bridge_folder_creates_project_local_index_files(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        result = auto.write_bridge_folder(project, mode="active-aggressive", project_name="SomeProject")

        self.assertEqual(result.root, project.resolve() / "RKF")
        resolved_project = project.resolve()
        expected_files = {
            resolved_project / "RKF" / "README.md",
            resolved_project / "RKF" / "hot.md",
            resolved_project / "RKF" / "memory.md",
            resolved_project / "RKF" / "captures.md",
        }
        self.assertEqual(set(result.created), expected_files)
        for path in expected_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("project-local", text)
            self.assertIn("not stable evidence", text)
            self.assertNotIn(str(self.researchwiki), text)
            self.assertNotIn("rk hot record", text)
            self.assertNotIn("tools/rk.py", text)
        readme = (project / "RKF" / "README.md").read_text(encoding="utf-8")
        hot = (project / "RKF" / "hot.md").read_text(encoding="utf-8")
        self.assertIn("starts with RKF OFF", readme)
        self.assertIn("workflow.ask", readme)
        self.assertIn("workflow.add", hot)
        self.assertNotIn("query.search", readme)
        self.assertNotIn("capture.route", hot)

    def test_write_bridge_folder_preserves_existing_files(self) -> None:
        project = self.root / "SomeProject"
        bridge = project / "RKF"
        bridge.mkdir(parents=True)
        memory = bridge / "memory.md"
        memory.write_text("custom project memory\n", encoding="utf-8")

        result = auto.write_bridge_folder(project, mode="active-aggressive", project_name="SomeProject")

        self.assertEqual(memory.read_text(encoding="utf-8"), "custom project memory\n")
        self.assertIn(memory.resolve(), result.existing)

    def test_write_bridge_folder_rolls_back_mid_write_failure(self) -> None:
        project = self.root / "BridgeRollback"
        bridge = project / "RKF"
        bridge.mkdir(parents=True)
        memory = bridge / "memory.md"
        memory.write_text("user-owned memory\n", encoding="utf-8")
        before = tree_snapshot(project)
        original = auto._write_if_missing
        calls = 0

        def fail_second(path: Path, text: str) -> bool:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected bridge failure")
            return original(path, text)

        with mock.patch.object(auto, "_write_if_missing", side_effect=fail_second):
            with self.assertRaisesRegex(SystemExit, "rolled back"):
                auto.write_bridge_folder(project, project_name="BridgeRollback")

        self.assertEqual(tree_snapshot(project), before)
        self.assertEqual(memory.read_text(encoding="utf-8"), "user-owned memory\n")

    def test_connect_project_rolls_back_bridge_when_marker_write_fails(self) -> None:
        project = self.root / "ConnectionRollback"
        project.mkdir()
        before = tree_snapshot(project)

        with mock.patch.object(
            auto,
            "write_project_marker",
            side_effect=SystemExit("injected marker failure"),
        ):
            with self.assertRaisesRegex(SystemExit, "injected marker failure"):
                auto.connect_project(project, project_name="ConnectionRollback")

        self.assertEqual(tree_snapshot(project), before)
        self.assertFalse((project / ".rkf-connect.toml").exists())
        self.assertFalse((project / "RKF").exists())

    def test_connect_project_readonly_preflight_is_nonmutating(self) -> None:
        project = self.root / "ReadonlyProject"
        bridge = project / "RKF"
        bridge.mkdir(parents=True)
        bridge.chmod(0o555)
        try:
            before = tree_snapshot(project)
            with self.assertRaisesRegex(SystemExit, "not writable"):
                auto.preview_project_connection(project)
            with self.assertRaisesRegex(SystemExit, "not writable"):
                auto.connect_project(project)
            self.assertEqual(tree_snapshot(project), before)
        finally:
            bridge.chmod(0o755)

        root_readonly = self.root / "ReadonlyRoot"
        root_readonly.mkdir()
        root_readonly.chmod(0o555)
        try:
            with self.assertRaisesRegex(SystemExit, "not writable"):
                auto.preview_project_connection(root_readonly)
            self.assertEqual(list(root_readonly.iterdir()), [])
        finally:
            root_readonly.chmod(0o755)

    def test_bridge_folder_command_writes_files(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(["bridge-folder", str(project), "--project-name", "SomeProject"])

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["created_count"], 4)
        self.assertTrue(payload["paths_redacted"])
        self.assertNotIn(str(project), stdout.getvalue())
        self.assertTrue((project / "RKF" / "README.md").exists())

    def test_connect_project_refuses_missing_project_root(self) -> None:
        missing = self.root / "TypoProject"

        with self.assertRaises(SystemExit):
            auto.preview_project_connection(missing)
        with self.assertRaises(SystemExit):
            auto.connect_project(missing)

        self.assertFalse(missing.exists())

    def test_connect_project_invalid_name_is_rejected_before_any_write(self) -> None:
        project = self.root / "AtomicProject"
        project.mkdir()
        before = tree_snapshot(project)

        with self.assertRaises(SystemExit):
            auto.preview_project_connection(project, project_name="<script>")
        with self.assertRaises(SystemExit):
            auto.connect_project(project, project_name="<script>")

        self.assertEqual(tree_snapshot(project), before)

    def test_connect_project_rejects_non_file_bridge_target_before_marker_write(self) -> None:
        project = self.root / "AtomicProject"
        (project / "RKF" / "memory.md").mkdir(parents=True)
        before = tree_snapshot(project)

        with self.assertRaises(SystemExit):
            auto.preview_project_connection(project)
        with self.assertRaises(SystemExit):
            auto.connect_project(project)

        self.assertEqual(tree_snapshot(project), before)

    def test_connect_project_refuses_broken_marker_and_bridge_symlinks(self) -> None:
        project = self.root / "SymlinkProject"
        project.mkdir()
        outside_marker = self.root / "outside-marker.toml"
        marker = project / ".rkf-connect.toml"
        marker.symlink_to(outside_marker)

        with self.assertRaises(SystemExit):
            auto.connect_project(project)
        self.assertFalse(outside_marker.exists())

        marker.unlink()
        bridge = project / "RKF"
        bridge.mkdir()
        outside_memory = self.root / "outside-memory.md"
        (bridge / "memory.md").symlink_to(outside_memory)

        with self.assertRaises(SystemExit):
            auto.connect_project(project)
        self.assertFalse(outside_memory.exists())
        self.assertFalse((project / ".rkf-connect.toml").exists())

    def test_capture_request_command_outputs_structured_action_json(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(
                [
                    "capture-request",
                    "Cloud paper lead",
                    "--text",
                    "Find DOI 10.1234/cloud.lead",
                    "--origin",
                    "project:Demo",
                    "--doi",
                    "10.1234/cloud.lead",
                    "--intent",
                    "paper-search",
                ]
            )

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["action"], "workflow.add")
        self.assertEqual(payload["params"]["doi"], "10.1234/cloud.lead")

    def test_legacy_command_array_subcommands_are_removed(self) -> None:
        self.assertFalse(hasattr(auto, "build_inbox_command"))
        self.assertFalse(hasattr(auto, "build_hot_command"))
        for argv in (
            ["inbox-command", "Legacy", "--origin", "project:Legacy", "--clip", "note"],
            ["hot-command", "legacy hot query", "--origin", "project:Legacy"],
            ["inbox-execute", "Legacy", "--origin", "project:Legacy", "--clip", "note"],
            ["hot-execute", "legacy hot query", "--origin", "project:Legacy"],
        ):
            with self.assertRaises(SystemExit) as caught:
                auto.main(argv)
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
