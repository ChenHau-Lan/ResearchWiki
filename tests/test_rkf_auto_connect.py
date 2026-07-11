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

from tools import rkf_auto_connect as auto


REPO = Path(__file__).resolve().parents[1]


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
        self.assertEqual(query.action, "query.search")
        self.assertEqual(capture.action, "capture.route")
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

    def test_write_project_marker_uses_v2_manual_activation(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")
        policy = auto.read_project_marker(project)

        self.assertEqual(marker, project / ".rkf-connect.toml")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("version = 2", text)
        self.assertIn("available = true", text)
        self.assertIn('activation = "manual"', text)
        self.assertNotIn("enabled = true", text)
        self.assertTrue(policy["available"])
        self.assertEqual(policy["activation"], "manual")
        self.assertNotIn(str(self.researchwiki), text)

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
        auto.write_project_marker(
            project,
            mode="active-aggressive",
            approve_upgrade=True,
        )
        self.assertIn("version = 2", marker.read_text(encoding="utf-8"))

    def test_write_bridge_folder_creates_project_local_index_files(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        result = auto.write_bridge_folder(project, mode="active-aggressive", project_name="SomeProject")

        self.assertEqual(result.root, project / "RKF")
        expected_files = {
            project / "RKF" / "README.md",
            project / "RKF" / "hot.md",
            project / "RKF" / "memory.md",
            project / "RKF" / "captures.md",
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
        self.assertIn("capture.route", hot)

    def test_write_bridge_folder_preserves_existing_files(self) -> None:
        project = self.root / "SomeProject"
        bridge = project / "RKF"
        bridge.mkdir(parents=True)
        memory = bridge / "memory.md"
        memory.write_text("custom project memory\n", encoding="utf-8")

        result = auto.write_bridge_folder(project, mode="active-aggressive", project_name="SomeProject")

        self.assertEqual(memory.read_text(encoding="utf-8"), "custom project memory\n")
        self.assertIn(memory, result.existing)

    def test_bridge_folder_command_writes_files(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(["bridge-folder", str(project), "--project-name", "SomeProject"])

        self.assertEqual(status, 0)
        self.assertIn(str(project / "RKF"), stdout.getvalue())
        self.assertTrue((project / "RKF" / "README.md").exists())

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
        self.assertEqual(payload["action"], "capture.route")
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
