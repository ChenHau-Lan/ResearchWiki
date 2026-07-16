from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime, execute_action_request
from rkf.core import Workspace, create_paper_note, create_source, lint_knowledge_pages


class RKFActionsTests(unittest.TestCase):
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
            'id = "machine-actions"\n'
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            'schema_version = "rkf-v1"\n',
            encoding="utf-8",
        )
        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-actions",'
            '"assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root, allow_internal_actions=True)
        activated = self.runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.status, "ok")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_runtime_blocks_all_non_control_actions_before_io(self) -> None:
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root, allow_internal_actions=True)
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())

        result = runtime.execute(ActionRequest(action="world.render"))

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.payload["error_code"], "RKF_NOT_ACTIVE")

    def test_activate_status_and_deactivate_share_one_runtime(self) -> None:
        self.runtime.execute(ActionRequest(action="rkf.deactivate"))
        runtime = RKFActionRuntime(
            workspace=self.workspace,
            project_root=self.root,
            session_id="task-actions",
            allow_internal_actions=True,
        )

        activated = runtime.execute(ActionRequest(action="rkf.activate"))
        status = runtime.execute(ActionRequest(action="rkf.status"))
        deactivated = runtime.execute(ActionRequest(action="rkf.deactivate"))
        blocked = runtime.execute(ActionRequest(action="world.render"))

        self.assertEqual(activated.status, "ok")
        self.assertEqual(status.payload["mode"], "ACTIVE")
        self.assertEqual(status.payload["active_project_count"], 1)
        self.assertEqual(status.payload["open_activation_count"], 1)
        self.assertTrue(status.payload["active_projects"][0]["includes_current_task"])
        self.assertTrue(status.payload["active_projects"][0]["paths_redacted"])
        self.assertEqual(deactivated.payload["mode"], "OFF")
        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")

        after = runtime.execute(ActionRequest(action="rkf.status"))
        self.assertEqual(after.payload["active_project_count"], 0)
        self.assertEqual(after.payload["open_activation_count"], 0)

    def test_read_only_session_blocks_writes_but_allows_reads(self) -> None:
        (self.root / "paper.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
        runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root, allow_internal_actions=True)
        runtime.execute(ActionRequest(action="rkf.activate"))

        read_result = runtime.execute(ActionRequest(action="world.render"))
        write_result = runtime.execute(
            ActionRequest(
                action="hot.record",
                params={"query": "paper search", "origin": "codex"},
            )
        )

        self.assertEqual(read_result.status, "ok")
        self.assertEqual(write_result.status, "blocked")
        self.assertEqual(write_result.payload["error_code"], "RKF_READ_ONLY")

    def test_query_search_is_available_only_after_activation(self) -> None:
        self.seed_paper(doi="10.1234/query.action")
        fresh = RKFActionRuntime(workspace=self.workspace, project_root=self.root, allow_internal_actions=True)

        blocked = fresh.execute(
            ActionRequest(
                action="query.search",
                params={"query": "10.1234/query.action"},
            )
        )
        fresh.execute(ActionRequest(action="rkf.activate"))
        found = fresh.execute(
            ActionRequest(
                action="query.search",
                params={"query": "10.1234/query.action"},
            )
        )

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(found.status, "ok")
        self.assertGreaterEqual(found.payload["count"], 1)

    def test_paper_migration_preview_requires_activation_and_keeps_live_paper_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            base = Path(tmp_name)
            repo = base / "repo"
            wiki = base / "wiki"
            raw = base / "raw"
            repo.mkdir()
            wiki.mkdir()
            raw.mkdir()
            (repo / "rkf.workspace.toml").write_text(
                "[storage]\n"
                f'wiki_root = "{wiki.as_posix()}"\n'
                f'raw_root = "{raw.as_posix()}"\n\n'
                "[machine]\n"
                'id = "machine-preview"\n'
                "maintenance_writer = false\n\n"
                "[knowledge]\n"
                'schema_version = "rkf-v1.1"\n',
                encoding="utf-8",
            )
            workspace = Workspace(repo)
            record = create_source(
                workspace,
                kind="doi",
                value="10.1234/preview.action",
                title="Preview Action Paper",
            )
            paper_path = create_paper_note(workspace, record)
            before = paper_path.read_bytes()
            report_root = repo / ".rkf_private" / "migration_reports"
            runtime = RKFActionRuntime(workspace=workspace, project_root=repo, allow_internal_actions=True)

            blocked = runtime.execute(
                ActionRequest(
                    action="paper.migration.preview",
                    params={"report_root": str(report_root), "expected_count": 1},
                )
            )
            self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
            self.assertFalse(report_root.exists())

            runtime.execute(ActionRequest(action="rkf.activate"))
            preview = runtime.execute(
                ActionRequest(
                    action="paper.migration.preview",
                    params={"report_root": str(report_root), "expected_count": 1},
                )
            )

            self.assertEqual(preview.status, "ok")
            self.assertEqual(preview.payload["input_count"], 1)
            self.assertEqual(preview.payload["promotion"], "none")
            self.assertEqual(paper_path.read_bytes(), before)

    def seed_paper(self, *, doi: str = "10.1234/report.action") -> str:
        record = create_source(
            self.workspace,
            kind="doi",
            value=doi,
            title="Report Action Paper",
            topic_id="",
            note="",
        )
        create_paper_note(self.workspace, record)
        return str(record["source_id"])

    def seed_graph_paper(self, *, doi: str = "10.1234/graph.traversal") -> tuple[str, str, str]:
        topic_id = "cloud-microphysics"
        record = create_source(
            self.workspace,
            kind="doi",
            value=doi,
            title="Graph Traversal Paper",
            topic_id=topic_id,
            note="Public-safe graph traversal seed.",
        )
        create_paper_note(self.workspace, record)
        source_id = str(record["source_id"])
        paper_id = f"papers/{source_id}"
        return source_id, paper_id, topic_id

    def test_execute_inbox_capture_request_writes_inbox_and_guarded_source_links(self) -> None:
        request = ActionRequest(
            action="inbox.capture",
            params={
                "title": "Codex note on aerosol paper",
                "origin": "codex",
                "clip": "Short public-safe summary for DOI 10.1234/example.",
                "reader_note": "User project relation stays separate.",
                "doi": "10.1234/example",
            },
        )

        result = execute_action_request(request, runtime=self.runtime)

        self.assertEqual(result.action, "inbox.capture")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["source_id"], "doi_10_1234_example")
        self.assertTrue((self.root / "knowledge" / "inbox").exists())
        self.assertTrue((self.root / "state" / "sources" / "doi_10_1234_example.json").exists())
        self.assertTrue((self.root / "knowledge" / "papers" / "doi_10_1234_example.md").exists())

    def test_capture_route_can_accept_a_candidate_without_creating_paper_draft(self) -> None:
        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Candidate-only cloud paper",
                    "text": "Candidate metadata for DOI 10.1234/candidate.only.",
                    "origin": "discovery:crossref",
                    "doi": "10.1234/candidate.only",
                    "intent": "paper-search",
                    "topic_id": "cloud-microphysics",
                    "create_paper_draft": False,
                },
            )
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["materialization"], "materialized")
        source_id = "doi_10_1234_candidate_only"
        self.assertTrue((self.root / "state" / "sources" / f"{source_id}.json").exists())
        inbox_projection = next(
            item for item in result.payload["projections"] if item["action"] == "inbox.capture"
        )
        self.assertTrue((self.root / inbox_projection["payload"]["path"]).exists())
        self.assertFalse((self.root / "knowledge" / "papers" / f"{source_id}.md").exists())

    def test_new_paper_draft_uses_paper_centered_v1_1_sections(self) -> None:
        source_id = self.seed_paper(doi="10.1234/canonical.draft")
        paper_path = self.root / "knowledge" / "papers" / f"{source_id}.md"
        content = paper_path.read_text(encoding="utf-8")

        self.assertIn("schema: rkf-paper-v1.1", content)
        self.assertIn("## Research Question", content)
        self.assertIn("## Questions About This Paper", content)
        self.assertIn("## Intrinsic Links", content)
        self.assertNotIn("## Reader Notes", content)

    def test_v1_1_paper_lint_requires_matching_reading_status_and_sections(self) -> None:
        source_id = self.seed_paper(doi="10.1234/v11.lint")
        paper_path = self.root / "knowledge" / "papers" / f"{source_id}.md"
        paper_path.write_text(
            paper_path.read_text(encoding="utf-8")
            .replace("reading_status: metadata-only", "reading_status: abstract-read")
            .replace("## Intrinsic Links", "## Legacy Links"),
            encoding="utf-8",
        )

        errors = lint_knowledge_pages(self.workspace)

        self.assertIn(f"knowledge/papers/{source_id}.md: reading_status must equal reading_state", errors)
        self.assertIn(f"knowledge/papers/{source_id}.md: missing canonical paper section Intrinsic Links", errors)

    def test_execute_hot_record_request_refreshes_hot_dashboard(self) -> None:
        request = ActionRequest(
            action="hot.record",
            params={
                "query": "recent aerosol-cloud parameterization papers",
                "origin": "local",
                "intent": "paper-search",
                "topic_id": "aerosol-cloud",
            },
        )

        result = execute_action_request(request, runtime=self.runtime)

        self.assertEqual(result.action, "hot.record")
        self.assertEqual(result.status, "ok")
        self.assertIn("event_id", result.payload)
        hot_md = (self.root / "hot.md").read_text(encoding="utf-8")
        self.assertIn("recent aerosol-cloud parameterization papers", hot_md)
        self.assertIn("aerosol-cloud", hot_md)

    def test_report_actions_return_structured_payloads(self) -> None:
        source_id = self.seed_paper()

        world = execute_action_request(
            ActionRequest(action="world.render", params={"log_tail": 1}),
            runtime=self.runtime,
        )
        self.assertEqual(world.status, "ok")
        self.assertIn("RKF Workspace Status", world.payload["markdown"])
        self.assertEqual(world.payload["counts"]["sources"], 1)
        self.assertEqual(world.payload["counts"]["knowledge_pages"], 1)

        queue = execute_action_request(
            ActionRequest(action="paper.queue", params={"limit": 5}),
            runtime=self.runtime,
        )
        self.assertEqual(queue.status, "ok")
        self.assertEqual(queue.payload["count"], 1)
        self.assertEqual(queue.payload["items"][0]["source_id"], source_id)

        lint = execute_action_request(
            ActionRequest(action="lint.run", params={"mode": "all"}),
            runtime=self.runtime,
        )
        self.assertEqual(lint.status, "ok")
        self.assertTrue(lint.payload["passed"])
        self.assertEqual(lint.payload["errors"], [])

        graph = execute_action_request(
            ActionRequest(action="graph.export"),
            runtime=self.runtime,
        )
        self.assertEqual(graph.status, "ok")
        self.assertEqual(graph.payload["path"], "graph/research_graph.json")
        self.assertGreaterEqual(graph.payload["node_count"], 1)
        self.assertGreaterEqual(graph.payload["edge_count"], 1)

        index = execute_action_request(
            ActionRequest(action="index.generate"),
            runtime=self.runtime,
        )
        self.assertEqual(index.status, "ok")
        self.assertEqual(index.payload["path"], "index.md")
        self.assertTrue((self.root / "index.md").exists())

        handoff = execute_action_request(
            ActionRequest(action="codex_handoff.generate"),
            runtime=self.runtime,
        )
        self.assertEqual(handoff.status, "ok")
        self.assertEqual(handoff.payload["path"], "prompts/codex_handoff_context.md")
        self.assertTrue((self.root / "prompts" / "codex_handoff_context.md").exists())

    def test_connect_doctor_is_active_read_only_action(self) -> None:
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())

        result = self.runtime.execute(ActionRequest(action="connect.doctor"))

        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["status"], "ok")
        self.assertNotIn(str(self.root), str(result.payload))

    def test_doctor_blocker_degrades_an_active_runtime_to_read_only(self) -> None:
        (self.root / "late.sync-conflict.md").write_text("conflict\n", encoding="utf-8")

        doctor = self.runtime.execute(ActionRequest(action="connect.doctor"))
        write = self.runtime.execute(
            ActionRequest(action="hot.record", params={"query": "must not write", "origin": "codex"})
        )

        self.assertEqual(doctor.status, "blocked")
        self.assertEqual(self.runtime.session.mode.value, "ACTIVE_READ_ONLY")
        self.assertEqual(write.payload["error_code"], "RKF_READ_ONLY")

    def test_late_doctor_blocker_prevents_every_canonical_write_before_dispatch(self) -> None:
        (self.root / "late.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())

        hot = self.runtime.execute(
            ActionRequest(action="hot.record", params={"query": "must not write", "origin": "codex"})
        )
        inbox = self.runtime.execute(
            ActionRequest(
                action="inbox.capture",
                params={"title": "must not write", "origin": "codex", "clip": "blocked"},
            )
        )
        projection = self.runtime.execute(ActionRequest(action="capture.project_pending"))
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())

        self.assertEqual(hot.payload["error_code"], "RKF_WRITE_DOCTOR_BLOCKED")
        self.assertEqual(inbox.payload["error_code"], "RKF_READ_ONLY")
        self.assertEqual(projection.payload["error_code"], "RKF_READ_ONLY")
        self.assertEqual(after, before)

    def test_stats_snapshot_summarizes_review_health_without_writes(self) -> None:
        source_id = self.seed_paper(doi="10.1234/stats.snapshot")
        before_files = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())

        result = execute_action_request(
            ActionRequest(action="stats.snapshot", params={"paper_limit": 3}),
            runtime=self.runtime,
        )

        after_files = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after_files, before_files)
        self.assertEqual(result.action, "stats.snapshot")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["counts"]["sources"], 1)
        self.assertEqual(result.payload["counts"]["knowledge_pages"], 1)
        self.assertEqual(result.payload["counts"]["paper_queue"], 1)
        self.assertEqual(result.payload["distributions"]["knowledge_types"]["paper"], 1)
        self.assertEqual(result.payload["distributions"]["claim_readiness"]["not-ready"], 1)
        self.assertEqual(result.payload["top_paper_nudges"][0]["source_id"], source_id)
        self.assertIn("review the top paper nudges", result.payload["next_actions"][0])

    def test_graph_neighbors_returns_public_safe_edges_without_writing_export(self) -> None:
        source_id, paper_id, topic_id = self.seed_graph_paper()
        graph_path = self.root / "graph" / "research_graph.json"
        self.assertFalse(graph_path.exists())

        result = execute_action_request(
            ActionRequest(
                action="graph.neighbors",
                params={"node_id": paper_id, "direction": "both", "limit": 10},
            ),
            runtime=self.runtime,
        )

        self.assertEqual(result.action, "graph.neighbors")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["node"]["id"], paper_id)
        neighbor_ids = {node["id"] for node in result.payload["neighbors"]}
        self.assertIn(source_id, neighbor_ids)
        self.assertIn(topic_id, neighbor_ids)
        edge_types = {edge["type"] for edge in result.payload["edges"]}
        self.assertIn("derived-from", edge_types)
        self.assertIn("tagged-with", edge_types)
        self.assertEqual(result.payload["direction"], "both")
        self.assertFalse(graph_path.exists())

    def test_graph_paths_returns_shortest_public_safe_path(self) -> None:
        _source_id, paper_id, topic_id = self.seed_graph_paper()

        result = execute_action_request(
            ActionRequest(
                action="graph.paths",
                params={
                    "source_id": paper_id,
                    "target_id": topic_id,
                    "direction": "both",
                    "max_depth": 4,
                    "limit": 5,
                },
            ),
            runtime=self.runtime,
        )

        self.assertEqual(result.action, "graph.paths")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["source"]["id"], paper_id)
        self.assertEqual(result.payload["target"]["id"], topic_id)
        self.assertGreaterEqual(len(result.payload["paths"]), 1)
        first_path = result.payload["paths"][0]
        self.assertEqual(first_path["node_ids"][0], paper_id)
        self.assertEqual(first_path["node_ids"][-1], topic_id)
        self.assertEqual(first_path["length"], 1)
        self.assertEqual(first_path["edges"][0]["type"], "tagged-with")

    def test_graph_page_context_groups_related_nodes(self) -> None:
        source_id, paper_id, topic_id = self.seed_graph_paper()

        result = execute_action_request(
            ActionRequest(action="graph.page_context", params={"page_id": paper_id, "limit": 10}),
            runtime=self.runtime,
        )

        self.assertEqual(result.action, "graph.page_context")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["page_id"], paper_id)
        self.assertEqual(result.payload["node"]["id"], paper_id)
        self.assertIn(source_id, {node["id"] for node in result.payload["related_sources"]})
        self.assertIn(topic_id, {node["id"] for node in result.payload["related_topics"]})
        self.assertIn("outgoing edge(s)", " ".join(result.payload["summary"]))
        self.assertIn("related topic(s)", " ".join(result.payload["summary"]))

    def test_graph_traversal_reports_missing_nodes(self) -> None:
        result = execute_action_request(
            ActionRequest(action="graph.neighbors", params={"node_id": "papers/missing"}),
            runtime=self.runtime,
        )

        self.assertEqual(result.action, "graph.neighbors")
        self.assertEqual(result.status, "not-found")
        self.assertEqual(result.payload["node_id"], "papers/missing")

    def test_graph_traversal_rejects_bad_parameters(self) -> None:
        self.seed_graph_paper()

        bad_direction = execute_action_request(
            ActionRequest(
                action="graph.neighbors",
                params={"node_id": "papers/doi_10_1234_graph_traversal", "direction": "sideways"},
            ),
            runtime=self.runtime,
        )
        self.assertEqual(bad_direction.status, "error")
        self.assertIn("direction must be one of", bad_direction.message)

        bad_depth = execute_action_request(
            ActionRequest(
                action="graph.paths",
                params={
                    "source_id": "papers/doi_10_1234_graph_traversal",
                    "target_id": "cloud-microphysics",
                    "max_depth": 0,
                },
            ),
            runtime=self.runtime,
        )
        self.assertEqual(bad_depth.status, "error")
        self.assertIn("max_depth must be greater than 0", bad_depth.message)


if __name__ == "__main__":
    unittest.main()
