from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class RKFPhase1DocsTests(unittest.TestCase):
    def test_example_config_documents_machine_and_event_boundaries(self) -> None:
        text = (REPO / "rkf.workspace.example.toml").read_text(encoding="utf-8")

        self.assertIn("[machine]", text)
        self.assertIn('id = "machine-7f3a2c91"', text)
        self.assertIn("maintenance_writer = false", text)
        self.assertIn("[sync]", text)
        self.assertIn('writer_registry = "state/sync/maintenance-writer.json"', text)
        self.assertIn('event_root = "state/events"', text)

    def test_public_docs_describe_manual_activation_and_structured_actions(self) -> None:
        architecture = (REPO / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        features = (REPO / "docs" / "FEATURES_AND_COMMANDS.zh-TW.md").read_text(
            encoding="utf-8"
        )
        workflow = (REPO / "docs" / "workflows" / "rkf-auto-connect.zh-TW.md").read_text(
            encoding="utf-8"
        )

        for action in ("rkf.activate", "query.search", "capture.route", "rkf.deactivate"):
            self.assertIn(action, architecture)
            self.assertIn(action, features)
            self.assertIn(action, workflow)
        for mapping in (
            "| 啟動 RKF | `rkf.activate` |",
            "| 問 RKF：... | `query.search` |",
            "| 收進 RKF：... | `capture.route` |",
            "| 停用 RKF | `rkf.deactivate` |",
        ):
            self.assertIn(mapping, features)
        self.assertIn("new Codex task -> OFF", architecture)
        self.assertIn("research request -> query.search", architecture)
        self.assertIn("停用 RKF -> OFF", architecture)
        self.assertIn("capture.project_pending", architecture)
        self.assertIn("capture.project_pending", features)
        self.assertIn("新 task 預設 RKF OFF", workflow)
        for step in (
            "1. 新 task 預設 RKF OFF。",
            "2. 使用者說「啟動 RKF」。",
            "3. Agent 執行 `rkf.activate`",
            "4. 研究型請求先執行 `query.search`",
            "5. DOI、URL、paper lead 或可重用研究討論經 `capture.route`",
            "6. 回報 event ID、dedupe、queued/materialized 與 `Promotion: none`。",
            "7. 使用者說「停用 RKF」後執行 `rkf.deactivate`。",
        ):
            self.assertIn(step, workflow)
        self.assertNotIn("rk hot record", workflow)
        self.assertNotIn("inbox-execute", workflow)
        self.assertNotIn("hot-execute", workflow)

    def test_project_memory_and_changelog_record_phase1_contract(self) -> None:
        memory = (REPO / "docs" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("RKF 1.1 Phase 1", memory)
        self.assertIn("session-owned `RKFActionRuntime`", memory)
        self.assertIn("v1 and v2 project markers mean available, never active", memory)
        self.assertIn("capture.project_pending", memory)
        self.assertIn("RKF 1.1 Phase 1", changelog)
        self.assertIn("Promotion: none", changelog)

    def test_documented_lint_commands_match_the_current_cli(self) -> None:
        agent_guide = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        project_memory = (REPO / "docs" / "PROJECT_MEMORY.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("python3 tools/rk.py lint", agent_guide)
        self.assertIn("python3 tools/rk.py lint --mode all", project_memory)
        self.assertIn("python3 tools/rk.py topic lint", project_memory)
        self.assertIn("python3 tools/rk.py lint --mode graph-lint", project_memory)


if __name__ == "__main__":
    unittest.main()
