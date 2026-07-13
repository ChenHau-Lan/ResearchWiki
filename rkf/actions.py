"""Structured RKF action API for Codex app workflows.

This module is the app-facing runtime layer between natural-language Codex
workflows and the lower-level RKF core helpers. The legacy CLI can keep using
the same core behavior, but new integrations should prefer ActionRequest over
building command strings.
"""

from __future__ import annotations

import hashlib
import os
import fcntl
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import (
    Workspace,
    codex_handoff_capsule,
    create_inbox_item,
    export_graph,
    generate_wiki_index,
    graph_neighbors,
    graph_page_context,
    graph_paths,
    knowledge_page_records,
    lint_ars_handoff,
    lint_graph_links,
    lint_knowledge_pages,
    lint_public_safety,
    lint_topics,
    paper_queue,
    recent_hot_events,
    read_json,
    record_hot_query,
    refresh_hot_markdown,
    relative_workspace_path,
    render_workspace_status,
)
from .session import (
    SessionMode,
    SessionState,
    activate_session,
    deactivate_session,
    new_session,
    session_receipt,
)
from .retrieval import search_central_rkf
from .capture import (
    CaptureInput,
    CaptureTransactionConflict,
    pending_projection_events,
    projection_checkpoint,
    record_projection_target,
    route_capture,
)
from .paper_migration import MigrationPreviewError, run_preview
from .paper_apply import MigrationApplyError, apply_migration, rollback_migration
from .sync import run_connect_doctor
from .views import preview_base_views, write_base_views
from .maintenance import MaintenanceBlocked, plan_maintenance, run_maintenance
from .cleanup import CleanupReportRootError, inventory_cleanup, validate_cleanup_report_root, write_cleanup_manifest
from .discovery import (
    DiscoveryError,
    discovery_status,
    load_acceptance_state,
    load_discovery_run,
    mark_candidates_accepted,
    preview_discovery,
    record_discovery_run,
    select_run_candidates,
)
from .public_dashboard import (
    DashboardSafetyError,
    preview_public_dashboard,
    publish_public_dashboard,
    render_dashboard_preview,
)


@dataclass(frozen=True)
class ActionRequest:
    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    action: str
    status: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


CONTROL_ACTIONS = {"rkf.activate", "rkf.status", "rkf.deactivate"}
WRITE_ACTIONS = {
    "inbox.capture",
    "hot.record",
    "graph.export",
    "index.generate",
    "codex_handoff.generate",
    "capture.route",
    "capture.project_pending",
    "views.generate",
    "maintenance.run",
    "paper.migration.apply",
    "paper.migration.rollback",
    "discover.record",
    "discover.accept",
    "dashboard.publish",
}
SHARED_WRITE_ACTIONS = WRITE_ACTIONS - {"dashboard.publish"}
WRITER_ONLY_ACTIONS = {
    "inbox.capture",
    "hot.record",
    "graph.export",
    "index.generate",
    "codex_handoff.generate",
    "capture.project_pending",
    "views.generate",
    "maintenance.run",
    "paper.migration.apply",
    "paper.migration.rollback",
    "discover.record",
    "discover.accept",
}
DOCTOR_GUARDED_ACTIONS = SHARED_WRITE_ACTIONS
AUTOMATION_DISCOVERY_ACCEPT_LIMIT = 20


def _discovery_acceptance_idempotency_key(run_id: str, candidate_id: str) -> str:
    identity = hashlib.sha256(
        f"{run_id}\0{candidate_id}".encode("utf-8")
    ).hexdigest()
    return f"discover.accept:{identity}"


def _workspace(workspace: Workspace | Path | None = None) -> Workspace:
    if isinstance(workspace, Workspace):
        return workspace
    if isinstance(workspace, Path):
        return Workspace(workspace)
    return Workspace()


ACTION_LINT_MODES = {
    "all",
    "structure-lint",
    "evidence-lint",
    "graph-lint",
    "ars-handoff-lint",
    "public-safety-lint",
    "repair-plan",
}


def _workspace_counts(ws: Workspace) -> dict[str, int]:
    return {
        "knowledge_pages": len(knowledge_page_records(ws)),
        "sources": len(list(ws.paths.sources.glob("*.json"))) if ws.paths.sources.exists() else 0,
        "evidence_artifacts": len(list(ws.paths.evidence_index.glob("*.json"))) if ws.paths.evidence_index.exists() else 0,
        "topics": len(ws.load_topics()),
    }


def _lint_errors(ws: Workspace, mode: str) -> list[str]:
    if mode not in ACTION_LINT_MODES:
        raise SystemExit(f"unknown lint mode: {mode}")
    errors: list[str] = []
    if mode in {"all", "structure-lint", "evidence-lint"}:
        errors.extend(lint_knowledge_pages(ws))
    if mode in {"all", "structure-lint"}:
        errors.extend(lint_topics(ws))
    if mode in {"all", "graph-lint"}:
        errors.extend(lint_graph_links(ws))
    if mode in {"all", "ars-handoff-lint"}:
        errors.extend(lint_ars_handoff(ws))
    if mode == "public-safety-lint":
        errors.extend(lint_public_safety(ws))
    return errors


