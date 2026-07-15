from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace
from rkf.maintenance import plan_maintenance
from rkf.sync import sha256_file


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class RKFMaintenancePlanTests(unittest.TestCase):
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
            'id = "machine-maintenance"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        sync_root = self.wiki / "state" / "sync"
        sync_root.mkdir(parents=True)
        (sync_root / "maintenance-writer.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-writer-registry-v1",
                    "machine_id": "machine-maintenance",
                    "assigned_at": "2026-07-11T12:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        incoming = self.raw / "incoming"
        incoming.mkdir()
        self.incoming_pdf = incoming / "new-paper.pdf"
        self.incoming_pdf.write_bytes(b"private source bytes")
        self.workspace = Workspace(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_daily_plan_scans_incoming_without_writing(self) -> None:
        before = file_snapshot(self.root)

        plan = plan_maintenance(self.workspace, cadence="daily", now=datetime(2026, 7, 11, 8, 0, 0))

        self.assertEqual(file_snapshot(self.root), before)
        self.assertEqual(plan.promotion, "none")
        self.assertEqual(plan.incoming[0].checksum, sha256_file(self.incoming_pdf))
        self.assertEqual(plan.incoming[0].logical_id, "raw/incoming/new-paper.pdf")
        self.assertIn("review source identity", plan.actions[0].reason)

    def test_weekly_and_monthly_plans_stay_proposal_only(self) -> None:
        weekly = plan_maintenance(self.workspace, cadence="weekly", now=datetime(2026, 7, 11, 8, 0, 0))
        monthly = plan_maintenance(self.workspace, cadence="monthly", now=datetime(2026, 7, 11, 8, 0, 0))

        self.assertIn("lint.run", {item.action for item in weekly.actions})
        self.assertIn("cleanup.manifest.preview", {item.action for item in monthly.actions})
        self.assertTrue(all(item.promotion == "none" for item in (*weekly.actions, *monthly.actions)))


class RKFMaintenanceActionTests(RKFMaintenancePlanTests):
    def test_fresh_runtime_blocks_maintenance_before_activation(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.repo, allow_internal_actions=True)
        before = file_snapshot(self.root)

        result = runtime.execute(ActionRequest(action="maintenance.preview", params={"cadence": "daily"}))

        self.assertEqual(file_snapshot(self.root), before)
        self.assertEqual(result.payload["error_code"], "RKF_NOT_ACTIVE")

    def test_only_writer_runs_daily_maintenance_with_no_promotion(self) -> None:
        writer = RKFActionRuntime(workspace=self.workspace, project_root=self.repo, allow_internal_actions=True)
        writer.execute(ActionRequest(action="rkf.activate"))

        preview = writer.execute(ActionRequest(action="maintenance.preview", params={"cadence": "daily"}))
        receipt = writer.execute(ActionRequest(action="maintenance.run", params={"cadence": "daily"}))

        self.assertEqual(preview.status, "ok")
        self.assertEqual(receipt.status, "ok")
        self.assertEqual(receipt.payload["promotion"], "none")
        self.assertEqual(receipt.payload["doctor_status"], "warning")
        self.assertTrue(
            any(
                finding["code"] == "PDF_IDENTITY_UNVERIFIED"
                for finding in receipt.payload["doctor"]["findings"]
            )
        )

    def test_non_writer_cannot_run_maintenance(self) -> None:
        config_path = self.repo / "rkf.workspace.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace("maintenance_writer = true", "maintenance_writer = false"),
            encoding="utf-8",
        )
        runtime = RKFActionRuntime(workspace=Workspace(self.repo), project_root=self.repo, allow_internal_actions=True)
        runtime.execute(ActionRequest(action="rkf.activate"))

        result = runtime.execute(ActionRequest(action="maintenance.run", params={"cadence": "daily"}))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_WRITER_REQUIRED")

    def test_doctor_blocker_prevents_maintenance_run(self) -> None:
        writer = RKFActionRuntime(workspace=self.workspace, project_root=self.repo, allow_internal_actions=True)
        writer.execute(ActionRequest(action="rkf.activate"))
        (self.wiki / "late.sync-conflict.md").write_text("conflict\n", encoding="utf-8")

        result = writer.execute(ActionRequest(action="maintenance.run", params={"cadence": "daily"}))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_MAINTENANCE_DOCTOR_BLOCKED")
        self.assertEqual(writer.session.mode.value, "ACTIVE_READ_ONLY")


if __name__ == "__main__":
    unittest.main()
