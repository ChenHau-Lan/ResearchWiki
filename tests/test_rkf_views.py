from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace
from rkf.views import BASE_FILENAMES, preview_base_views, render_base_views


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class RKFViewsTests(unittest.TestCase):
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
            'id = "machine-views"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        sync_root = self.wiki / "state" / "sync"
        sync_root.mkdir(parents=True)
        (sync_root / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-views",'
            '"assigned_at":"2026-07-11T12:00:00Z"}\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_renderer_emits_five_public_safe_bases(self) -> None:
        views = render_base_views(self.workspace)

        self.assertEqual(tuple(views), BASE_FILENAMES)
        self.assertEqual(
            set(views),
            {"papers.base", "reading-queue.base", "inbox.base", "questions.base", "synthesis.base"},
        )
        self.assertIn('file.inFolder("knowledge/papers")', views["papers.base"])
        self.assertIn('type == "paper"', views["papers.base"])
        self.assertIn("reading_state:", views["reading-queue.base"])
        self.assertNotIn(str(self.root), "\n".join(views.values()))

    def test_preview_does_not_create_views_directory(self) -> None:
        before = file_snapshot(self.root)

        payload = preview_base_views(self.workspace)

        self.assertEqual(file_snapshot(self.root), before)
        self.assertEqual(payload["count"], 5)
        self.assertFalse((self.wiki / "views").exists())

    def test_only_designated_writer_generates_bases(self) -> None:
        writer = RKFActionRuntime(workspace=self.workspace, project_root=self.repo)
        writer.execute(ActionRequest(action="rkf.activate"))

        preview = writer.execute(ActionRequest(action="views.preview"))
        generated = writer.execute(ActionRequest(action="views.generate"))

        self.assertEqual(preview.status, "ok")
        self.assertEqual(preview.payload["count"], 5)
        self.assertEqual(generated.status, "ok")
        self.assertEqual(generated.payload["count"], 5)
        self.assertEqual(set(path.name for path in (self.wiki / "views").glob("*.base")), set(BASE_FILENAMES))

    def test_non_writer_cannot_generate_bases(self) -> None:
        config_path = self.repo / "rkf.workspace.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace("maintenance_writer = true", "maintenance_writer = false"),
            encoding="utf-8",
        )
        non_writer = RKFActionRuntime(workspace=Workspace(self.repo), project_root=self.repo)
        non_writer.execute(ActionRequest(action="rkf.activate"))

        result = non_writer.execute(ActionRequest(action="views.generate"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_WRITER_REQUIRED")

    def test_doctor_blocker_prevents_view_generation(self) -> None:
        writer = RKFActionRuntime(workspace=self.workspace, project_root=self.repo)
        writer.execute(ActionRequest(action="rkf.activate"))
        (self.wiki / "late.sync-conflict.md").write_text("conflict\n", encoding="utf-8")

        result = writer.execute(ActionRequest(action="views.generate"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_VIEW_DOCTOR_BLOCKED")
        self.assertFalse((self.wiki / "views").exists())
        self.assertEqual(writer.session.mode.value, "ACTIVE_READ_ONLY")


if __name__ == "__main__":
    unittest.main()
