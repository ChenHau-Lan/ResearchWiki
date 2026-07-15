from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.capture import CaptureInput, classify_capture
from rkf.core import (
    Workspace,
    append_reading_event,
    create_source,
    load_reading_ledger,
    slugify,
)


class RKFCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.root.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-capture"\n'
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1"\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root, allow_internal_actions=True)
        activated = self.runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.status, "ok")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_uncertain_and_ordinary_coding_do_not_auto_capture(self) -> None:
        uncertain = classify_capture(CaptureInput(text="Maybe remember this", origin="codex"))
        coding = classify_capture(
            CaptureInput(text="Fix the CSS padding", origin="project:WebApp")
        )

        self.assertEqual(uncertain.level, "none")
        self.assertEqual(coding.level, "none")

        routed = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Uncertain",
                    "text": "Maybe remember this",
                    "origin": "codex",
                },
            )
        )
        self.assertEqual(routed.status, "not-applicable")
        self.assertEqual(routed.payload["error_code"], "RKF_CAPTURE_NOT_TRIGGERED")

    def test_sensitive_and_private_material_are_blocked(self) -> None:
        private_value = "/" + "Users/example/private.pdf"
        private = classify_capture(
            CaptureInput(text=f"Read paper at {private_value}", origin="codex")
        )
        sensitive = classify_capture(
            CaptureInput(text="API key secret for paper search", origin="codex")
        )

        self.assertEqual(private.level, "blocked")
        self.assertIn("private-path", private.reasons)
        self.assertEqual(sensitive.level, "blocked")
        self.assertIn("sensitive-material", sensitive.reasons)

    def test_every_persisted_capture_field_is_safety_checked(self) -> None:
        sensitive_note = classify_capture(
            CaptureInput(
                text="Find DOI 10.1234/safe.fields",
                origin="project:Demo",
                reader_note="access_token=do-not-store",
            )
        )
        private_origin = classify_capture(
            CaptureInput(
                text="Find DOI 10.1234/private.origin",
                origin="/private/research/session",
            )
        )
        personal_author = classify_capture(
            CaptureInput(
                text="Find DOI 10.1234/personal.author",
                origin="project:Demo",
                authors="Person <private@example.org>",
            )
        )

        self.assertIn("sensitive-material", sensitive_note.reasons)
        self.assertIn("private-path", private_origin.reasons)
        self.assertIn("personal-data", personal_author.reasons)

        blocked = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Unsafe note",
                    "text": "Find DOI 10.1234/unsafe.note",
                    "origin": "project:Demo",
                    "agent_note": "password: do-not-store",
                },
            )
        )
        self.assertEqual(blocked.status, "blocked")
        self.assertFalse((self.root / "state" / "events").exists())

    def test_external_gpt_source_is_explicitly_provenanced_and_retrievable(self) -> None:
        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "External GPT paper lead",
                    "text": "Short summary for DOI 10.1234/external.gpt",
                    "origin": "external-gpt",
                    "doi": "10.1234/external.gpt",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["promotion"], "none")
        self.assertEqual(result.payload["materialization"], "queued")
        event_path = self.root / result.payload["event_path"]
        event = json.loads(event_path.read_text(encoding="utf-8"))
        self.assertEqual(event["origin"], "external-gpt")

        found = self.runtime.execute(
            ActionRequest(
                action="query.search",
                params={"query": "10.1234/external.gpt"},
            )
        )
        event_card = next(
            card for card in found.payload["cards"] if card["type"] == "event"
        )
        self.assertEqual(event_card["evidence_use"], "proposal-only")

    def test_existing_doi_is_recorded_without_duplicate_projection(self) -> None:
        create_source(
            self.workspace,
            kind="doi",
            value="10.1234/existing",
            title="Existing Paper",
            topic_id="",
            note="",
        )

        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Existing Paper",
                    "text": "A repeated DOI 10.1234/existing lead",
                    "origin": "project:Demo",
                    "doi": "10.1234/existing",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.payload["dedupe_status"], "existing")
        self.assertEqual(result.payload["materialization"], "not-needed")

    def test_canonical_url_and_ambiguous_title_do_not_silently_merge(self) -> None:
        create_source(
            self.workspace,
            kind="url",
            value="https://example.org/paper?a=1",
            title="Shared Paper Title",
            topic_id="",
            note="",
        )

        url_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "URL repeat",
                    "text": "Paper source URL",
                    "origin": "project:Demo",
                    "source_url": "https://EXAMPLE.org/paper?utm_source=chat&a=1#abstract",
                    "intent": "paper-search",
                },
            )
        )
        title_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Shared Paper Title",
                    "text": "Find this paper title",
                    "origin": "project:Demo",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(url_result.payload["dedupe_status"], "existing")
        self.assertEqual(title_result.payload["dedupe_status"], "ambiguous")
        self.assertEqual(title_result.payload["materialization"], "not-needed")

    def test_doi_identity_is_derived_from_title_or_url_once(self) -> None:
        create_source(
            self.workspace,
            kind="doi",
            value="10.1234/title.only",
            title="Title DOI Paper",
            topic_id="",
            note="",
        )

        title_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Paper DOI 10.1234/title.only",
                    "text": "Literature source lead",
                    "origin": "project:Demo",
                    "intent": "paper-search",
                },
            )
        )
        url_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "URL DOI Paper",
                    "text": "Literature source lead",
                    "origin": "project:Demo",
                    "source_url": "https://doi.org/10.1234/url.only",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(title_result.payload["dedupe_status"], "existing")
        url_event = json.loads(
            (self.root / url_result.payload["event_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(url_event["payload"]["doi"], "10.1234/url.only")
        self.assertEqual(url_event["target_identity"], "doi:10.1234/url.only")

    def test_traditional_chinese_title_dedupe_is_not_empty(self) -> None:
        create_source(
            self.workspace,
            kind="url",
            value="https://example.org/zh-paper",
            title="臺灣雲微物理研究",
            topic_id="",
            note="",
        )

        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "臺灣雲微物理研究",
                    "text": "尋找這篇研究文獻",
                    "origin": "project:Demo",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.payload["dedupe_status"], "ambiguous")

    def test_same_capture_within_24_hours_is_idempotent(self) -> None:
        params = {
            "title": "Repeated cloud lead",
            "text": "Find DOI 10.1234/repeated.cloud",
            "origin": "project:Demo",
            "doi": "10.1234/repeated.cloud",
            "intent": "paper-search",
        }

        first = self.runtime.execute(ActionRequest(action="capture.route", params=params))
        second = self.runtime.execute(ActionRequest(action="capture.route", params=params))

        self.assertEqual(first.payload["dedupe_status"], "new")
        self.assertEqual(second.payload["dedupe_status"], "existing")

    def test_writer_materializes_inbox_and_hot_after_event(self) -> None:
        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-capture",'
            '"assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        text = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(
            text.replace("maintenance_writer = false", "maintenance_writer = true"),
            encoding="utf-8",
        )
        writer_runtime = RKFActionRuntime(
            workspace=Workspace(self.root),
            project_root=self.root,
            allow_internal_actions=True,
        )
        activated = writer_runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.payload["writer_role"], "designated")

        result = writer_runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "New cloud paper",
                    "text": "Find DOI 10.1234/new.cloud paper",
                    "origin": "project:Demo",
                    "doi": "10.1234/new.cloud",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.status, "ok", result)
        self.assertEqual(result.payload["materialization"], "materialized")
        self.assertTrue((self.root / "knowledge" / "inbox").exists())
        self.assertTrue((self.root / "hot.md").exists())
        self.assertTrue((self.root / "state" / "events").exists())

    def test_designated_writer_materializes_previously_queued_event_once(self) -> None:
        queued = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Queued cloud paper",
                    "text": "Find DOI 10.1234/queued.cloud paper",
                    "origin": "project:Demo",
                    "doi": "10.1234/queued.cloud",
                    "intent": "paper-search",
                },
            )
        )
        self.assertEqual(queued.status, "ok", queued)
        self.assertEqual(queued.payload["materialization"], "queued")

        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-capture",'
            '"assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        config = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(
            config.replace("maintenance_writer = false", "maintenance_writer = true"),
            encoding="utf-8",
        )
        writer = RKFActionRuntime(workspace=Workspace(self.root), project_root=self.root, allow_internal_actions=True)
        writer.execute(ActionRequest(action="rkf.activate"))

        projection_dir = self.root / "state" / "sync" / "projections"
        projection_dir.mkdir(parents=True, exist_ok=True)
        stale_lock = projection_dir / f"{queued.payload['event_id']}.lock"
        stale_lock.write_text("stale file; no live OS lock\n", encoding="utf-8")

        partial_inbox = (
            self.root
            / "knowledge"
            / "inbox"
            / f"{slugify(queued.payload['event_id'], 120)}.md"
        )
        partial_inbox.parent.mkdir(parents=True, exist_ok=True)
        partial_inbox.write_text(
            "---\n"
            "type: inbox\n"
            f"projection_event_id: {queued.payload['event_id']}\n"
            "projection_complete: false\n"
            "---\n# Partial projection\n",
            encoding="utf-8",
        )
        reading_key = f"{queued.payload['event_id']}:inbox-injection"
        append_reading_event(
            Workspace(self.root),
            source_id="doi_10_1234_queued_cloud",
            event_type="inbox-injection",
            summary="Simulated crash after ledger persistence.",
            idempotency_key=reading_key,
        )

        first = writer.execute(ActionRequest(action="capture.project_pending"))
        inbox_count = len(list((self.root / "knowledge" / "inbox").glob("*.md")))
        checkpoint = self.root / "state" / "sync" / "projections" / f"{queued.payload['event_id']}.json"
        checkpoint.unlink()
        second = writer.execute(ActionRequest(action="capture.project_pending"))
        third = writer.execute(ActionRequest(action="capture.project_pending"))

        self.assertEqual(first.status, "ok")
        self.assertEqual(first.payload["events_materialized"], 1)
        self.assertEqual(second.payload["events_materialized"], 1)
        self.assertEqual(third.payload["events_materialized"], 0)
        self.assertEqual(len(list((self.root / "knowledge" / "inbox").glob("*.md"))), inbox_count)
        hot_records = [
            line
            for line in (self.root / "hot.md").read_text(encoding="utf-8").splitlines()
            if "origin=project:Demo" in line
            and 'query="Find DOI 10.1234/queued.cloud paper"' in line
        ]
        self.assertEqual(len(hot_records), 1)
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(state["completed_targets"], ["hot", "inbox"])
        completed_text = partial_inbox.read_text(encoding="utf-8")
        self.assertIn("projection_complete: true", completed_text)
        self.assertTrue((self.root / "knowledge" / "papers" / "doi_10_1234_queued_cloud.md").exists())
        ledger = load_reading_ledger(Workspace(self.root), "doi_10_1234_queued_cloud")
        matching = [
            event
            for event in ledger["events"]
            if event.get("idempotency_key") == reading_key
        ]
        self.assertEqual(len(matching), 1)


if __name__ == "__main__":
    unittest.main()
