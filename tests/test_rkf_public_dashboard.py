from __future__ import annotations

import io
import json
import re
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.core import PAPER_READING_STATUSES, Workspace, record_hot_query
from rkf.discovery import mark_candidates_accepted, preview_discovery, record_discovery_run
from rkf.session import SessionMode
from rkf.public_dashboard import (
    DashboardSafetyError,
    REVIEW_STATIC_FILES,
    _snapshot_digest,
    build_public_snapshot,
    dashboard_preview_root,
    load_dashboard_preview,
    preview_public_dashboard,
    publish_public_dashboard,
    render_dashboard_preview,
    validate_site_publication,
    validate_public_snapshot,
)
from tools.build_public_dashboard import main as dashboard_main


REPO_ROOT = Path(__file__).resolve().parents[1]


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class RKFPublicDashboardTests(unittest.TestCase):
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
            f'raw_root = "{self.raw.as_posix()}"\n'
            f'private_evidence_root = "{(self.root / "evidence").as_posix()}"\n\n'
            "[machine]\n"
            'id = "machine-dashboard-secret"\n'
            "maintenance_writer = true\n\n"
            "[sync]\n"
            'writer_registry = "state/sync/maintenance-writer.json"\n'
            "aggregate_cadence_hours = 24\n\n"
            "[gates]\n"
            "require_pdf_checkpoint = true\n"
            "require_pdf_qc = true\n"
            "require_claim_support = true\n"
            "require_synthesis_review = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1.1"\n'
            'default_review_cadence = "monthly"\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.repo)
        self.workspace.ensure_base()
        (self.root / "evidence").mkdir()
        (self.wiki / "state" / "sync" / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-dashboard-secret",'
            '"assigned_at":"2026-07-13T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (self.wiki / "governance" / "topic_registry.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-topic-registry-v1",
                    "updated": date.today().isoformat(),
                    "topics": [
                        {
                            "topic_id": "atmospheric-dynamics",
                            "name": "Atmospheric Dynamics",
                            "scope": "Public scope",
                            "default_search_strings": ["private search phrase"],
                            "review_cadence": "monthly",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        record_hot_query(
            self.workspace,
            query="Hidden research question",
            topic_id="atmospheric-dynamics",
            origin="private-project",
            intent="discover",
            paper_leads=["Hidden paper lead"],
            notes="Hidden hot note",
            created=date.today().isoformat(),
        )
        (self.wiki / "state" / "sources" / "source-secret.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-source-record-v1",
                    "source_id": "source-secret",
                    "title": "Hidden Paper Title",
                    "status": "new",
                    "reading_state": "metadata-only",
                    "fulltext_status": "needs-user-pdf",
                    "topic_ids": ["atmospheric-dynamics"],
                }
            ),
            encoding="utf-8",
        )
        paper_dir = self.wiki / "knowledge" / "papers"
        paper_dir.mkdir(parents=True)
        (paper_dir / "secret-paper.md").write_text(
            "---\n"
            "type: paper\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "source_id: source-secret\n"
            "reading_status: metadata-only\n"
            "reading_state: metadata-only\n"
            "fulltext_status: needs-user-pdf\n"
            "human_feedback_level: none\n"
            "understanding_confidence: low\n"
            "claim_readiness: not-ready\n"
            "reading_ledger: state/reading/source-secret.json\n"
            "evidence_boundary: review-blocker\n"
            "topics:\n"
            "  - atmospheric-dynamics\n"
            f"created: {date.today().isoformat()}\n"
            f"updated: {date.today().isoformat()}\n"
            "sources: []\n"
            "---\n\n"
            "# Hidden Paper Title\n\nHidden article-derived note.\n",
            encoding="utf-8",
        )
        (self.wiki / "state" / "reading" / "source-secret.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-reading-ledger-v1",
                    "source_id": "source-secret",
                    "events": [{"summary": "Hidden reader note"}],
                }
            ),
            encoding="utf-8",
        )
        run_dir = self.wiki / "state" / "search_runs" / "secret-run"
        run_dir.mkdir(parents=True)
        (run_dir / "candidates.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-discovery-run-v1",
                    "query": "Hidden discovery query",
                    "topic_ids": ["atmospheric-dynamics"],
                    "live": False,
                    "gate": "candidates_are_not_evidence",
                    "created": "2026-07-13",
                    "candidates": [
                        {
                            "source_id": "candidate-secret",
                            "title": "Hidden Candidate Title",
                            "year": 2025,
                            "doi": "10.1000/hidden-one",
                            "evidence_role": "private fixture role",
                            "status": "metadata_ok",
                        },
                        {
                            "source_id": "candidate-secret-2",
                            "title": "Another Hidden Candidate",
                            "year": "2024",
                            "doi": "",
                            "evidence_role": "private fixture role",
                            "status": "metadata_ok",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install_site_assets(self) -> None:
        for relative in REVIEW_STATIC_FILES:
            source = REPO_ROOT / "site" / relative
            target = self.repo / "site" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    def test_build_is_read_only_and_contains_only_aggregate_content(self) -> None:
        before = file_snapshot(self.root)

        snapshot = build_public_snapshot(
            self.workspace,
            now=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(file_snapshot(self.root), before)
        validate_public_snapshot(snapshot)
        serialized = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        for private_value in (
            str(self.root),
            "machine-dashboard-secret",
            "Hidden research question",
            "Hidden Paper Title",
            "Hidden reader note",
            "source-secret",
            "candidate-secret",
            "Hidden abstract",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertEqual(snapshot["research_hotspots"][0]["topic_id"], "atmospheric-dynamics")
        self.assertEqual(snapshot["research_hotspots"][0]["demand_count"], 1)
        self.assertEqual(
            snapshot["registered_research_areas"],
            [{"topic_id": "atmospheric-dynamics", "name": "Atmospheric Dynamics"}],
        )
        self.assertEqual(snapshot["discovery"]["candidate_count"], 2)
        self.assertEqual(snapshot["discovery"]["decision_counts"]["other"], 2)
        self.assertEqual(snapshot["discovery"]["decision_counts"]["accepted"], 0)
        self.assertTrue(snapshot["safety"]["aggregate_only"])
        self.assertFalse(snapshot["safety"]["candidates_are_evidence"])

    def test_governed_discovery_and_acceptance_use_strict_loaders(self) -> None:
        preview = preview_discovery(
            self.workspace,
            query="public fixture query",
            topic_id="atmospheric-dynamics",
            provider_clients={
                "fixture": lambda _query, _limit: [
                    {
                        "title": "Public Fixture Candidate",
                        "authors": ["Public Author"],
                        "year": 2026,
                        "doi": "10.1000/public-fixture",
                        "url": "https://doi.org/10.1000/public-fixture",
                    }
                ]
            },
            generated_at="2026-07-13T12:00:00Z",
        )
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at="2026-07-13T12:01:00Z",
        )
        candidate_id = recorded["candidates"][0]["candidate_id"]
        mark_candidates_accepted(
            self.workspace,
            run_id=recorded["run_id"],
            candidate_ids=[candidate_id],
            accepted_at="2026-07-13T12:02:00Z",
        )

        snapshot = build_public_snapshot(self.workspace)

        self.assertEqual(snapshot["discovery"]["run_count"], 2)
        self.assertEqual(snapshot["discovery"]["candidate_count"], 3)
        self.assertEqual(snapshot["discovery"]["decision_counts"]["accepted"], 1)
        self.assertEqual(snapshot["discovery"]["decision_counts"]["other"], 2)

    def test_tampered_governed_acceptance_fails_dashboard_preview(self) -> None:
        preview = preview_discovery(
            self.workspace,
            query="tamper fixture query",
            provider_clients={
                "fixture": lambda _query, _limit: [
                    {"title": "Tamper Fixture Candidate", "year": 2026}
                ]
            },
            generated_at="2026-07-13T12:00:00Z",
        )
        recorded = record_discovery_run(
            self.workspace,
            preview=preview,
            expected_hash=preview["preview_hash"],
            recorded_at="2026-07-13T12:01:00Z",
        )
        acceptance_path = (
            self.workspace.paths.search_runs / recorded["run_id"] / "acceptance.json"
        )
        acceptance_path.write_text(
            json.dumps(
                {
                    "schema": "rkf-discovery-acceptance-v1",
                    "run_id": recorded["run_id"],
                    "preview_hash": recorded["preview_hash"],
                    "updated_at": "2026-07-13T12:02:00Z",
                    "accepted": [
                        {
                            "candidate_id": recorded["candidates"][0]["candidate_id"],
                            "accepted_at": "2026-07-13T12:02:00Z",
                            "actor": "human",
                            "untrusted": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(DashboardSafetyError, "governed discovery state"):
            build_public_snapshot(self.workspace)

    def test_suspicious_topic_label_falls_back_to_public_topic_id(self) -> None:
        registry_path = self.wiki / "governance" / "topic_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["topics"][0]["name"] = str(self.root / "private-topic-name")
        registry_path.write_text(json.dumps(registry), encoding="utf-8")

        snapshot = build_public_snapshot(self.workspace)

        self.assertEqual(snapshot["research_hotspots"][0]["name"], "atmospheric-dynamics")
        self.assertEqual(snapshot["registered_research_areas"][0]["name"], "atmospheric-dynamics")

    def test_registered_areas_remain_distinct_when_recent_demand_is_empty(self) -> None:
        self.workspace.paths.hot_md.write_text("# Hot Research Questions\n", encoding="utf-8")

        snapshot = build_public_snapshot(self.workspace)

        self.assertEqual(snapshot["research_hotspots"], [])
        self.assertEqual(
            snapshot["registered_research_areas"],
            [{"topic_id": "atmospheric-dynamics", "name": "Atmospheric Dynamics"}],
        )
        self.assertEqual(snapshot["demand"]["event_count"], 0)

    def test_unknown_topic_ids_remain_untriaged_demand(self) -> None:
        record_hot_query(
            self.workspace,
            query="Demand linked to a retired topic",
            topic_id="retired-topic",
            origin="private-project",
            intent="discover",
            created=date.today().isoformat(),
        )

        snapshot = build_public_snapshot(self.workspace)

        self.assertEqual(snapshot["demand"]["event_count"], 2)
        self.assertEqual(snapshot["demand"]["topic_linked_event_count"], 1)
        self.assertEqual(snapshot["demand"]["untriaged_event_count"], 1)
        self.assertEqual(
            snapshot["research_hotspots"],
            [
                {
                    "topic_id": "atmospheric-dynamics",
                    "name": "Atmospheric Dynamics",
                    "demand_count": 1,
                }
            ],
        )

    def test_registered_areas_are_deterministic_and_capped(self) -> None:
        registry_path = self.wiki / "governance" / "topic_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["topics"] = [
            {
                "topic_id": f"area-{index:02d}",
                "name": f"Research Area {index:02d}",
                "scope": "Public scope",
                "default_search_strings": [],
                "review_cadence": "monthly",
            }
            for index in range(14)
        ]
        registry_path.write_text(json.dumps(registry), encoding="utf-8")

        snapshot = build_public_snapshot(self.workspace)

        self.assertEqual(len(snapshot["registered_research_areas"]), 12)
        self.assertEqual(snapshot["registered_research_areas"][0]["topic_id"], "area-00")
        self.assertEqual(snapshot["registered_research_areas"][-1]["topic_id"], "area-11")

    def test_preview_writes_only_to_private_dashboard_directory(self) -> None:
        before = file_snapshot(self.root)
        result = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 12, 30, tzinfo=timezone.utc),
        )

        after = file_snapshot(self.root)
        new_files = set(after) - set(before)
        expected_prefix = f"repo/.rkf_private/dashboard_previews/{result['preview_id']}/"
        self.assertEqual(
            new_files,
            {expected_prefix + "manifest.json", expected_prefix + "snapshot.json"},
        )
        self.assertTrue(result["paths_redacted"])
        self.assertNotIn(str(self.root), json.dumps(result))
        snapshot, manifest = load_dashboard_preview(self.workspace, result["preview_id"])
        self.assertEqual(snapshot["snapshot_hash"], result["snapshot_hash"])
        self.assertEqual(manifest["snapshot_file"], "snapshot.json")

    def test_preview_loader_requires_exact_pending_review_envelope(self) -> None:
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 12, 40, tzinfo=timezone.utc),
        )
        preview_dir = dashboard_preview_root(self.workspace) / preview["preview_id"]
        snapshot_path = preview_dir / "snapshot.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["publication"] = {
            "status": "synthetic-preview",
            "approved_snapshot_hash": "",
            "published_at": "",
        }
        validate_public_snapshot(snapshot)
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(DashboardSafetyError, "does not match"):
            load_dashboard_preview(self.workspace, preview["preview_id"])

    def test_preview_loader_rejects_extra_manifest_fields(self) -> None:
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 12, 50, tzinfo=timezone.utc),
        )
        manifest_path = (
            dashboard_preview_root(self.workspace)
            / preview["preview_id"]
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["path"] = "private-value"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(DashboardSafetyError, "does not match"):
            load_dashboard_preview(self.workspace, preview["preview_id"])

    def test_publish_requires_exact_hash_and_replaces_only_site_snapshot(self) -> None:
        site_data = self.repo / "site" / "data"
        site_data.mkdir(parents=True)
        target = site_data / "rkf-public-snapshot.json"
        target.write_text('{"sentinel":true}\n', encoding="utf-8")
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 0, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(DashboardSafetyError, "does not match"):
            publish_public_dashboard(
                self.workspace,
                preview_id=preview["preview_id"],
                approved_snapshot_hash="f" * 64,
            )
        self.assertEqual(target.read_text(encoding="utf-8"), '{"sentinel":true}\n')

        result = publish_public_dashboard(
            self.workspace,
            preview_id=preview["preview_id"],
            approved_snapshot_hash=preview["snapshot_hash"],
            now=datetime(2026, 7, 13, 13, 5, tzinfo=timezone.utc),
        )

        published = json.loads(target.read_text(encoding="utf-8"))
        validate_public_snapshot(published)
        self.assertEqual(result["publication_status"], "published")
        self.assertEqual(published["snapshot_hash"], preview["snapshot_hash"])
        self.assertEqual(published["publication"]["approved_snapshot_hash"], preview["snapshot_hash"])

    def test_private_review_bundle_is_self_contained_idempotent_and_nonpublishing(self) -> None:
        self.install_site_assets()
        site_snapshot = self.repo / "site" / "data" / "rkf-public-snapshot.json"
        site_snapshot.parent.mkdir(parents=True, exist_ok=True)
        site_snapshot.write_text('{"sentinel":true}\n', encoding="utf-8")
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 10, tzinfo=timezone.utc),
        )
        preview_root = dashboard_preview_root(self.workspace) / preview["preview_id"]
        source_preview = {
            name: (preview_root / name).read_bytes()
            for name in ("snapshot.json", "manifest.json")
        }
        canonical_site = file_snapshot(self.repo / "site")

        rendered = render_dashboard_preview(
            self.workspace,
            preview_id=preview["preview_id"],
        )
        review_root = (
            dashboard_preview_root(self.workspace)
            / preview["preview_id"]
            / "review"
        )
        before_retry = file_snapshot(review_root)
        repeated = render_dashboard_preview(
            self.workspace,
            preview_id=preview["preview_id"],
        )

        self.assertEqual(rendered["review_status"], "rendered")
        self.assertEqual(repeated["review_status"], "already-rendered")
        self.assertTrue(rendered["self_contained"])
        self.assertTrue(rendered["paths_redacted"])
        self.assertNotIn(str(self.root), json.dumps(rendered))
        self.assertEqual(file_snapshot(review_root), before_retry)
        self.assertEqual(file_snapshot(self.repo / "site"), canonical_site)
        self.assertEqual(
            {
                name: (preview_root / name).read_bytes()
                for name in ("snapshot.json", "manifest.json")
            },
            source_preview,
        )
        self.assertEqual(site_snapshot.read_text(encoding="utf-8"), '{"sentinel":true}\n')
        index = (review_root / "index.html").read_text(encoding="utf-8")
        guide = (review_root / "getting-started.html").read_text(encoding="utf-8")
        script = (review_root / "assets" / "app.js").read_text(encoding="utf-8")
        review_snapshot = json.loads(
            (review_root / "data" / "rkf-public-snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("PRIVATE REVIEW · NOT PUBLISHED", index)
        self.assertIn("PRIVATE REVIEW · NOT PUBLISHED", guide)
        self.assertIn("noindex,nofollow,noarchive", index)
        self.assertIn("noindex,nofollow,noarchive", guide)
        self.assertIn("__RKF_PRIVATE_REVIEW_SNAPSHOT__", script)
        self.assertIn("const snapshotRequest = embeddedReviewSnapshot", script)
        self.assertIn("Promise.resolve(embeddedReviewSnapshot)", script)
        self.assertIn(preview["snapshot_hash"], script)
        self.assertEqual(review_snapshot["snapshot_hash"], preview["snapshot_hash"])
        self.assertEqual(review_snapshot["publication"]["status"], "pending-review")
        self.assertEqual(
            set(before_retry),
            {
                "assets/app.js",
                "assets/styles.css",
                "data/rkf-public-snapshot.json",
                "favicon.svg",
                "getting-started.html",
                "index.html",
                "review-manifest.json",
            },
        )
        for path in review_root.rglob("*"):
            expected_mode = 0o700 if path.is_dir() else 0o600
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), expected_mode)
        self.assertEqual(stat.S_IMODE(review_root.stat().st_mode), 0o700)

    def test_private_review_bundle_fails_closed_after_asset_tampering(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 20, tzinfo=timezone.utc),
        )
        render_dashboard_preview(self.workspace, preview_id=preview["preview_id"])
        review_root = (
            dashboard_preview_root(self.workspace)
            / preview["preview_id"]
            / "review"
        )
        (review_root / "assets" / "app.js").write_text(
            "tampered\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(DashboardSafetyError, "checksum does not match"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

    def test_private_review_bundle_rejects_extra_file(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 25, tzinfo=timezone.utc),
        )
        render_dashboard_preview(self.workspace, preview_id=preview["preview_id"])
        review_root = (
            dashboard_preview_root(self.workspace)
            / preview["preview_id"]
            / "review"
        )
        extra = review_root / "unexpected.txt"
        extra.write_text("unexpected\n", encoding="utf-8")
        extra.chmod(0o600)

        with self.assertRaisesRegex(DashboardSafetyError, "tree is not exact"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

    def test_private_review_validation_failure_never_creates_final_review(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 27, tzinfo=timezone.utc),
        )
        preview_root = dashboard_preview_root(self.workspace) / preview["preview_id"]
        original_validator = __import__(
            "rkf.public_dashboard",
            fromlist=["_validate_review_bundle"],
        )._validate_review_bundle

        def reject_build(root: Path, *, preview_id: str, snapshot_hash: str):
            if root.name.startswith(".review-build-"):
                raise DashboardSafetyError("injected pre-rename validation failure")
            return original_validator(
                root,
                preview_id=preview_id,
                snapshot_hash=snapshot_hash,
            )

        with patch("rkf.public_dashboard._validate_review_bundle", side_effect=reject_build):
            with self.assertRaisesRegex(DashboardSafetyError, "injected pre-rename"):
                render_dashboard_preview(
                    self.workspace,
                    preview_id=preview["preview_id"],
                )

        self.assertFalse((preview_root / "review").exists())

    def test_private_review_refuses_symlinked_source_assets(self) -> None:
        self.install_site_assets()
        assets = self.repo / "site" / "assets"
        for child in assets.iterdir():
            child.unlink()
        assets.rmdir()
        external = self.root / "external-assets"
        external.mkdir()
        assets.symlink_to(external, target_is_directory=True)
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 28, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(DashboardSafetyError, "symlink|escapes"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

        self.assertEqual(list(external.iterdir()), [])

    def test_private_review_refuses_in_root_source_file_symlink(self) -> None:
        self.install_site_assets()
        app = self.repo / "site" / "assets" / "app.js"
        app.unlink()
        app.symlink_to(self.repo / "site" / "assets" / "styles.css")
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 28, 30, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(DashboardSafetyError, "symlink"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

    def test_private_review_refuses_symlinked_destination(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 29, tzinfo=timezone.utc),
        )
        preview_root = dashboard_preview_root(self.workspace) / preview["preview_id"]
        external = self.root / "external-review"
        external.mkdir()
        (preview_root / "review").symlink_to(external, target_is_directory=True)

        with self.assertRaisesRegex(DashboardSafetyError, "symlink|escapes"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

        self.assertEqual(list(external.iterdir()), [])

    def test_private_review_refuses_in_root_destination_symlink(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 29, 30, tzinfo=timezone.utc),
        )
        preview_root = dashboard_preview_root(self.workspace) / preview["preview_id"]
        internal = preview_root / "inside-target"
        internal.mkdir()
        (preview_root / "review").symlink_to(internal, target_is_directory=True)

        with self.assertRaisesRegex(DashboardSafetyError, "symlink"):
            render_dashboard_preview(
                self.workspace,
                preview_id=preview["preview_id"],
            )

        self.assertEqual(list(internal.iterdir()), [])

    def test_dashboard_actions_require_activation_and_exact_hash(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.repo, allow_internal_actions=True)
        before = file_snapshot(self.root)

        blocked = runtime.execute(ActionRequest(action="dashboard.preview"))

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(file_snapshot(self.root), before)

        activated = runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.status, "ok")
        preview = runtime.execute(
            ActionRequest(action="dashboard.preview", params={"window_days": 30})
        )
        self.assertEqual(preview.status, "ok")
        self.assertTrue(preview.payload["paths_redacted"])
        self.install_site_assets()
        reviewed = runtime.execute(
            ActionRequest(
                action="dashboard.review",
                params={"preview_id": preview.payload["preview_id"]},
            )
        )
        self.assertEqual(reviewed.status, "ok")
        self.assertEqual(reviewed.payload["review_status"], "rendered")
        self.assertEqual(reviewed.payload["publication_status"], "pending-review")

        site_data = self.repo / "site" / "data"
        site_data.mkdir(parents=True, exist_ok=True)
        target = site_data / "rkf-public-snapshot.json"
        target.write_text('{"sentinel":true}\n', encoding="utf-8")
        runtime.session.mode = SessionMode.ACTIVE_READ_ONLY
        mismatch = runtime.execute(
            ActionRequest(
                action="dashboard.publish",
                params={
                    "preview_id": preview.payload["preview_id"],
                    "snapshot_hash": "f" * 64,
                },
            )
        )
        self.assertEqual(mismatch.status, "blocked")
        self.assertEqual(target.read_text(encoding="utf-8"), '{"sentinel":true}\n')

        published = runtime.execute(
            ActionRequest(
                action="dashboard.publish",
                params={
                    "preview_id": preview.payload["preview_id"],
                    "snapshot_hash": preview.payload["snapshot_hash"],
                },
            )
        )
        self.assertEqual(published.status, "ok")
        self.assertEqual(published.payload["publication_status"], "published")
        published_snapshot = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(published_snapshot["publication"]["status"], "published")

    def test_invalid_preview_identifier_cannot_escape_private_root(self) -> None:
        with self.assertRaisesRegex(DashboardSafetyError, "preview_id"):
            load_dashboard_preview(self.workspace, "../site")
        self.assertEqual(
            dashboard_preview_root(self.workspace),
            (self.repo / ".rkf_private" / "dashboard_previews").resolve(),
        )

    def test_preview_refuses_symlinked_private_root(self) -> None:
        external = self.root / "external-private"
        external.mkdir()
        (self.repo / ".rkf_private").symlink_to(external, target_is_directory=True)

        with self.assertRaisesRegex(DashboardSafetyError, "must not be a symlink"):
            preview_public_dashboard(self.workspace)

        self.assertEqual(list(external.iterdir()), [])

    def test_publish_refuses_symlinked_site_data_root(self) -> None:
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 13, 30, tzinfo=timezone.utc),
        )
        site = self.repo / "site"
        site.mkdir()
        external = self.root / "external-site-data"
        external.mkdir()
        (site / "data").symlink_to(external, target_is_directory=True)

        with self.assertRaisesRegex(DashboardSafetyError, "must not be a symlink"):
            publish_public_dashboard(
                self.workspace,
                preview_id=preview["preview_id"],
                approved_snapshot_hash=preview["snapshot_hash"],
            )

        self.assertEqual(list(external.iterdir()), [])

    def test_validator_rejects_nested_field_even_with_recalculated_hash(self) -> None:
        snapshot = build_public_snapshot(self.workspace)
        snapshot["demand"]["raw_query"] = "not allowlisted"
        snapshot["snapshot_hash"] = _snapshot_digest(snapshot)

        with self.assertRaisesRegex(DashboardSafetyError, "unallowlisted"):
            validate_public_snapshot(snapshot)

    def test_validator_rejects_registered_area_identity_field(self) -> None:
        snapshot = build_public_snapshot(self.workspace)
        snapshot["registered_research_areas"][0]["source_id"] = "not-public"
        snapshot["snapshot_hash"] = _snapshot_digest(snapshot)

        with self.assertRaisesRegex(DashboardSafetyError, "unallowlisted"):
            validate_public_snapshot(snapshot)

    def test_committed_site_is_relative_dependency_free_and_publishable(self) -> None:
        snapshot_path = REPO_ROOT / "site" / "data" / "rkf-public-snapshot.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schema"], "rkf-public-demo-v1")
        self.assertEqual(snapshot["status"], "published")
        self.assertTrue(snapshot["quality"]["synthetic"])
        self.assertFalse(snapshot["quality"]["project_activity_published"])

        html = (REPO_ROOT / "site" / "index.html").read_text(encoding="utf-8")
        script = (REPO_ROOT / "site" / "assets" / "app.js").read_text(encoding="utf-8")
        guide_path = REPO_ROOT / "site" / "getting-started.html"
        guide = guide_path.read_text(encoding="utf-8")
        self.assertIn('href="./assets/styles.css"', html)
        self.assertIn('href="./favicon.svg"', html)
        self.assertIn('href="./getting-started.html"', html)
        self.assertNotIn("ResearchWiki/blob/main/docs/GETTING_STARTED", html)
        self.assertTrue((REPO_ROOT / "site" / "favicon.svg").is_file())
        self.assertTrue(guide_path.is_file())
        self.assertIn('src="./assets/app.js"', html)
        self.assertIn('./data/rkf-public-snapshot.json', script)
        self.assertIn("locator_coverage_pct", script)
        self.assertNotIn("writer_role", script)
        self.assertNotIn("candidate_count", script)
        self.assertIn("mobile-nav", html)
        self.assertIn("publication gate not satisfied", script)
        self.assertIn("python3 tools/bootstrap_rkf.py", guide)
        self.assertIn("connect-project", guide)
        self.assertIn("Candidate metadata 與 model output 不是 stable Evidence", guide)
        self.assertIn("workflow.add", guide)
        self.assertIn("workflow.review", guide)
        self.assertNotIn("topic registry 一開始是空的", guide)
        self.assertNotIn("根據目前 topics", guide)
        self.assertNotRegex(html, r'<script[^>]+src=["\']https?://')
        self.assertNotRegex(html, r'<link[^>]+href=["\']https?://')
        self.assertNotRegex(guide, r'<script[^>]+src=["\']https?://')
        self.assertNotRegex(guide, r'<link[^>]+href=["\']https?://')

        validated = validate_site_publication(REPO_ROOT)
        self.assertEqual(validated["publication_status"], "published")
        self.assertEqual(validated["schema"], "rkf-demo-deployment-validation-v1")

    def test_deployment_validator_requires_published_exact_snapshot(self) -> None:
        site_data = self.repo / "site" / "data"
        site_data.mkdir(parents=True)
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc),
        )
        publish_public_dashboard(
            self.workspace,
            preview_id=preview["preview_id"],
            approved_snapshot_hash=preview["snapshot_hash"],
        )

        result = validate_site_publication(self.repo)

        self.assertEqual(result["publication_status"], "published")
        self.assertEqual(result["snapshot_hash"], preview["snapshot_hash"])

    def test_wrapper_rejects_synthetic_snapshot_for_deployment(self) -> None:
        site_data = self.repo / "site" / "data"
        site_data.mkdir(parents=True)
        synthetic = build_public_snapshot(self.workspace)
        (site_data / "rkf-public-snapshot.json").write_text(
            json.dumps(synthetic, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output = io.StringIO()

        with redirect_stdout(output):
            return_code = dashboard_main(
                ["--repo-root", str(self.repo), "validate-publication"]
            )

        receipt = json.loads(output.getvalue())
        self.assertEqual(return_code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertNotIn(str(self.root), output.getvalue())

    def test_schema_is_closed_at_every_public_object_boundary(self) -> None:
        schema = json.loads((REPO_ROOT / "schemas" / "rkf_public_dashboard.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        for key in ("publication", "freshness", "demand", "discovery", "paper_pipeline", "knowledge", "graph", "framework", "health", "safety"):
            self.assertFalse(schema["properties"][key]["additionalProperties"])
        self.assertFalse(schema["properties"]["research_hotspots"]["items"]["additionalProperties"])
        self.assertFalse(schema["properties"]["registered_research_areas"]["items"]["additionalProperties"])
        self.assertIn("registered_research_areas", schema["required"])

    def test_pages_template_validates_publication_before_upload(self) -> None:
        validator = "python3 tools/build_public_dashboard.py validate-publication"
        for path in (
            REPO_ROOT / "docs" / "workflows" / "github-pages-rkf-dashboard.example.yml",
            REPO_ROOT / ".github" / "workflows" / "pages.yml",
        ):
            workflow = path.read_text(encoding="utf-8")
            upload_match = re.search(r"actions/upload-pages-artifact@v[0-9]+", workflow)
            self.assertIn(validator, workflow)
            self.assertIsNotNone(upload_match)
            self.assertLess(workflow.index(validator), upload_match.start())

    def test_wrapper_returns_path_redacted_preview_receipt(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = dashboard_main(["--repo-root", str(self.repo), "preview", "--window-days", "30"])

        receipt = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertTrue(receipt["paths_redacted"])
        self.assertEqual(receipt["publication_status"], "pending-review")
        self.assertNotIn(str(self.root), output.getvalue())

    def test_wrapper_returns_path_redacted_private_review_receipt(self) -> None:
        self.install_site_assets()
        preview = preview_public_dashboard(
            self.workspace,
            now=datetime(2026, 7, 13, 14, 10, tzinfo=timezone.utc),
        )
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = dashboard_main(
                [
                    "--repo-root",
                    str(self.repo),
                    "review",
                    "--preview-id",
                    preview["preview_id"],
                ]
            )

        receipt = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(receipt["review_entry"], "review/index.html")
        self.assertEqual(receipt["publication_status"], "pending-review")
        self.assertTrue(receipt["self_contained"])
        self.assertTrue(receipt["paths_redacted"])
        self.assertNotIn(str(self.root), output.getvalue())

    def test_action_rejects_non_integer_window_without_exception(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.repo, allow_internal_actions=True)
        self.assertEqual(runtime.execute(ActionRequest(action="rkf.activate")).status, "ok")

        result = runtime.execute(
            ActionRequest(action="dashboard.preview", params={"window_days": "30"})
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.payload["error_code"], "RKF_DASHBOARD_INPUT_INVALID")


if __name__ == "__main__":
    unittest.main()
