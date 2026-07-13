from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, frontmatter
from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.paper_apply import MigrationApplyError, apply_migration, rollback_migration
from rkf.paper_migration import run_preview


def legacy_paper(source_id: str) -> str:
    return frontmatter(
        {
            "type": "paper",
            "status": "draft",
            "source_id": source_id,
            "reading_status": "abstract-only",
            "evidence_ids": [],
            "topics": [],
            "created": "2026-07-01",
            "updated": "2026-07-01",
        }
    ) + (
        f"# {source_id}\n\n"
        "## Source Identity\n\n- DOI: 10.1234/example\n\n"
        "## Source-Grounded Summary\n\n"
        "- Research question: Does it work?\n"
        "- Method/data: A fixture method.\n"
        "- Key findings: A fixture result.\n"
        "- Limitations: Fixture only.\n\n"
        "## Extracted Evidence And Locators\n\n- Locator: p. 1\n\n"
        "## Future Agent Retrieval Brief\n\n- Read this page when: testing migration.\n"
    )


class RKFPaperApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.repo.mkdir()
        self.wiki.mkdir()
        self.raw.mkdir()
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.wiki.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-apply"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        sync = self.wiki / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-apply",'
            '"assigned_at":"2026-07-12T00:00:00Z"}\n',
            encoding="utf-8",
        )
        self.paper_root = self.wiki / "knowledge" / "papers"
        self.paper_root.mkdir(parents=True)
        self.originals = {}
        for index in range(2):
            path = self.paper_root / f"paper-{index}.md"
            path.write_text(legacy_paper(f"doi_example_{index}"), encoding="utf-8")
            self.originals[path.name] = path.read_bytes()
        self.workspace = Workspace(self.repo)
        self.report = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports",
            expected_count=2,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_apply_requires_exact_reviewed_manifest_hash(self) -> None:
        with self.assertRaises(MigrationApplyError):
            apply_migration(
                self.workspace,
                report_dir=self.report.report_dir,
                approved_manifest_hash="0" * 64,
            )

        self.assertEqual(self.originals["paper-0.md"], (self.paper_root / "paper-0.md").read_bytes())
        self.assertFalse((self.raw / "migration_backups").exists())

    def test_input_drift_invalidates_apply_before_backup(self) -> None:
        (self.paper_root / "paper-0.md").write_text("drift\n", encoding="utf-8")

        with self.assertRaises(MigrationApplyError):
            apply_migration(
                self.workspace,
                report_dir=self.report.report_dir,
                approved_manifest_hash=self.report.manifest_hash,
            )

        self.assertFalse((self.raw / "migration_backups").exists())

    def test_apply_and_explicit_rollback_restore_exact_originals(self) -> None:
        applied = apply_migration(
            self.workspace,
            report_dir=self.report.report_dir,
            approved_manifest_hash=self.report.manifest_hash,
        )

        self.assertEqual(applied.status, "applied")
        self.assertEqual(applied.page_count, 2)
        self.assertEqual(applied.ledger_count, 2)
        self.assertIn("schema: rkf-paper-v1.1", (self.paper_root / "paper-0.md").read_text(encoding="utf-8"))
        self.assertTrue((self.wiki / "state" / "reading" / "doi_example_0.json").exists())

        rolled_back = rollback_migration(
            self.workspace,
            backup_id=applied.backup_id,
            approved_manifest_hash=self.report.manifest_hash,
        )

        self.assertEqual(rolled_back.status, "rolled-back")
        for name, original in self.originals.items():
            self.assertEqual(original, (self.paper_root / name).read_bytes())
        self.assertFalse((self.wiki / "state" / "reading" / "doi_example_0.json").exists())

    def test_partial_failure_rolls_back_every_applied_target(self) -> None:
        with self.assertRaises(MigrationApplyError):
            apply_migration(
                self.workspace,
                report_dir=self.report.report_dir,
                approved_manifest_hash=self.report.manifest_hash,
                fail_after=3,
            )

        for name, original in self.originals.items():
            self.assertEqual(original, (self.paper_root / name).read_bytes())
        self.assertFalse((self.wiki / "state" / "reading" / "doi_example_0.json").exists())
        journal = next((self.raw / "migration_backups").rglob("apply-journal.json"))
        self.assertEqual(json.loads(journal.read_text(encoding="utf-8"))["status"], "rolled-back-after-failure")

    def test_actions_require_activation_writer_and_exact_approval(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.repo)
        request = ActionRequest(
            action="paper.migration.apply",
            params={"report_dir": str(self.report.report_dir), "manifest_hash": self.report.manifest_hash},
        )

        blocked = runtime.execute(request)
        runtime.execute(ActionRequest(action="rkf.activate"))
        applied = runtime.execute(request)
        rolled_back = runtime.execute(
            ActionRequest(
                action="paper.migration.rollback",
                params={"backup_id": applied.payload["backup_id"], "manifest_hash": self.report.manifest_hash},
            )
        )

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(applied.status, "ok")
        self.assertEqual(rolled_back.status, "ok")
        self.assertEqual(rolled_back.payload["status"], "rolled-back")


if __name__ == "__main__":
    unittest.main()
