from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tools import rkf_auto_connect as auto


class RKFAutoConnectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.researchwiki = self.root / "ResearchWiki"
        self.researchwiki.mkdir()
        (self.researchwiki / "tools").mkdir()
        (self.researchwiki / "tools" / "rk.py").write_text("# test RKF CLI\n", encoding="utf-8")
        (self.researchwiki / "rkf.workspace.toml").write_text(
            "[storage]\nwiki_root = \"${HOME}/ResearchWiki/wiki\"\n",
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

    def test_build_inbox_command_uses_existing_rkf_cli(self) -> None:
        config = auto.load_connector_config()
        command = auto.build_inbox_command(
            config=config,
            title="ChatGPT note on aerosol paper",
            origin="project:QUACS",
            clip="Short source-grounded summary mentioning DOI 10.1234/example.",
            reader_note="User idea goes here.",
            doi="10.1234/example",
            source_url="https://example.org/paper",
            no_inject=False,
        )

        self.assertEqual(command[:4], ["python3", str((self.researchwiki / "tools" / "rk.py").resolve()), "inbox", "capture"])
        self.assertIn("--doi", command)
        self.assertIn("10.1234/example", command)
        self.assertNotIn("/" + "Users/", " ".join(command))

    def test_build_hot_command_records_research_demand(self) -> None:
        config = auto.load_connector_config()
        command = auto.build_hot_command(
            config=config,
            query="recent aerosol-cloud parameterization papers",
            origin="project:ResearchProject",
            intent="paper-search",
        )

        self.assertEqual(command[:4], ["python3", str((self.researchwiki / "tools" / "rk.py").resolve()), "hot", "record"])
        self.assertIn("--intent", command)
        self.assertIn("paper-search", command)

    def test_write_project_marker_is_public_safe(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")

        self.assertEqual(marker, project / ".rkf-connect.toml")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("enabled = true", text)
        self.assertIn("mode = \"active-aggressive\"", text)
        self.assertNotIn(str(self.researchwiki), text)


if __name__ == "__main__":
    unittest.main()
