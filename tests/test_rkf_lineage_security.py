from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from rkf.lineage import (
    LineageStorageError,
    activity_timeline,
    input_fingerprint,
    record_action,
    record_activation,
    record_activation_transition,
    result_fingerprint,
    update_activation,
)


ACTIVATION_ID = "act_111111111111111111111111"
PROJECT_ID = "prj_222222222222222222222222"


def action_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "activation_id": ACTIVATION_ID,
        "origin_project_id": PROJECT_ID,
        "action": "workflow.ask",
        "status": "ok",
        "affected_object_ids": [],
    }
    payload.update(updates)
    return payload


def activation_payload() -> dict[str, object]:
    return {
        "activation_id": ACTIVATION_ID,
        "project_id": PROJECT_ID,
        "project_name": "fixture",
        "mode": "ACTIVE_READ_WRITE",
        "result": "ok",
    }


def transition_payload() -> dict[str, object]:
    return {
        "activation_id": ACTIVATION_ID,
        "project_id": PROJECT_ID,
        "project_name": "fixture",
        "transition": "started",
        "mode": "ACTIVE_READ_WRITE",
    }


class LineageStorageSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _repo(self, name: str) -> Path:
        root = self.base / name
        root.mkdir()
        return root

    def test_rejects_symlinked_lineage_root(self) -> None:
        root = self._repo("lineage-root")
        private_root = root / ".rkf_private"
        private_root.mkdir()
        outside = self.base / "outside-lineage"
        outside.mkdir()
        (private_root / "lineage").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(LineageStorageError):
            record_action(root, action_payload())

        self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_symlinked_fallback_root(self) -> None:
        root = self._repo("fallback-root")
        outside_private = self.base / "outside-private"
        outside_private.mkdir()
        outside_fallback = self.base / "outside-fallback"
        outside_fallback.mkdir()
        (root / ".rkf_private").symlink_to(outside_private, target_is_directory=True)
        (root / ".rkf_lineage").symlink_to(outside_fallback, target_is_directory=True)

        with self.assertRaises(LineageStorageError):
            record_action(root, action_payload())

        self.assertEqual(list(outside_private.iterdir()), [])
        self.assertEqual(list(outside_fallback.iterdir()), [])

    def test_safe_fallback_stays_inside_workspace(self) -> None:
        root = self._repo("safe-fallback")
        outside_private = self.base / "outside-safe-private"
        outside_private.mkdir()
        (root / ".rkf_private").symlink_to(outside_private, target_is_directory=True)

        path, _ = record_action(root, action_payload())

        self.assertEqual(
            path.parent.resolve(),
            (root / ".rkf_lineage" / "actions").resolve(),
        )
        self.assertEqual(list(outside_private.iterdir()), [])
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE((root / ".rkf_lineage").stat().st_mode), 0o700)

    def test_rejects_symlinked_lineage_subdirectories(self) -> None:
        operations = {
            "actions": lambda root: record_action(root, action_payload()),
            "activations": lambda root: record_activation(root, activation_payload()),
            "activation_events": lambda root: record_activation_transition(
                root, transition_payload()
            ),
        }
        for subdirectory, operation in operations.items():
            with self.subTest(subdirectory=subdirectory):
                root = self._repo(f"subdir-{subdirectory}")
                lineage = root / ".rkf_private" / "lineage"
                lineage.mkdir(parents=True)
                outside = self.base / f"outside-{subdirectory}"
                outside.mkdir()
                (lineage / subdirectory).symlink_to(outside, target_is_directory=True)

                with self.assertRaises(LineageStorageError):
                    operation(root)

                self.assertEqual(list(outside.iterdir()), [])

    def test_timeline_rejects_symlinked_actions_directory(self) -> None:
        root = self._repo("timeline-root")
        lineage = root / ".rkf_private" / "lineage"
        lineage.mkdir(parents=True)
        outside = self.base / "outside-timeline"
        outside.mkdir()
        (outside / "external.json").write_text(
            json.dumps({"event_id": "aevt_external", "status": "ok"}),
            encoding="utf-8",
        )
        (lineage / "actions").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(LineageStorageError):
            activity_timeline(root)

    def test_rejects_symlinked_target_json(self) -> None:
        root = self._repo("target-link")
        events = root / ".rkf_private" / "lineage" / "activation_events"
        events.mkdir(parents=True)
        event_id = "actevt_" + hashlib.sha256(
            f"{ACTIVATION_ID}\0started".encode("utf-8")
        ).hexdigest()[:24]
        outside = self.base / "outside-event.json"
        outside.write_text('{"sentinel": "unchanged"}\n', encoding="utf-8")
        (events / f"{event_id}.json").symlink_to(outside)
        before = outside.read_bytes()

        with self.assertRaises(LineageStorageError):
            record_activation_transition(root, transition_payload())

        self.assertEqual(outside.read_bytes(), before)

    def test_update_activation_rejects_path_traversal(self) -> None:
        root = self._repo("update-traversal")
        outside = self.base / "outside.json"
        outside.write_text('{"sentinel": "unchanged"}\n', encoding="utf-8")
        before = outside.read_bytes()

        with self.assertRaisesRegex(ValueError, "invalid activation_id"):
            update_activation(root, "../../../../outside", changed=True)

        self.assertEqual(outside.read_bytes(), before)

    def test_private_lineage_modes_are_restrictive_even_with_open_umask(self) -> None:
        root = self._repo("modes")
        old_umask = os.umask(0o000)
        try:
            path, _ = record_action(root, action_payload())
        finally:
            os.umask(old_umask)

        if os.name == "posix":
            for directory in (
                root / ".rkf_private",
                root / ".rkf_private" / "lineage",
                root / ".rkf_private" / "lineage" / "actions",
            ):
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_existing_private_modes_are_normalized(self) -> None:
        root = self._repo("normalize-modes")
        path, _ = record_action(root, action_payload())
        if os.name != "posix":
            self.skipTest("POSIX permission modes are required")
        for directory in (
            root / ".rkf_private",
            root / ".rkf_private" / "lineage",
            root / ".rkf_private" / "lineage" / "actions",
        ):
            directory.chmod(0o755)
        path.chmod(0o644)

        activity_timeline(root)

        for directory in (
            root / ".rkf_private",
            root / ".rkf_private" / "lineage",
            root / ".rkf_private" / "lineage" / "actions",
        ):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_object_fingerprints_are_validated_and_affect_result_identity(self) -> None:
        root = self._repo("object-fingerprints")
        affected = ["papers/z", "papers/a"]
        fingerprints = {"papers/z": "f" * 64, "papers/a": "a" * 64}
        payload = action_payload(
            affected_object_ids=affected,
            object_fingerprints=fingerprints,
        )

        _, event = record_action(root, payload)

        self.assertEqual(list(event["object_fingerprints"]), ["papers/a", "papers/z"])
        baseline = result_fingerprint({"status": "ok", "affected_object_ids": affected})
        with_objects = result_fingerprint(
            {
                "status": "ok",
                "affected_object_ids": affected,
                "object_fingerprints": fingerprints,
            }
        )
        self.assertNotEqual(baseline, with_objects)
        self.assertEqual(event["input_fingerprint"], input_fingerprint(payload))

    def test_object_fingerprints_must_be_valid_and_affected(self) -> None:
        root = self._repo("invalid-object-fingerprints")
        with self.assertRaisesRegex(ValueError, "object_fingerprints"):
            record_action(
                root,
                action_payload(
                    affected_object_ids=["papers/a"],
                    object_fingerprints={"papers/a": "invalid"},
                ),
            )
        with self.assertRaisesRegex(ValueError, "affected_object_ids"):
            record_action(
                root,
                action_payload(
                    affected_object_ids=["papers/a"],
                    object_fingerprints={"papers/b": "b" * 64},
                ),
            )


if __name__ == "__main__":
    unittest.main()
