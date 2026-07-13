from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from rkf.core import Workspace, read_json
from rkf.events import (
    build_operational_event,
    load_operational_events,
    load_recent_operational_events,
    write_operational_event,
)


class RKFOperationalEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_event_id_and_path_are_unique_and_public_safe(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="project:Demo",
            machine_id="machine-7f3a2c91",
            target_identity="doi:10.1234/example",
            idempotency_key="idem-123",
            payload={"title": "Example paper", "promotion": "none"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="a1b2c3d4",
        )

        path = write_operational_event(self.workspace, event)
        stored = read_json(path)

        self.assertEqual(stored["schema"], "rkf-operational-event-v1")
        self.assertEqual(stored["event_id"], event.event_id)
        self.assertEqual(path.parent.name, "2026-07-10")
        self.assertEqual(stored["payload"]["promotion"], "none")

    def test_existing_event_cannot_be_overwritten(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="query:cloud",
            idempotency_key="idem-456",
            payload={"query": "cloud microphysics"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="fixednonce",
        )
        write_operational_event(self.workspace, event)

        with self.assertRaises(FileExistsError):
            write_operational_event(self.workspace, event)

    def test_private_path_payload_is_rejected(self) -> None:
        private_value = "/" + "Users/example/private.pdf"

        with self.assertRaises(SystemExit):
            build_operational_event(
                action="capture.route",
                actor="codex",
                origin="codex",
                machine_id="machine-7f3a2c91",
                target_identity="file:private",
                idempotency_key="idem-789",
                payload={"clip": private_value},
            )

    def test_complete_event_envelope_rejects_secrets_private_paths_and_email(self) -> None:
        unsafe_values = (
            {"origin": "/Volumes/Private/research", "payload": {"title": "Paper"}},
            {"origin": "codex", "payload": {"attachment": "/tmp/private-paper.pdf"}},
            {"origin": "codex", "payload": {"agent_note": "api_key=hidden"}},
            {"origin": "codex", "payload": {"agent_note": "sk-proj-AbCdEf1234567890"}},
            {"origin": "codex", "payload": {"authors": "private@example.org"}},
        )
        for case in unsafe_values:
            with self.subTest(case=case), self.assertRaises(SystemExit):
                build_operational_event(
                    action="capture.route",
                    actor="codex",
                    origin=case["origin"],
                    machine_id="machine-7f3a2c91",
                    target_identity="doi:10.1234/unsafe",
                    idempotency_key="idem-unsafe",
                    payload=case["payload"],
                )

    def test_loader_skips_malformed_event_files(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="doi:10.1234/valid",
            idempotency_key="idem-valid",
            payload={"title": "Valid paper"},
            nonce="valid0001",
        )
        write_operational_event(self.workspace, event)
        broken = self.workspace.paths.events / "2026-07-10" / "evt_broken.json"
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text("{truncated", encoding="utf-8")

        loaded = load_operational_events(self.workspace)

        self.assertEqual([item["event_id"] for item in loaded], [event.event_id])

    def test_loader_skips_valid_json_with_invalid_timestamp_or_unsafe_payload(self) -> None:
        folder = self.workspace.paths.events / "2026-07-10"
        folder.mkdir(parents=True, exist_ok=True)
        base = {
            "schema": "rkf-operational-event-v1",
            "event_id": "evt_20260710T120000Z_machine-test_invalid",
            "action": "capture.route",
            "actor": "codex",
            "origin": "codex",
            "machine_id": "machine-test",
            "created": "not-a-date",
            "target_identity": "doi:10.1234/invalid",
            "idempotency_key": "idem-invalid",
            "public_safe": True,
            "payload": {"title": "Paper"},
        }
        (folder / f"{base['event_id']}.json").write_text(
            json.dumps(base), encoding="utf-8"
        )
        unsafe = dict(base)
        unsafe["event_id"] = "evt_20260710T120001Z_machine-test_unsafe"
        unsafe["created"] = "2026-07-10T12:00:01Z"
        unsafe["payload"] = {"attachment": "/tmp/private.pdf"}
        (folder / f"{unsafe['event_id']}.json").write_text(
            json.dumps(unsafe), encoding="utf-8"
        )

        self.assertEqual(load_operational_events(self.workspace), [])

    def test_event_timestamp_requires_rfc3339_datetime_with_timezone(self) -> None:
        with self.assertRaises(SystemExit):
            build_operational_event(
                action="capture.route",
                actor="codex",
                origin="codex",
                machine_id="machine-test",
                target_identity="doi:10.1234/date-only",
                idempotency_key="idem-date-only",
                payload={"title": "Paper"},
                created=datetime.fromisoformat("2026-07-10"),
            )

    def test_recent_loader_filters_by_cutoff(self) -> None:
        old = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="query:old",
            idempotency_key="idem-old",
            payload={"query": "old event"},
            created=datetime(2026, 7, 8, 12, 30, tzinfo=timezone.utc),
            nonce="old00001",
        )
        recent = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="query:cloud",
            idempotency_key="idem-recent",
            payload={"query": "cloud microphysics"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="recent001",
        )
        write_operational_event(self.workspace, old)
        write_operational_event(self.workspace, recent)

        loaded = load_recent_operational_events(
            self.workspace,
            since=datetime(2026, 7, 9, tzinfo=timezone.utc),
        )

        self.assertEqual([item["event_id"] for item in loaded], [recent.event_id])


if __name__ == "__main__":
    unittest.main()
