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

    def test_build_inbox_request_uses_structured_action(self) -> None:
        config = auto.load_connector_config()
        request = auto.build_inbox_request(
            config=config,
            title="ChatGPT note on aerosol paper",
            origin="project:QUACS",
            clip="Short source-grounded summary mentioning DOI 10.1234/example.",
            reader_note="User idea goes here.",
            doi="10.1234/example",
            source_url="https://example.org/paper",
            no_inject=False,
        )

        self.assertEqual(request.action, "inbox.capture")
        self.assertEqual(request.params["doi"], "10.1234/example")
        self.assertEqual(request.params["origin"], "project:QUACS")
        self.assertNotIn("/" + "Users/", repr(request.params))

    def test_build_hot_request_records_research_demand(self) -> None:
        config = auto.load_connector_config()
        request = auto.build_hot_request(
            config=config,
            query="recent aerosol-cloud parameterization papers",
            origin="project:ResearchProject",
            intent="paper-search",
        )

        self.assertEqual(request.action, "hot.record")
        self.assertEqual(request.params["query"], "recent aerosol-cloud parameterization papers")
        self.assertEqual(request.params["intent"], "paper-search")

    def test_execute_action_request_writes_to_configured_researchwiki_root(self) -> None:
        config = auto.load_connector_config()
        request = auto.build_hot_request(
            config=config,
            query="recent aerosol-cloud parameterization papers",
            origin="project:ResearchProject",
            intent="paper-search",
        )

        result = auto.execute_action_request(config=config, request=request)

        self.assertEqual(result.status, "ok")
        hot = (self.researchwiki / "hot.md").read_text(encoding="utf-8")
        self.assertIn("recent aerosol-cloud parameterization papers", hot)

    def test_write_project_marker_is_public_safe(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")

        self.assertEqual(marker, project / ".rkf-connect.toml")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("enabled = true", text)
        self.assertIn("mode = \"active-aggressive\"", text)
        self.assertNotIn(str(self.researchwiki), text)

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

    def test_hot_request_command_outputs_structured_action_json(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(
                [
                    "hot-request",
                    "recent aerosol-cloud parameterization papers",
                    "--origin",
                    "project:ResearchProject",
                    "--intent",
                    "paper-search",
                ]
            )

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["action"], "hot.record")
        self.assertEqual(payload["params"]["intent"], "paper-search")

    def test_hot_execute_command_writes_without_legacy_cli(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(
                [
                    "hot-execute",
                    "recent aerosol-cloud parameterization papers",
                    "--origin",
                    "project:ResearchProject",
                    "--intent",
                    "paper-search",
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("recorded hot query:", stdout.getvalue())
        hot = (self.researchwiki / "hot.md").read_text(encoding="utf-8")
        self.assertIn("recent aerosol-cloud parameterization papers", hot)

    def test_legacy_command_array_subcommands_are_removed(self) -> None:
        self.assertFalse(hasattr(auto, "build_inbox_command"))
        self.assertFalse(hasattr(auto, "build_hot_command"))
        for argv in (
            ["inbox-command", "Legacy", "--origin", "project:Legacy", "--clip", "note"],
            ["hot-command", "legacy hot query", "--origin", "project:Legacy"],
        ):
            with self.assertRaises(SystemExit) as caught:
                auto.main(argv)
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