def _counter_dict(values: list[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _source_status_counts(ws: Workspace) -> dict[str, int]:
    if not ws.paths.sources.exists():
        return {}
    statuses: list[str] = []
    for path in sorted(ws.paths.sources.glob("*.json")):
        record = read_json(path)
        statuses.append(str(record.get("status", "unknown")))
    return _counter_dict(statuses)


def _evidence_status_counts(ws: Workspace) -> dict[str, int]:
    if not ws.paths.evidence_index.exists():
        return {}
    statuses: list[str] = []
    for path in sorted(ws.paths.evidence_index.glob("*.json")):
        record = read_json(path)
        statuses.append(str(record.get("status", "unknown")))
    return _counter_dict(statuses)


def _knowledge_distributions(ws: Workspace) -> dict[str, dict[str, int]]:
    records = knowledge_page_records(ws)
    return {
        "knowledge_types": _counter_dict([str(meta.get("type", "unknown")) for _, meta, _ in records]),
        "paper_reading_state": _counter_dict(
            [
                str(meta.get("reading_state", meta.get("reading_status", "unknown")))
                for _, meta, _ in records
                if meta.get("type") == "paper"
            ]
        ),
        "fulltext_status": _counter_dict(
            [str(meta.get("fulltext_status", "unknown")) for _, meta, _ in records if meta.get("type") == "paper"]
        ),
        "claim_readiness": _counter_dict(
            [
                str(meta.get("claim_readiness", "unknown"))
                for _, meta, _ in records
                if meta.get("type") in {"paper", "claim", "synthesis"}
            ]
        ),
        "synthesis_maturity": _counter_dict(
            [str(meta.get("synthesis_maturity", "unknown")) for _, meta, _ in records if meta.get("type") == "synthesis"]
        ),
    }


def capture_inbox(
    *,
    workspace: Workspace | Path | None = None,
    title: str,
    origin: str,
    source_url: str = "",
    doi: str = "",
    clip: str = "",
    reader_note: str = "",
    agent_note: str = "",
    topic_id: str = "",
    inject: bool = True,
    projection_event_id: str = "",
) -> ActionResult:
    ws = _workspace(workspace)
    payload = create_inbox_item(
        ws,
        title=title,
        origin=origin,
        source_url=source_url,
        doi=doi,
        clip=clip,
        reader_note=reader_note,
        agent_note=agent_note,
        topic_id=topic_id,
        inject=inject,
        projection_event_id=projection_event_id,
    )
    return ActionResult(
        action="inbox.capture",
        status="ok",
        message=f"wrote inbox item: {payload['path']}",
        payload=payload,
    )


def record_hot(
    *,
    workspace: Workspace | Path | None = None,
    query: str,
    topic_id: str = "",
    origin: str = "local",
    intent: str = "query",
    paper_leads: list[str] | None = None,
    notes: str = "",
    refresh: bool = True,
    days: int = 30,
    created: str = "",
    projection_event_id: str = "",
) -> ActionResult:
    ws = _workspace(workspace)
    event = record_hot_query(
        ws,
        query=query,
        topic_id=topic_id,
        origin=origin,
        intent=intent,
        paper_leads=paper_leads or [],
        notes=notes,
        created=created,
        projection_event_id=projection_event_id,
    )
    hot_path = ""
    if refresh:
        hot_path = str(refresh_hot_markdown(ws, days=days))
    return ActionResult(
        action="hot.record",
        status="ok",
        message=f"recorded hot query: {event['event_id']}",
        payload={"event_id": event["event_id"], "event": event, "hot_path": hot_path},
    )


def render_world(
    *,
    workspace: Workspace | Path | None = None,
    log_tail: int = 5,
) -> ActionResult:
    ws = _workspace(workspace)
    markdown = render_workspace_status(ws, log_tail=log_tail)
    return ActionResult(
        action="world.render",
        status="ok",
        message="rendered RKF world context",
        payload={"markdown": markdown, "counts": _workspace_counts(ws), "log_tail": log_tail},
    )


def queue_papers(
    *,
    workspace: Workspace | Path | None = None,
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    items = paper_queue(ws)
    limited = items[:limit]
    return ActionResult(
        action="paper.queue",
        status="ok",
        message=f"found {len(items)} active paper nudges",
        payload={"items": limited, "count": len(items), "limit": limit},
    )


def run_lint(
    *,
    workspace: Workspace | Path | None = None,
    mode: str = "all",
) -> ActionResult:
    ws = _workspace(workspace)
    errors = _lint_errors(ws, mode)
    passed = not errors
    return ActionResult(
        action="lint.run",
        status="ok" if passed else "failed",
        message=f"rkf {mode} {'passed' if passed else 'failed'}",
        payload={"mode": mode, "passed": passed, "errors": errors},
    )


def export_graph_action(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    graph = export_graph(ws)
    rel_path = relative_workspace_path(ws, ws.paths.graph / "research_graph.json")
    return ActionResult(
        action="graph.export",
        status="ok",
        message=f"exported graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges",
        payload={
            "path": rel_path,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "graph": graph,
        },
    )


def _graph_action_result(*, action: str, payload: dict[str, Any], ok_message: str) -> ActionResult:
    status = str(payload.get("status", "ok"))
    if status == "ok":
        message = ok_message
    elif status == "not-found":
        message = f"graph node not found: {payload.get('node_id', payload.get('page_id', 'unknown'))}"
    else:
        message = str(payload.get("error", "graph traversal failed"))
    return ActionResult(action=action, status=status, message=message, payload=payload)


def graph_neighbors_action(
    *,
    workspace: Workspace | Path | None = None,
    node_id: str,
    direction: str = "both",
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_neighbors(ws, node_id=node_id, direction=direction, limit=limit)
    neighbor_count = len(payload.get("neighbors", []))
    return _graph_action_result(
        action="graph.neighbors",
        payload=payload,
        ok_message=f"found {neighbor_count} graph neighbor(s) for {node_id}",
    )


def graph_paths_action(
    *,
    workspace: Workspace | Path | None = None,
    source_id: str,
    target_id: str,
    direction: str = "both",
    max_depth: int = 4,
    limit: int = 5,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_paths(
        ws,
        source_id=source_id,
        target_id=target_id,
        direction=direction,
        max_depth=max_depth,
        limit=limit,
    )
    path_count = len(payload.get("paths", []))
    return _graph_action_result(
        action="graph.paths",
        payload=payload,
        ok_message=f"found {path_count} graph path(s) from {source_id} to {target_id}",
    )


def graph_page_context_action(
    *,
    workspace: Workspace | Path | None = None,
    page_id: str,
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_page_context(ws, page_id=page_id, limit=limit)
    return _graph_action_result(
        action="graph.page_context",
        payload=payload,
        ok_message=f"rendered graph page context for {page_id}",
    )


def generate_index(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    path = generate_wiki_index(ws)
    rel_path = relative_workspace_path(ws, path)
    return ActionResult(
        action="index.generate",
        status="ok",
        message=f"generated wiki index: {rel_path}",
        payload={"path": rel_path},
    )


def generate_codex_handoff(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    path = codex_handoff_capsule(ws)
    rel_path = relative_workspace_path(ws, path)
    return ActionResult(
        action="codex_handoff.generate",
        status="ok",
        message=f"generated Codex handoff context: {rel_path}",
        payload={"path": rel_path},
    )


def snapshot_stats(
    *,
    workspace: Workspace | Path | None = None,
    paper_limit: int = 8,
    lint_mode: str = "all",
) -> ActionResult:
    ws = _workspace(workspace)
    queue_items = paper_queue(ws)
    hot_events = recent_hot_events(ws) if ws.paths.hot_md.exists() else []
    lint_errors = _lint_errors(ws, lint_mode)
    counts = _workspace_counts(ws)
    counts.update(
        {
            "paper_queue": len(queue_items),
            "hot_queries": len(hot_events),
            "lint_errors": len(lint_errors),
        }
    )
    distributions = {
        "source_status": _source_status_counts(ws),
        "evidence_status": _evidence_status_counts(ws),
        **_knowledge_distributions(ws),
    }
    next_actions: list[str] = []
    if queue_items:
        next_actions.append("review the top paper nudges before promoting claims")
    if lint_errors:
        next_actions.append(f"resolve {len(lint_errors)} lint finding(s) before publishing or trusting synthesis")
    if not next_actions:
        next_actions.append("no deterministic RKF health blocker detected in this snapshot")
    return ActionResult(
        action="stats.snapshot",
        status="ok" if not lint_errors else "blocked",
        message=f"snapshot: {counts['paper_queue']} paper nudges, {counts['lint_errors']} lint findings",
        payload={
            "counts": counts,
            "distributions": distributions,
            "top_paper_nudges": queue_items[:paper_limit],
            "lint": {"mode": lint_mode, "passed": not lint_errors, "errors": lint_errors},
            "next_actions": next_actions,
        },
    )


def _resolve_discovery_query(ws: Workspace, *, query: str, topic_id: str) -> str:
    normalized = " ".join(query.split())
    if normalized:
        return normalized
    if topic_id:
        topic = next(
            (
                item
                for item in ws.load_topics()
                if isinstance(item, dict) and str(item.get("topic_id", "")) == topic_id
            ),
            None,
        )
        if topic is None:
            raise DiscoveryError("unknown RKF topic_id")
        defaults = topic.get("default_search_strings", [])
        if isinstance(defaults, list):
            for value in defaults:
                candidate = " ".join(str(value).split())
                if candidate:
                    return candidate
        name = " ".join(str(topic.get("name", "")).split())
        if name:
            return name
        raise DiscoveryError("RKF topic has no usable discovery query")
    events = recent_hot_events(ws) if ws.paths.hot_md.exists() else []
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        candidate = " ".join(
            str(event.get("query") or event.get("normalized_query") or "").split()
        )
        if candidate:
            return candidate
    raise DiscoveryError("discover.preview requires query, topic_id, or recent hot demand")


def preview_discovery_action(
    *,
    workspace: Workspace | Path | None = None,
    query: str = "",
    topic_id: str = "",
    max_results: int = 20,
    providers: list[str] | None = None,
    paper_radar_records: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> ActionResult:
    ws = _workspace(workspace)
    if not isinstance(query, str) or not isinstance(topic_id, str):
        return ActionResult(
            action="discover.preview",
            status="error",
            message="query and topic_id must be text",
            payload={"error_code": "RKF_DISCOVERY_INPUT_INVALID", "promotion": "none"},
        )
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        return ActionResult(
            action="discover.preview",
            status="error",
            message="max_results must be an integer",
            payload={"error_code": "RKF_DISCOVERY_INPUT_INVALID", "promotion": "none"},
        )
    if providers is not None and (
        not isinstance(providers, list)
        or not all(isinstance(item, str) for item in providers)
    ):
        return ActionResult(
            action="discover.preview",
            status="error",
            message="providers must be a list of provider names",
            payload={"error_code": "RKF_DISCOVERY_INPUT_INVALID", "promotion": "none"},
        )
    try:
        resolved_query = _resolve_discovery_query(ws, query=query, topic_id=topic_id)
        preview = preview_discovery(
            ws,
            query=resolved_query,
            topic_id=topic_id,
            max_results=max_results,
            provider_names=providers,
            paper_radar_records=paper_radar_records,
        )
    except DiscoveryError as error:
        return ActionResult(
            action="discover.preview",
            status="blocked",
            message=str(error),
            payload={"error_code": "RKF_DISCOVERY_PREVIEW_REJECTED", "promotion": "none"},
        )
    return ActionResult(
        action="discover.preview",
        status=str(preview["status"]),
        message=(
            f"previewed {preview['candidate_count']} candidate paper(s); "
            "candidate-only; Promotion: none"
        ),
        payload=preview,
    )


def record_discovery_action(
    *,
    workspace: Workspace | Path | None = None,
    preview: dict[str, Any],
    preview_hash: str,
) -> ActionResult:
    ws = _workspace(workspace)
    try:
        recorded = record_discovery_run(
            ws,
            preview=preview,
            expected_hash=preview_hash,
        )
    except DiscoveryError as error:
        return ActionResult(
            action="discover.record",
            status="blocked",
            message=str(error),
            payload={"error_code": "RKF_DISCOVERY_RECORD_REJECTED", "promotion": "none"},
        )
    receipt = {
        "run_id": recorded["run_id"],
        "run_path": recorded["run_path"],
        "preview_hash": recorded["preview_hash"],
        "candidate_count": recorded["candidate_count"],
        "provider_status": recorded["provider_status"],
        "evidence_boundary": "candidate-only",
        "promotion": "none",
    }
    return ActionResult(
        action="discover.record",
        status="ok",
        message=f"recorded {recorded['candidate_count']} candidate paper(s); Promotion: none",
        payload=receipt,
    )


def discovery_status_action(
    *,
    workspace: Workspace | Path | None = None,
) -> ActionResult:
    payload = discovery_status(_workspace(workspace))
    return ActionResult(
        action="discover.status",
        status="ok" if not payload["malformed_run_count"] else "partial",
        message=(
            f"discovery has {payload['run_count']} run(s), "
            f"{payload['candidate_count']} candidate(s), and "
            f"{payload['accepted_count']} accepted candidate(s)"
        ),
        payload=payload,
    )


def preview_dashboard_action(
    *,
    workspace: Workspace | Path | None = None,
    window_days: int = 30,
) -> ActionResult:
    if isinstance(window_days, bool) or not isinstance(window_days, int):
        return ActionResult(
            action="dashboard.preview",
            status="error",
            message="window_days must be an integer",
            payload={"error_code": "RKF_DASHBOARD_INPUT_INVALID"},
        )
    try:
        payload = preview_public_dashboard(_workspace(workspace), window_days=window_days)
    except DashboardSafetyError as error:
        return ActionResult(
            action="dashboard.preview",
            status="blocked",
            message=str(error),
            payload={"error_code": "RKF_DASHBOARD_PREVIEW_REJECTED"},
        )
    return ActionResult(
        action="dashboard.preview",
        status="ok",
        message="prepared aggregate-only dashboard preview for exact-hash review",
        payload=payload,
    )


def publish_dashboard_action(
    *,
    workspace: Workspace | Path | None = None,
    preview_id: str,
    snapshot_hash: str,
) -> ActionResult:
    try:
        payload = publish_public_dashboard(
            _workspace(workspace),
            preview_id=preview_id,
            approved_snapshot_hash=snapshot_hash,
        )
    except DashboardSafetyError as error:
        return ActionResult(
            action="dashboard.publish",
            status="blocked",
            message=str(error),
            payload={"error_code": "RKF_DASHBOARD_PUBLISH_REJECTED"},
        )
    return ActionResult(
        action="dashboard.publish",
        status="ok",
        message="published the exact approved aggregate snapshot to the local static site",
        payload=payload,
    )


def review_dashboard_action(
    *,
    workspace: Workspace | Path | None = None,
    preview_id: str,
) -> ActionResult:
    if not isinstance(preview_id, str):
        return ActionResult(
            action="dashboard.review",
            status="error",
            message="preview_id must be text",
            payload={"error_code": "RKF_DASHBOARD_INPUT_INVALID"},
        )
    try:
        payload = render_dashboard_preview(
            _workspace(workspace),
            preview_id=preview_id,
        )
    except DashboardSafetyError as error:
        return ActionResult(
            action="dashboard.review",
            status="blocked",
            message=str(error),
            payload={"error_code": "RKF_DASHBOARD_REVIEW_REJECTED"},
        )
    return ActionResult(
        action="dashboard.review",
        status="ok",
        message="rendered a private self-contained page for exact-preview review",
        payload=payload,
    )


def _dispatch_active_action(request: ActionRequest, *, workspace: Workspace) -> ActionResult:
    params = dict(request.params)
    if request.action == "inbox.capture":
        return capture_inbox(workspace=workspace, **params)
    if request.action == "hot.record":
        return record_hot(workspace=workspace, **params)
    if request.action == "world.render":
        return render_world(workspace=workspace, **params)
    if request.action == "paper.queue":
        return queue_papers(workspace=workspace, **params)
    if request.action == "lint.run":
        return run_lint(workspace=workspace, **params)
    if request.action == "graph.export":
        return export_graph_action(workspace=workspace, **params)
    if request.action == "graph.neighbors":
        return graph_neighbors_action(workspace=workspace, **params)
    if request.action == "graph.paths":
        return graph_paths_action(workspace=workspace, **params)
    if request.action == "graph.page_context":
        return graph_page_context_action(workspace=workspace, **params)
    if request.action == "index.generate":
        return generate_index(workspace=workspace, **params)
    if request.action == "codex_handoff.generate":
        return generate_codex_handoff(workspace=workspace, **params)
    if request.action == "stats.snapshot":
        return snapshot_stats(workspace=workspace, **params)
    if request.action == "discover.preview":
        return preview_discovery_action(workspace=workspace, **params)
    if request.action == "discover.record":
        return record_discovery_action(workspace=workspace, **params)
    if request.action == "discover.status":
        if params:
            raise SystemExit(f"unsupported discover status parameter(s): {', '.join(sorted(params))}")
        return discovery_status_action(workspace=workspace)
    if request.action == "dashboard.preview":
        return preview_dashboard_action(workspace=workspace, **params)
    if request.action == "dashboard.review":
        return review_dashboard_action(workspace=workspace, **params)
    if request.action == "dashboard.publish":
        return publish_dashboard_action(workspace=workspace, **params)
    if request.action == "query.search":
        payload = search_central_rkf(workspace, **params)
        return ActionResult(
            action="query.search",
            status="ok",
            message=f"found {payload['count']} governed RKF result(s)",
            payload=payload,
        )
    if request.action == "connect.doctor":
        if params:
            raise SystemExit(f"unsupported connect doctor parameter(s): {', '.join(sorted(params))}")
        report = run_connect_doctor(workspace)
        payload = report.as_payload()
        return ActionResult(
            action="connect.doctor",
            status="blocked" if report.status == "blocked" else "ok",
            message=f"RKF connection doctor: {report.status}",
            payload=payload,
        )
    if request.action == "views.preview":
        if params:
            raise SystemExit(f"unsupported views preview parameter(s): {', '.join(sorted(params))}")
        payload = preview_base_views(workspace)
        return ActionResult(
            action="views.preview",
            status="ok",
            message=f"rendered {payload['count']} RKF Obsidian Base preview(s)",
            payload=payload,
        )
    if request.action == "views.generate":
        if params:
            raise SystemExit(f"unsupported views generate parameter(s): {', '.join(sorted(params))}")
        try:
            payload = write_base_views(workspace)
        except RuntimeError as error:
            return ActionResult(
                action="views.generate",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_VIEW_WRITE_FAILED"},
            )
        return ActionResult(
            action="views.generate",
            status="ok",
            message=f"generated {payload['count']} canonical RKF Obsidian Base view(s)",
            payload=payload,
        )
    if request.action == "maintenance.preview":
        cadence = str(params.pop("cadence", "weekly"))
        if params:
            raise SystemExit(f"unsupported maintenance preview parameter(s): {', '.join(sorted(params))}")
        try:
            plan = plan_maintenance(workspace, cadence=cadence)
        except ValueError as error:
            return ActionResult(
                action="maintenance.preview",
                status="error",
                message=str(error),
                payload={"error_code": "RKF_MAINTENANCE_CADENCE_INVALID"},
            )
        payload = plan.as_payload()
        return ActionResult(
            action="maintenance.preview",
            status="blocked" if plan.doctor.status == "blocked" else "ok",
            message=f"prepared {cadence} RKF maintenance plan; Promotion: none",
            payload=payload,
        )
    if request.action == "maintenance.run":
        cadence = str(params.pop("cadence", "daily"))
        if params:
            raise SystemExit(f"unsupported maintenance run parameter(s): {', '.join(sorted(params))}")
        try:
            payload = run_maintenance(workspace, cadence=cadence)
        except (MaintenanceBlocked, ValueError) as error:
            return ActionResult(
                action="maintenance.run",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_MAINTENANCE_BLOCKED", "promotion": "none"},
            )
        return ActionResult(
            action="maintenance.run",
            status="ok",
            message=f"confirmed {cadence} RKF maintenance receipt; Promotion: none",
            payload=payload,
        )
    if request.action == "cleanup.manifest.preview":
        requested_report_root = Path(str(params.pop("report_root", workspace.root / ".rkf_private" / "cleanup_manifests")))
        automation_candidates = params.pop("automation_candidates", [])
        if params:
            raise SystemExit(f"unsupported cleanup preview parameter(s): {', '.join(sorted(params))}")
        try:
            report_root = validate_cleanup_report_root(
                requested_report_root,
                workspace_root=workspace.root,
                wiki_root=workspace.paths.wiki_root,
                raw_root=workspace.paths.raw_root,
            )
        except CleanupReportRootError:
            return ActionResult(
                action="cleanup.manifest.preview",
                status="blocked",
                message="cleanup manifest report root must stay inside local .rkf_private",
                payload={"error_code": "RKF_CLEANUP_REPORT_ROOT_REJECTED"},
            )
        if not isinstance(automation_candidates, list) or not all(
            isinstance(item, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in item.items())
            for item in automation_candidates
        ):
            return ActionResult(
                action="cleanup.manifest.preview",
                status="error",
                message="automation_candidates must be a list of string-only snapshots",
                payload={"error_code": "RKF_CLEANUP_INPUT_INVALID"},
            )
        manifest = inventory_cleanup(
            workspace.root,
            raw_root=workspace.paths.raw_root,
            automation_candidates=automation_candidates,
        )
        write_cleanup_manifest(manifest, report_root)
        payload = {"manifest": manifest.as_payload(), "entry_count": len(manifest.entries), "promotion": "none"}
        return ActionResult(
            action="cleanup.manifest.preview",
            status="ok",
            message="prepared a read-only RKF cleanup manifest; no cleanup was applied",
            payload=payload,
        )
    if request.action == "paper.migration.preview":
        report_root = Path(str(params.pop("report_root", workspace.root / ".rkf_private" / "migration_reports")))
        expected_count = params.pop("expected_count", 57)
        if params:
            raise SystemExit(f"unsupported paper migration preview parameter(s): {', '.join(sorted(params))}")
        try:
            report = run_preview(
                workspace,
                report_root=report_root,
                expected_count=expected_count,
            )
        except MigrationPreviewError as error:
            return ActionResult(
                action="paper.migration.preview",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_MIGRATION_PREVIEW_REJECTED", "promotion": "none"},
            )
        return ActionResult(
            action="paper.migration.preview",
            status="ok",
            message=(
                f"prepared paper migration preview {report.run_id}; "
                "review manifest before any live apply; Promotion: none"
            ),
            payload={
                "run_id": report.run_id,
                "manifest_hash": report.manifest_hash,
                "input_count": report.input_count,
                "output_count": report.output_count,
                "diff_count": report.diff_count,
                "routing_count": report.routing_count,
                "unresolved_count": report.unresolved_count,
                "validation_error_count": report.validation_error_count,
                "ready_for_live_apply": report.ready_for_live_apply,
                "promotion": "none",
            },
        )
    if request.action == "paper.migration.apply":
        report_dir = Path(str(params.pop("report_dir", "")))
        manifest_hash = str(params.pop("manifest_hash", ""))
        if params:
            raise SystemExit(f"unsupported paper migration apply parameter(s): {', '.join(sorted(params))}")
        try:
            result = apply_migration(
                workspace,
                report_dir=report_dir,
                approved_manifest_hash=manifest_hash,
            )
        except MigrationApplyError as error:
            return ActionResult(
                action="paper.migration.apply",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_MIGRATION_APPLY_REJECTED", "promotion": "none"},
            )
        return ActionResult(
            action="paper.migration.apply",
            status="ok",
            message=f"applied approved paper migration with backup {result.backup_id}; Promotion: none",
            payload=result.as_payload(),
        )
    if request.action == "paper.migration.rollback":
        backup_id = str(params.pop("backup_id", ""))
        manifest_hash = str(params.pop("manifest_hash", ""))
        if params:
            raise SystemExit(f"unsupported paper migration rollback parameter(s): {', '.join(sorted(params))}")
        try:
            result = rollback_migration(
                workspace,
                backup_id=backup_id,
                approved_manifest_hash=manifest_hash,
            )
        except MigrationApplyError as error:
            return ActionResult(
                action="paper.migration.rollback",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_MIGRATION_ROLLBACK_REJECTED", "promotion": "none"},
            )
        return ActionResult(
            action="paper.migration.rollback",
            status="ok",
            message=f"rolled back approved paper migration backup {result.backup_id}; Promotion: none",
            payload=result.as_payload(),
        )
    raise SystemExit(f"unsupported RKF action: {request.action}")


class RKFActionRuntime:
    """Session-owned action dispatcher for one Codex task."""

    def __init__(
        self,
        *,
        workspace: Workspace | Path | None = None,
        project_root: Path | None = None,
        session_id: str = "",
    ) -> None:
        self.workspace = _workspace(workspace)
        self.project_root = project_root
        self.session: SessionState = new_session(session_id)

    def _materialize_targets(
        self,
        *,
        event_id: str,
        item: CaptureInput,
        targets: list[str],
        event_created: str,
    ) -> tuple[list[dict[str, Any]], str, bool]:
        lock_path = self.workspace.paths.sync_state / "projections" / f"{event_id}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            return [], "projection is already running", False
        try:
            return self._materialize_targets_locked(
                event_id=event_id,
                item=item,
                targets=targets,
                event_created=event_created,
            )
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def _materialize_targets_locked(
        self,
        *,
        event_id: str,
        item: CaptureInput,
        targets: list[str],
        event_created: str,
    ) -> tuple[list[dict[str, Any]], str, bool]:
        completed = {
            str(target)
            for target in projection_checkpoint(self.workspace, event_id).get(
                "completed_targets", []
            )
        }
        projections: list[dict[str, Any]] = []
        for target in sorted(set(targets) - completed):
            try:
                if target == "inbox":
                    result = capture_inbox(
                        workspace=self.workspace,
                        title=item.title or item.text[:80],
                        origin=item.origin,
                        source_url=item.source_url,
                        doi=item.doi,
                        clip=item.text,
                        reader_note=item.reader_note,
                        agent_note=item.agent_note,
                        topic_id=item.topic_id,
                        inject=item.create_paper_draft,
                        projection_event_id=event_id,
                    )
                elif target == "hot":
                    result = record_hot(
                        workspace=self.workspace,
                        query=item.text,
                        topic_id=item.topic_id,
                        origin=item.origin,
                        intent=item.intent,
                        notes="",
                        created=event_created,
                        projection_event_id=event_id,
                    )
                else:
                    return projections, f"unsupported projection target: {target}", False
                record_projection_target(self.workspace, event_id, target)
                projections.append(
                    {
                        "action": result.action,
                        "status": result.status,
                        "payload": result.payload,
                    }
                )
                completed.add(target)
            except (OSError, SystemExit) as error:
                return projections, str(error), False
        return projections, "", set(targets).issubset(completed)

    def _project_pending(self) -> ActionResult:
        events = pending_projection_events(self.workspace)
        materialized = 0
        projections: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for event in events:
            payload = event.get("payload", {})
            item = CaptureInput(
                text=str(payload.get("text", "")),
                origin=str(event.get("origin", "")),
                title=str(payload.get("title", "")),
                doi=str(payload.get("doi", "")),
                source_url=str(payload.get("source_url", "")),
                authors=str(payload.get("authors", "")),
                year=str(payload.get("year", "")),
                intent=str(payload.get("intent", "research-discussion")),
                reader_note=str(payload.get("reader_note", "")),
                agent_note=str(payload.get("agent_note", "")),
                topic_id=str(payload.get("topic_id", "")),
                create_paper_draft=bool(payload.get("create_paper_draft", True)),
            )
            event_id = str(event.get("event_id", ""))
            projected, error, done = self._materialize_targets(
                event_id=event_id,
                item=item,
                targets=[str(target) for target in payload.get("targets", [])],
                event_created=str(event.get("created", "")),
            )
            projections.extend(projected)
            if done:
                materialized += 1
            elif error:
                errors.append({"event_id": event_id, "error": error})
        return ActionResult(
            action="capture.project_pending",
            status="partial" if errors else "ok",
            message=(
                f"materialized {materialized} pending capture event(s); "
                "Promotion: none"
            ),
            payload={
                "events_seen": len(events),
                "events_materialized": materialized,
                "projections": projections,
                "errors": errors,
                "promotion": "none",
            },
        )

    def _capture_route(
        self,
        params: dict[str, Any],
        *,
        actor: str = "codex",
        idempotency_key: str = "",
    ) -> ActionResult:
        item = CaptureInput(**params)
        try:
            routed = route_capture(
                self.workspace,
                item,
                machine_id=self.session.machine_id,
                actor=actor,
                idempotency_key=idempotency_key,
            )
        except CaptureTransactionConflict as error:
            return ActionResult(
                action="capture.route",
                status="blocked",
                message=str(error),
                payload={
                    "error_code": "RKF_CAPTURE_TRANSACTION_CONFLICT",
                    "promotion": "none",
                },
            )
        except SystemExit as error:
            message = str(error)
            not_triggered = "did not find a deterministic research trigger" in message
            return ActionResult(
                action="capture.route",
                status="not-applicable" if not_triggered else "blocked",
                message=message,
                payload={
                    "error_code": (
                        "RKF_CAPTURE_NOT_TRIGGERED"
                        if not_triggered
                        else "RKF_CAPTURE_REJECTED"
                    ),
                    "promotion": "none",
                },
            )

        projections: list[dict[str, Any]] = []
        materialization = "not-needed" if not routed.materialize else "queued"
        if routed.materialize and self.session.writer_role == "designated":
            projections, projection_error, complete = self._materialize_targets(
                event_id=routed.event_id,
                item=item,
                targets=routed.decision.targets,
                event_created=routed.created,
            )
            if not complete:
                return ActionResult(
                    action="capture.route",
                    status="partial",
                    message=(
                        f"captured event {routed.event_id}; projection queued after "
                        "failure; Promotion: none"
                    ),
                    payload={
                        "event_id": routed.event_id,
                        "event_path": routed.event_path,
                        "dedupe_status": routed.dedupe.status,
                        "materialization": "queued",
                        "projection_error": projection_error,
                        "transaction_recovered": routed.transaction_recovered,
                        "promotion": "none",
                    },
                )
            materialization = "materialized"

        payload = {
            "event_id": routed.event_id,
            "event_path": routed.event_path,
            "capture_level": routed.decision.level,
            "targets": routed.decision.targets,
            "reasons": routed.decision.reasons,
            "dedupe_status": routed.dedupe.status,
            "matched_id": routed.dedupe.matched_id,
            "materialization": materialization,
            "projections": projections,
            "transaction_recovered": routed.transaction_recovered,
            "promotion": "none",
        }
        return ActionResult(
            action="capture.route",
            status="ok",
            message=f"captured event {routed.event_id}; Promotion: none",
            payload=payload,
        )

    def _accept_discovery(self, params: dict[str, Any]) -> ActionResult:
        run_id = str(params.pop("run_id", ""))
        candidate_ids = params.pop("candidate_ids", [])
        create_paper_drafts = params.pop("create_paper_drafts", False)
        actor = str(params.pop("actor", "human"))
        if params:
            raise SystemExit(
                f"unsupported discover accept parameter(s): {', '.join(sorted(params))}"
            )
        if not isinstance(candidate_ids, list) or not all(
            isinstance(candidate_id, str) for candidate_id in candidate_ids
        ):
            return ActionResult(
                action="discover.accept",
                status="error",
                message="candidate_ids must be a list of candidate IDs",
                payload={"error_code": "RKF_DISCOVERY_ACCEPT_INPUT_INVALID", "promotion": "none"},
            )
        if not isinstance(create_paper_drafts, bool):
            return ActionResult(
                action="discover.accept",
                status="error",
                message="create_paper_drafts must be true or false",
                payload={"error_code": "RKF_DISCOVERY_ACCEPT_INPUT_INVALID", "promotion": "none"},
            )
        if actor not in {"human", "automation"}:
            return ActionResult(
                action="discover.accept",
                status="error",
                message="actor must be human or automation",
                payload={"error_code": "RKF_DISCOVERY_ACCEPT_INPUT_INVALID", "promotion": "none"},
            )
        if actor == "automation" and create_paper_drafts:
            return ActionResult(
                action="discover.accept",
                status="blocked",
                message="automation acceptance cannot create paper drafts",
                payload={"error_code": "RKF_DISCOVERY_AUTOMATION_POLICY", "promotion": "none"},
            )
        if actor == "automation" and len(candidate_ids) > AUTOMATION_DISCOVERY_ACCEPT_LIMIT:
            return ActionResult(
                action="discover.accept",
                status="blocked",
                message=(
                    "automation acceptance exceeds the built-in per-run safety limit"
                ),
                payload={
                    "error_code": "RKF_DISCOVERY_AUTOMATION_POLICY",
                    "maximum_count": AUTOMATION_DISCOVERY_ACCEPT_LIMIT,
                    "promotion": "none",
                },
            )
        try:
            run = load_discovery_run(self.workspace, run_id)
            candidates = select_run_candidates(run, candidate_ids)
            existing_acceptance = load_acceptance_state(self.workspace, run_id)
        except DiscoveryError as error:
            return ActionResult(
                action="discover.accept",
                status="blocked",
                message=str(error),
                payload={"error_code": "RKF_DISCOVERY_ACCEPT_REJECTED", "promotion": "none"},
            )
        if not candidates:
            return ActionResult(
                action="discover.accept",
                status="blocked",
                message="at least one candidate ID is required",
                payload={"error_code": "RKF_DISCOVERY_ACCEPT_REJECTED", "promotion": "none"},
            )
        if actor == "automation" and any(
            candidate.get("dedupe_status") != "new"
            or not (candidate.get("doi") or candidate.get("url"))
            for candidate in candidates
        ):
            return ActionResult(
                action="discover.accept",
                status="blocked",
                message=(
                    "automation may accept only new candidates with a DOI or public landing URL"
                ),
                payload={
                    "error_code": "RKF_DISCOVERY_AUTOMATION_POLICY",
                    "ineligible_count": sum(
                        candidate.get("dedupe_status") != "new"
                        or not (candidate.get("doi") or candidate.get("url"))
                        for candidate in candidates
                    ),
                    "promotion": "none",
                },
            )

        previously_accepted_ids = {
            str(item["candidate_id"])
            for item in existing_acceptance.get("accepted", [])
            if isinstance(item, dict) and item.get("candidate_id")
        }
        already_accepted = [
            candidate
            for candidate in candidates
            if str(candidate["candidate_id"]) in previously_accepted_ids
        ]
        pending_candidates = [
            candidate
            for candidate in candidates
            if str(candidate["candidate_id"]) not in previously_accepted_ids
        ]
        accepted_ids: list[str] = []
        receipts: list[dict[str, Any]] = [
            {
                "candidate_id": str(candidate["candidate_id"]),
                "status": "already-accepted",
                "event_id": "",
                "dedupe_status": str(candidate.get("dedupe_status", "")),
                "materialization": "not-needed",
                "transaction_recovered": False,
                "error_code": "",
            }
            for candidate in already_accepted
        ]
        failed_count = 0
        transaction_conflict_count = 0
        for candidate in pending_candidates:
            provider = str(candidate.get("provider", "discovery"))
            item = {
                "title": str(candidate.get("title", "")),
                "text": (
                    "Selected bibliographic paper candidate from "
                    f"{provider}; metadata only; candidate is not evidence."
                ),
                "origin": f"discovery:{provider}",
                "doi": str(candidate.get("doi", "")),
                "source_url": str(candidate.get("url", "")),
                "authors": "; ".join(str(author) for author in candidate.get("authors", [])),
                "year": str(candidate.get("year") or ""),
                "intent": "paper-search",
                "topic_id": str(candidate.get("topic_id", "")),
                "create_paper_draft": create_paper_drafts,
            }
            candidate_id = str(candidate["candidate_id"])
            transaction_key = _discovery_acceptance_idempotency_key(
                run_id,
                candidate_id,
            )
            routed = self._capture_route(
                item,
                actor=actor,
                idempotency_key=transaction_key,
            )
            receipt = {
                "candidate_id": candidate_id,
                "status": routed.status,
                "event_id": str(routed.payload.get("event_id", "")),
                "dedupe_status": str(routed.payload.get("dedupe_status", "")),
                "materialization": str(routed.payload.get("materialization", "not-started")),
                "transaction_recovered": bool(
                    routed.payload.get("transaction_recovered", False)
                ),
                "error_code": str(routed.payload.get("error_code", "")),
            }
            receipts.append(receipt)
            if routed.status in {"ok", "partial"} and receipt["event_id"]:
                accepted_ids.append(candidate_id)
            else:
                failed_count += 1
                if receipt["error_code"] == "RKF_CAPTURE_TRANSACTION_CONFLICT":
                    transaction_conflict_count += 1

        acceptance: dict[str, Any] = {
            "added_count": 0,
            "accepted_count": len(previously_accepted_ids),
        }
        if accepted_ids:
            try:
                acceptance = mark_candidates_accepted(
                    self.workspace,
                    run_id=run_id,
                    candidate_ids=accepted_ids,
                    actor=actor,
                )
            except (DiscoveryError, OSError) as error:
                return ActionResult(
                    action="discover.accept",
                    status="partial",
                    message=(
                        "capture events were recorded, but candidate acceptance state could not be updated; "
                        "Promotion: none"
                    ),
                    payload={
                        "error_code": "RKF_DISCOVERY_ACCEPT_STATE_FAILED",
                        "reason": str(error),
                        "route_receipts": receipts,
                        "transaction_recovered_count": sum(
                            bool(receipt.get("transaction_recovered"))
                            for receipt in receipts
                        ),
                        "promotion": "none",
                    },
                )
        if failed_count:
            status = "partial" if accepted_ids or already_accepted else "blocked"
        else:
            status = "ok"
        return ActionResult(
            action="discover.accept",
            status=status,
            message=(
                f"accepted {len(accepted_ids)} new candidate(s) into governed capture; "
                f"{len(already_accepted)} already accepted; "
                f"paper drafts {'enabled' if create_paper_drafts else 'disabled'}; "
                "Promotion: none"
            ),
            payload={
                "run_id": run_id,
                "requested_count": len(candidates),
                "captured_count": len(accepted_ids),
                "already_accepted_count": len(already_accepted),
                "failed_count": failed_count,
                "transaction_conflict_count": transaction_conflict_count,
                "transaction_recovered_count": sum(
                    bool(receipt.get("transaction_recovered"))
                    for receipt in receipts
                ),
                "new_acceptance_count": int(acceptance.get("added_count", 0)),
                "accepted_count": int(acceptance.get("accepted_count", 0)),
                "route_receipts": receipts,
                "paper_drafts_requested": create_paper_drafts,
                "acceptance_actor": actor,
                "evidence_boundary": "candidate-to-source-capture",
                "promotion": "none",
                **(
                    {
                        "error_code": "RKF_DISCOVERY_ACCEPT_TRANSACTION_CONFLICT"
                    }
                    if transaction_conflict_count
                    else {}
                ),
            },
        )

    def execute(self, request: ActionRequest) -> ActionResult:
        if request.action == "rkf.status":
            return ActionResult(
                action="rkf.status",
                status="ok",
                message=f"RKF is {self.session.mode.value}",
                payload=session_receipt(self.session),
            )
        if request.action == "rkf.activate":
            receipt = activate_session(
                self.session,
                self.workspace,
                project_root=self.project_root,
            )
            status = "failed" if self.session.mode == SessionMode.OFF else "ok"
            return ActionResult(
                action="rkf.activate",
                status=status,
                message=f"RKF is {self.session.mode.value}",
                payload=receipt,
            )
        if request.action == "rkf.deactivate":
            receipt = deactivate_session(self.session)
            return ActionResult(
                action="rkf.deactivate",
                status="ok",
                message="RKF is OFF",
                payload=receipt,
            )
        if self.session.mode == SessionMode.OFF:
            return ActionResult(
                action=request.action,
                status="blocked",
                message="RKF is not active; say 啟動 RKF first",
                payload={"error_code": "RKF_NOT_ACTIVE", **session_receipt(self.session)},
            )
        if self.session.mode == SessionMode.ACTIVE_READ_ONLY and request.action in SHARED_WRITE_ACTIONS:
            return ActionResult(
                action=request.action,
                status="blocked",
                message="RKF is active read-only",
                payload={"error_code": "RKF_READ_ONLY", **session_receipt(self.session)},
            )
        if request.action in DOCTOR_GUARDED_ACTIONS:
            doctor = run_connect_doctor(self.workspace)
            if doctor.status == "blocked":
                if self.session.mode == SessionMode.ACTIVE:
                    self.session.mode = SessionMode.ACTIVE_READ_ONLY
                    if "CONNECT_DOCTOR_BLOCKED" not in self.session.warnings:
                        self.session.warnings.append("CONNECT_DOCTOR_BLOCKED")
                error_code = {
                    "views.generate": "RKF_VIEW_DOCTOR_BLOCKED",
                    "maintenance.run": "RKF_MAINTENANCE_DOCTOR_BLOCKED",
                }.get(request.action, "RKF_WRITE_DOCTOR_BLOCKED")
                return ActionResult(
                    action=request.action,
                    status="blocked",
                    message="connection doctor reported blockers; shared write was not attempted",
                    payload={
                        "error_code": error_code,
                        "doctor": doctor.as_payload(),
                        "session": session_receipt(self.session),
                        "promotion": "none",
                    },
                )
        if request.action == "capture.route":
            return self._capture_route(dict(request.params))
        if request.action in WRITER_ONLY_ACTIONS and self.session.writer_role != "designated":
            return ActionResult(
                action=request.action,
                status="blocked",
                message="This projection requires the maintenance writer",
                payload={"error_code": "RKF_WRITER_REQUIRED", **session_receipt(self.session)},
            )
        if request.action == "capture.project_pending":
            return self._project_pending()
        if request.action == "discover.accept":
            return self._accept_discovery(dict(request.params))
        if request.action == "connect.doctor":
            result = _dispatch_active_action(request, workspace=self.workspace)
            if result.status == "blocked" and self.session.mode == SessionMode.ACTIVE:
                self.session.mode = SessionMode.ACTIVE_READ_ONLY
                if "CONNECT_DOCTOR_BLOCKED" not in self.session.warnings:
                    self.session.warnings.append("CONNECT_DOCTOR_BLOCKED")
                payload = dict(result.payload)
                payload["session"] = session_receipt(self.session)
                return ActionResult(
                    action=result.action,
                    status=result.status,
                    message=result.message,
                    payload=payload,
                )
            return result
        return _dispatch_active_action(request, workspace=self.workspace)


def execute_action_request(
    request: ActionRequest,
    *,
    workspace: Workspace | Path | None = None,
    runtime: RKFActionRuntime | None = None,
) -> ActionResult:
    active_runtime = runtime or RKFActionRuntime(workspace=workspace)
    return active_runtime.execute(request)
