from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, parse_toml_fallback
from rkf.session import (
    SessionMode,
    activate_session,
    deactivate_session,
    new_session,
    read_project_policy,
    session_receipt,
)


class RKFSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.project = self.root / "project"
        self.wiki.mkdir()
        self.raw.mkdir()
        self.project.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.wiki.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-7f3a2c91"\n'
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1"\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_session_is_off_and_receipt_contains_no_absolute_paths(self) -> None:
        session = new_session("task-001")

        receipt = session_receipt(session)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["session_id"], "task-001")
        self.assertEqual(receipt["mode"], "OFF")
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_fallback_toml_parser_preserves_top_level_and_boolean_types(self) -> None:
        parsed = parse_toml_fallback(
            "version = 2\n\n"
            "[rkf]\n"
            "available = true\n"
            'activation = "manual"\n'
            "query_first = false\n"
        )

        self.assertEqual(parsed["version"], 2)
        self.assertIs(parsed["rkf"]["available"], True)
        self.assertEqual(parsed["rkf"]["activation"], "manual")
        self.assertIs(parsed["rkf"]["query_first"], False)

    def test_fallback_toml_parser_rejects_malformed_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_toml_fallback("version = [broken\n")

    def test_v1_and_v2_markers_only_mean_available(self) -> None:
        (self.project / ".rkf-connect.toml").write_text(
            "[rkf_auto_connect]\n"
            "enabled = true\n"
            'mode = "active-aggressive"\n',
            encoding="utf-8",
        )
        v1 = read_project_policy(self.project)
        (self.project / ".rkf-connect.toml").write_text(
            "version = 2\n\n"
            "[rkf]\n"
            "available = true\n"
            'activation = "manual"\n'
            "query_first = true\n"
            'capture_mode = "active-aggressive"\n',
            encoding="utf-8",
        )
        v2 = read_project_policy(self.project)

        self.assertTrue(v1.available)
        self.assertEqual(v1.activation, "manual")
        self.assertTrue(v2.available)
        self.assertEqual(v2.activation, "manual")

    def test_activation_is_read_only_and_becomes_active(self) -> None:
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        session = new_session("task-002")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertEqual(session.mode, SessionMode.ACTIVE)
        self.assertEqual(receipt["roots"]["wiki_root"], {"exists": True, "readable": True})
        self.assertEqual(receipt["roots"]["raw_root"], {"exists": True, "readable": True})
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_conflict_degrades_to_active_read_only(self) -> None:
        (self.wiki / "paper.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
        session = new_session("task-003")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        self.assertEqual(session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("SYNC_CONFLICT", receipt["warnings"])

    def test_missing_raw_root_fails_activation(self) -> None:
        self.raw.rmdir()
        session = new_session("task-004")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["error_code"], "RKF_PREFLIGHT_FAILED")

    def test_deactivate_clears_active_scope(self) -> None:
        session = new_session("task-005")
        activate_session(session, self.workspace, project_root=self.project)

        receipt = deactivate_session(session)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["mode"], "OFF")
        self.assertEqual(receipt["writer_role"], "unknown")

    def test_malformed_marker_returns_masked_off_receipt(self) -> None:
        (self.project / ".rkf-connect.toml").write_text(
            "version = [broken\n",
            encoding="utf-8",
        )
        session = new_session("task-bad-marker")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["error_code"], "RKF_PROJECT_UNAVAILABLE")
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_malformed_writer_registry_degrades_without_path_leak(self) -> None:
        config = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(
            config.replace("maintenance_writer = false", "maintenance_writer = true"),
            encoding="utf-8",
        )
        sync = self.wiki / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text("{broken", encoding="utf-8")
        session = new_session("task-bad-writer")

        receipt = activate_session(
            session,
            Workspace(self.root),
            project_root=self.project,
        )

        self.assertEqual(session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("WRITER_REGISTRY_MISMATCH", receipt["warnings"])
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_semantically_invalid_marker_and_registry_are_rejected(self) -> None:
        (self.project / ".rkf-connect.toml").write_text(
            'version = "two"\n', encoding="utf-8"
        )
        marker_session = new_session("task-semantic-marker")
        marker_receipt = activate_session(
            marker_session, self.workspace, project_root=self.project
        )
        self.assertEqual(marker_session.mode, SessionMode.OFF)
        self.assertEqual(marker_receipt["error_code"], "RKF_PROJECT_UNAVAILABLE")

        (self.project / ".rkf-connect.toml").unlink()
        config = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(
            config.replace("maintenance_writer = false", "maintenance_writer = true"),
            encoding="utf-8",
        )
        sync = self.wiki / "state" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-7f3a2c91",'
            '"assigned_at":123}\n',
            encoding="utf-8",
        )
        registry_session = new_session("task-semantic-registry")
        registry_receipt = activate_session(
            registry_session, Workspace(self.root), project_root=self.project
        )
        self.assertEqual(registry_session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("WRITER_REGISTRY_MISMATCH", registry_receipt["warnings"])

        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-7f3a2c91",'
            '"assigned_at":"2026-07-10"}\n',
            encoding="utf-8",
        )
        date_only_session = new_session("task-date-only-registry")
        date_only_receipt = activate_session(
            date_only_session, Workspace(self.root), project_root=self.project
        )
        self.assertEqual(date_only_session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("WRITER_REGISTRY_MISMATCH", date_only_receipt["warnings"])

    def test_activation_uses_the_configured_writer_registry(self) -> None:
        config = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(
            config.replace("maintenance_writer = false", "maintenance_writer = true")
            + "\n[sync]\nwriter_registry = \"state/sync/alternate-writer.json\"\n",
            encoding="utf-8",
        )
        sync = self.wiki / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-7f3a2c91",'
            '"assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        (sync / "alternate-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"other-machine",'
            '"assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        session = new_session("task-alternate-registry")

        receipt = activate_session(session, Workspace(self.root), project_root=self.project)

        self.assertEqual(session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("WRITER_REGISTRY_MISMATCH", receipt["warnings"])


if __name__ == "__main__":
    unittest.main()
