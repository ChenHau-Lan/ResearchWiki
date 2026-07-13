from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import Workspace
from rkf.discovery import DiscoveryError, load_acceptance_state
from rkf.events import build_operational_event, write_operational_event


class RKFDiscoveryActionTests(unittest.TestCase):
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
            'id = "machine-discovery-actions"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n',
            encoding="utf-8",
        )
        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-discovery-actions",'
            '"assigned_at":"2026-07-13T12:00:00Z"}\n',
            encoding="utf-8",
        )
        governance = self.root / "governance"
        governance.mkdir()
        (governance / "topic_registry.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-topic-registry-v1",
                    "updated": "2026-07-13",
                    "topics": [
                        {
                            "topic_id": "cloud-microphysics",
                            "name": "Cloud Microphysics",
                            "scope": "Cloud microphysics research.",
                            "default_search_strings": [
                                "cloud microphysics observation parameterization"
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        activated = self.runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.status, "ok")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def radar_record(doi: str = "10.1234/discovery.action") -> dict[str, object]:
        return {
            "id": "radar-action-1",
            "title": "Observed Cloud Microphysics Candidate",
            "authors": ["Ada Researcher"],
            "published": "2025-01-02",
            "journal": "Journal of Cloud Studies",
            "doi": doi,
            "url": f"https://doi.org/{doi}",
            "interest_score": 0.9,
            "abstract": "must be stripped",
        }

    def preview(self, doi: str = "10.1234/discovery.action"):
        return self.runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={
                    "topic_id": "cloud-microphysics",
                    "providers": ["paper-radar"],
                    "paper_radar_records": [self.radar_record(doi)],
                },
            )
        )

    def record(self, preview_result):
        return self.runtime.execute(
            ActionRequest(
                action="discover.record",
                params={
                    "preview": preview_result.payload,
                    "preview_hash": preview_result.payload["preview_hash"],
                },
            )
        )

    def test_preview_requires_activation_and_does_not_write_run_state(self) -> None:
        fresh = RKFActionRuntime(workspace=self.workspace, project_root=self.root)

        blocked = fresh.execute(
            ActionRequest(
                action="discover.preview",
                params={
                    "query": "cloud microphysics",
                    "providers": ["paper-radar"],
                    "paper_radar_records": [self.radar_record()],
                },
            )
        )
        preview = self.preview()

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(preview.status, "ok")
        self.assertEqual(
            preview.payload["query"],
            "cloud microphysics observation parameterization",
        )
        self.assertEqual(preview.payload["candidate_count"], 1)
        self.assertFalse(self.workspace.paths.search_runs.exists())
        self.assertNotIn("abstract", json.dumps(preview.payload).lower())

    def test_preview_rejects_untyped_action_parameters_without_exception(self) -> None:
        invalid_limit = self.runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={"query": "cloud", "max_results": "20"},
            )
        )
        invalid_providers = self.runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={"query": "cloud", "providers": "crossref"},
            )
        )

        self.assertEqual(invalid_limit.status, "error")
        self.assertEqual(invalid_limit.payload["error_code"], "RKF_DISCOVERY_INPUT_INVALID")
        self.assertEqual(invalid_providers.status, "error")
        self.assertEqual(invalid_providers.payload["error_code"], "RKF_DISCOVERY_INPUT_INVALID")

    def test_record_requires_exact_hash_and_designated_writer(self) -> None:
        preview = self.preview()
        mismatch = self.runtime.execute(
            ActionRequest(
                action="discover.record",
                params={"preview": preview.payload, "preview_hash": "0" * 64},
            )
        )
        recorded = self.record(preview)

        self.assertEqual(mismatch.status, "blocked")
        self.assertEqual(mismatch.payload["error_code"], "RKF_DISCOVERY_RECORD_REJECTED")
        self.assertEqual(recorded.status, "ok")
        self.assertEqual(recorded.payload["candidate_count"], 1)
        self.assertTrue(
            (self.workspace.paths.search_runs / recorded.payload["run_id"] / "candidates.json").exists()
        )

    def test_accept_routes_candidate_to_source_and_inbox_without_paper_by_default(self) -> None:
        preview = self.preview()
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        accepted = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                },
            )
        )

        source_id = "doi_10_1234_discovery_action"
        self.assertEqual(accepted.status, "ok")
        self.assertEqual(accepted.payload["captured_count"], 1)
        self.assertFalse(accepted.payload["paper_drafts_requested"])
        self.assertTrue((self.root / "state" / "sources" / f"{source_id}.json").exists())
        self.assertTrue((self.root / "knowledge" / "inbox").exists())
        self.assertFalse((self.root / "knowledge" / "papers" / f"{source_id}.md").exists())
        state = load_acceptance_state(self.workspace, recorded.payload["run_id"])
        self.assertEqual(state["accepted"][0]["candidate_id"], candidate_id)

    def test_accept_can_explicitly_create_an_early_paper_draft(self) -> None:
        preview = self.preview(doi="10.1234/discovery.paper")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        accepted = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "create_paper_drafts": True,
                },
            )
        )

        self.assertEqual(accepted.status, "ok")
        self.assertTrue(
            (self.root / "knowledge" / "papers" / "doi_10_1234_discovery_paper.md").exists()
        )

    def test_automation_acceptance_cannot_create_paper_drafts(self) -> None:
        preview = self.preview(doi="10.1234/discovery.automation")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        result = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "create_paper_drafts": True,
                    "actor": "automation",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_DISCOVERY_AUTOMATION_POLICY")
        self.assertFalse((self.root / "knowledge" / "papers").exists())

    def test_automation_acceptance_requires_new_candidate_with_public_identity(self) -> None:
        preview = self.runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={
                    "query": "candidate without identifier",
                    "providers": ["paper-radar"],
                    "paper_radar_records": [
                        {
                            "id": "metadata-only",
                            "title": "Candidate Without Public Identifier",
                            "authors": ["Ada Researcher"],
                            "published": "2025",
                        }
                    ],
                },
            )
        )
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        result = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "actor": "automation",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_DISCOVERY_AUTOMATION_POLICY")

    def test_automation_rejects_nonpublic_landing_url(self) -> None:
        preview = self.runtime.execute(
            ActionRequest(
                action="discover.preview",
                params={
                    "query": "private host candidate",
                    "providers": ["paper-radar"],
                    "paper_radar_records": [
                        {
                            "id": "private-host",
                            "title": "Private Host Candidate",
                            "authors": ["Ada Researcher"],
                            "published": "2025",
                            "url": "http://127.0.0.1/internal-landing",
                        }
                    ],
                },
            )
        )
        self.assertEqual(preview.status, "ok")
        self.assertEqual(preview.payload["candidates"][0]["url"], "")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        result = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "actor": "automation",
                },
            )
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_DISCOVERY_AUTOMATION_POLICY")
        self.assertFalse(self.workspace.paths.events.exists())

    def test_successful_automation_acceptance_forwards_event_actor(self) -> None:
        preview = self.preview(doi="10.1234/discovery.actor")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]

        accepted = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "actor": "automation",
                },
            )
        )

        self.assertEqual(accepted.status, "ok")
        event_id = accepted.payload["route_receipts"][0]["event_id"]
        event_paths = list(self.workspace.paths.events.rglob(f"{event_id}.json"))
        self.assertEqual(len(event_paths), 1)
        event = json.loads(event_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(event["actor"], "automation")
        state = load_acceptance_state(self.workspace, recorded.payload["run_id"])
        self.assertEqual(state["accepted"][0]["actor"], "automation")

    def test_repeated_accept_is_idempotent_without_duplicate_capture_event(self) -> None:
        preview = self.preview(doi="10.1234/discovery.retry")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]
        request = ActionRequest(
            action="discover.accept",
            params={
                "run_id": recorded.payload["run_id"],
                "candidate_ids": [candidate_id],
            },
        )

        first = self.runtime.execute(request)
        event_count_before = len(list(self.workspace.paths.events.rglob("evt_*.json")))
        second = self.runtime.execute(request)
        event_count_after = len(list(self.workspace.paths.events.rglob("evt_*.json")))

        self.assertEqual(first.status, "ok")
        self.assertEqual(second.status, "ok")
        self.assertEqual(second.payload["captured_count"], 0)
        self.assertEqual(second.payload["already_accepted_count"], 1)
        self.assertEqual(second.payload["new_acceptance_count"], 0)
        self.assertEqual(second.payload["accepted_count"], 1)
        self.assertEqual(second.payload["route_receipts"][0]["status"], "already-accepted")
        self.assertEqual(event_count_after, event_count_before)

    def test_retry_recovers_capture_event_after_acceptance_sidecar_failure(self) -> None:
        preview = self.preview(doi="10.1234/discovery.crash-recovery")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]
        request = ActionRequest(
            action="discover.accept",
            params={
                "run_id": recorded.payload["run_id"],
                "candidate_ids": [candidate_id],
            },
        )

        with patch(
            "rkf.actions.mark_candidates_accepted",
            side_effect=OSError("simulated acceptance sidecar failure"),
        ):
            first = self.runtime.execute(request)

        event_paths_before = list(self.workspace.paths.events.rglob("evt_*.json"))
        event = json.loads(event_paths_before[0].read_text(encoding="utf-8"))
        expected_transaction_key = "discover.accept:" + hashlib.sha256(
            f"{recorded.payload['run_id']}\0{candidate_id}".encode("utf-8")
        ).hexdigest()
        retry_runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
        )
        self.assertEqual(
            retry_runtime.execute(ActionRequest(action="rkf.activate")).status,
            "ok",
        )
        second = retry_runtime.execute(request)
        event_paths_after = list(self.workspace.paths.events.rglob("evt_*.json"))

        self.assertEqual(first.status, "partial")
        self.assertEqual(
            first.payload["error_code"],
            "RKF_DISCOVERY_ACCEPT_STATE_FAILED",
        )
        self.assertEqual(len(event_paths_before), 1)
        self.assertEqual(event["idempotency_key"], expected_transaction_key)
        self.assertEqual(second.status, "ok")
        self.assertEqual(second.payload["captured_count"], 1)
        self.assertEqual(second.payload["new_acceptance_count"], 1)
        self.assertEqual(second.payload["transaction_recovered_count"], 1)
        self.assertTrue(
            second.payload["route_receipts"][0]["transaction_recovered"]
        )
        self.assertEqual(
            second.payload["route_receipts"][0]["event_id"],
            first.payload["route_receipts"][0]["event_id"],
        )
        self.assertEqual(event_paths_after, event_paths_before)
        acceptance = load_acceptance_state(
            self.workspace,
            recorded.payload["run_id"],
        )
        self.assertEqual(
            [item["candidate_id"] for item in acceptance["accepted"]],
            [candidate_id],
        )

    def test_retry_fails_closed_when_transaction_actor_changes(self) -> None:
        preview = self.preview(doi="10.1234/discovery.actor-conflict")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]
        human_request = ActionRequest(
            action="discover.accept",
            params={
                "run_id": recorded.payload["run_id"],
                "candidate_ids": [candidate_id],
                "actor": "human",
            },
        )

        with patch(
            "rkf.actions.mark_candidates_accepted",
            side_effect=DiscoveryError("simulated acceptance sidecar failure"),
        ):
            first = self.runtime.execute(human_request)
        event_count_before = len(list(self.workspace.paths.events.rglob("evt_*.json")))

        retry = self.runtime.execute(
            ActionRequest(
                action="discover.accept",
                params={
                    "run_id": recorded.payload["run_id"],
                    "candidate_ids": [candidate_id],
                    "actor": "automation",
                },
            )
        )

        self.assertEqual(first.status, "partial")
        self.assertEqual(retry.status, "blocked")
        self.assertEqual(
            retry.payload["error_code"],
            "RKF_DISCOVERY_ACCEPT_TRANSACTION_CONFLICT",
        )
        self.assertEqual(retry.payload["transaction_conflict_count"], 1)
        self.assertEqual(
            retry.payload["route_receipts"][0]["error_code"],
            "RKF_CAPTURE_TRANSACTION_CONFLICT",
        )
        self.assertEqual(
            len(list(self.workspace.paths.events.rglob("evt_*.json"))),
            event_count_before,
        )
        self.assertEqual(
            load_acceptance_state(
                self.workspace,
                recorded.payload["run_id"],
            )["accepted"],
            [],
        )

    def test_retry_fails_closed_on_duplicate_transaction_events(self) -> None:
        preview = self.preview(doi="10.1234/discovery.duplicate-transaction")
        recorded = self.record(preview)
        candidate_id = preview.payload["candidates"][0]["candidate_id"]
        request = ActionRequest(
            action="discover.accept",
            params={
                "run_id": recorded.payload["run_id"],
                "candidate_ids": [candidate_id],
            },
        )

        with patch(
            "rkf.actions.mark_candidates_accepted",
            side_effect=DiscoveryError("simulated acceptance sidecar failure"),
        ):
            first = self.runtime.execute(request)
        first_event_path = next(self.workspace.paths.events.rglob("evt_*.json"))
        first_event = json.loads(first_event_path.read_text(encoding="utf-8"))
        conflicting_payload = dict(first_event["payload"])
        conflicting_payload["title"] = "Conflicting transaction payload"
        duplicate = build_operational_event(
            action=first_event["action"],
            actor=first_event["actor"],
            origin=first_event["origin"],
            machine_id=first_event["machine_id"],
            target_identity=first_event["target_identity"],
            idempotency_key=first_event["idempotency_key"],
            payload=conflicting_payload,
        )
        write_operational_event(self.workspace, duplicate)

        retry = self.runtime.execute(request)

        self.assertEqual(first.status, "partial")
        self.assertEqual(retry.status, "blocked")
        self.assertEqual(
            retry.payload["error_code"],
            "RKF_DISCOVERY_ACCEPT_TRANSACTION_CONFLICT",
        )
        self.assertEqual(retry.payload["transaction_conflict_count"], 1)
        self.assertEqual(
            len(list(self.workspace.paths.events.rglob("evt_*.json"))),
            2,
        )
        self.assertEqual(
            load_acceptance_state(
                self.workspace,
                recorded.payload["run_id"],
            )["accepted"],
            [],
        )

    def test_non_writer_cannot_record_or_accept_discovery_candidates(self) -> None:
        preview = self.preview()
        self.runtime.session.writer_role = "other"

        blocked = self.runtime.execute(
            ActionRequest(
                action="discover.record",
                params={
                    "preview": preview.payload,
                    "preview_hash": preview.payload["preview_hash"],
                },
            )
        )

        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(blocked.payload["error_code"], "RKF_WRITER_REQUIRED")


if __name__ == "__main__":
    unittest.main()
