from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.cleanup import inventory_cleanup, write_cleanup_manifest
from rkf.core import Workspace


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class RKFCleanupManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        duplicate = self.root / "docs" / "manuals" / "assets" / "duplicate.png"
        canonical = self.root / "examples" / "assets" / "canonical.png"
        duplicate.parent.mkdir(parents=True)
        canonical.parent.mkdir(parents=True)
        duplicate.write_bytes(b"same image bytes")
        canonical.write_bytes(b"same image bytes")
        cache = self.root / "rkf" / "__pycache__" / "module.pyc"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"cache")
        (self.root / "log.md").write_text("# old log\n", encoding="utf-8")
        (self.root / "README.md").write_text("See log.md for legacy details.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_manifest_never_deletes_or_archives(self) -> None:
        before = file_snapshot(self.root)

        manifest = inventory_cleanup(
            self.root,
            automation_candidates=[{"id": "legacy-paused", "status": "PAUSED", "name": "old RKF job"}],
        )

        self.assertEqual(file_snapshot(self.root), before)
        duplicate = next(item for item in manifest.entries if item.logical_id == "docs/manuals/assets/duplicate.png")
        self.assertEqual(duplicate.kind, "duplicate-asset")
        self.assertEqual(duplicate.approval_status, "pending")
        self.assertEqual(duplicate.dry_run, "no-change")
        self.assertEqual(duplicate.recommended_action, "review-delete")
        self.assertTrue(any(item.logical_id == "rkf/__pycache__/module.pyc" for item in manifest.entries))
        log = next(item for item in manifest.entries if item.logical_id == "log.md")
        self.assertEqual(log.recommended_action, "retain")
        self.assertTrue(log.references)
        self.assertTrue(any(item.logical_id == "automation:legacy-paused" for item in manifest.entries))

    def test_manifest_writer_only_creates_private_review_file(self) -> None:
        manifest = inventory_cleanup(self.root)
        before = file_snapshot(self.root)
        report_root = self.root / ".rkf_private" / "cleanup_manifests"

        path = write_cleanup_manifest(manifest, report_root)

        after = file_snapshot(self.root)
        self.assertTrue(path.exists())
        self.assertEqual(path.parent, report_root)
        self.assertEqual(set(after) - set(before), {path.relative_to(self.root).as_posix()})
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["approval_status"], "pending")
        self.assertEqual(payload["manifest_hash"], manifest.manifest_hash)

    def test_cleanup_manifest_schema_requires_review_and_rollback_fields(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "cleanup_manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertIn("manifest_hash", schema["required"])
        entry = schema["properties"]["entries"]["items"]
        self.assertIn("rollback", entry["required"])
        self.assertIn("approval_status", entry["required"])
        self.assertEqual(entry["properties"]["dry_run"]["const"], "no-change")

    def test_empty_shared_raw_full_text_directory_is_a_read_only_candidate(self) -> None:
        raw_root = self.root / "shared-raw"
        (raw_root / "full_txt").mkdir(parents=True)

        manifest = inventory_cleanup(self.root, raw_root=raw_root)

        candidate = next(item for item in manifest.entries if item.logical_id == "raw/full_txt")
        self.assertEqual(candidate.kind, "empty-directory")
        self.assertEqual(candidate.approval_status, "pending")

    def test_referenced_cleanup_candidates_are_retained_for_review(self) -> None:
        (self.root / "README.md").write_text(
            "Use docs/manuals/assets/duplicate.png and raw/full_txt.\n",
            encoding="utf-8",
        )
        raw_root = self.root / "shared-raw"
        (raw_root / "full_txt").mkdir(parents=True)

        manifest = inventory_cleanup(self.root, raw_root=raw_root)

        duplicate = next(item for item in manifest.entries if item.logical_id == "docs/manuals/assets/duplicate.png")
        full_text = next(item for item in manifest.entries if item.logical_id == "raw/full_txt")
        self.assertEqual(duplicate.recommended_action, "retain")
        self.assertEqual(full_text.recommended_action, "retain")

    def test_current_paused_replacement_is_retained_not_retired(self) -> None:
        manifest = inventory_cleanup(
            self.root,
            automation_candidates=[
                {"id": "rkf-maintenance-preview", "status": "PAUSED", "role": "replacement"}
            ],
        )

        candidate = next(item for item in manifest.entries if item.logical_id == "automation:rkf-maintenance-preview")

        self.assertEqual(candidate.recommended_action, "retain")
        self.assertEqual(candidate.approval_status, "pending")


class RKFCleanupActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.wiki.mkdir()
        self.raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.wiki.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-cleanup"\n'
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_preview_requires_activation_and_writes_only_private_report(self) -> None:
        fresh = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        before = file_snapshot(self.root)

        blocked = fresh.execute(ActionRequest(action="cleanup.manifest.preview"))

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(file_snapshot(self.root), before)

        fresh.execute(ActionRequest(action="rkf.activate"))
        preview = fresh.execute(
            ActionRequest(
                action="cleanup.manifest.preview",
                params={"automation_candidates": [{"id": "paused-one", "status": "PAUSED"}]},
            )
        )

        self.assertEqual(preview.status, "ok")
        self.assertEqual(preview.payload["manifest"]["approval_status"], "pending")
        self.assertTrue((self.root / ".rkf_private" / "cleanup_manifests").exists())

    def test_preview_rejects_a_report_root_inside_canonical_storage(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        runtime.execute(ActionRequest(action="rkf.activate"))
        before = file_snapshot(self.root)

        result = runtime.execute(
            ActionRequest(
                action="cleanup.manifest.preview",
                params={"report_root": str(self.wiki / ".rkf_private" / "cleanup_manifests")},
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_CLEANUP_REPORT_ROOT_REJECTED")
        self.assertEqual(file_snapshot(self.root), before)

    def test_preview_rejects_a_private_root_symlink_to_canonical_storage(self) -> None:
        link = self.root / ".rkf_private"
        link.symlink_to(self.wiki, target_is_directory=True)
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        runtime.execute(ActionRequest(action="rkf.activate"))
        before = file_snapshot(self.root)

        result = runtime.execute(ActionRequest(action="cleanup.manifest.preview"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_CLEANUP_REPORT_ROOT_REJECTED")
        self.assertEqual(file_snapshot(self.root), before)

    def test_preview_rejects_a_private_root_symlink_outside_the_workspace(self) -> None:
        external = self.root.parent / f"{self.root.name}-external"
        external.mkdir()
        link = self.root / ".rkf_private"
        link.symlink_to(external, target_is_directory=True)
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        runtime.execute(ActionRequest(action="rkf.activate"))

        result = runtime.execute(ActionRequest(action="cleanup.manifest.preview"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_CLEANUP_REPORT_ROOT_REJECTED")
        self.assertEqual(list(external.iterdir()), [])

    def test_default_wiki_root_rejects_its_private_report_directory(self) -> None:
        root = self.root / "default-workspace"
        raw = self.root / "default-raw"
        root.mkdir()
        raw.mkdir()
        (root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'raw_root = "{raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-default"\n'
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        workspace = Workspace(root)
        runtime = RKFActionRuntime(workspace=workspace, project_root=root)
        runtime.execute(ActionRequest(action="rkf.activate"))
        before = file_snapshot(root)

        result = runtime.execute(ActionRequest(action="cleanup.manifest.preview"))

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_CLEANUP_REPORT_ROOT_REJECTED")
        self.assertEqual(file_snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
