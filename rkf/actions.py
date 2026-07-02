"""Structured RKF action API for Codex app workflows.

This module is the app-facing runtime layer between natural-language Codex
workflows and the lower-level RKF core helpers. The legacy CLI can keep using
the same core behavior, but new integrations should prefer ActionRequest over
building command strings.
"""

from __future__ import annotations

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


def execute_action_request(request: ActionRequest, *, workspace: Workspace | Path | None = None) -> ActionResult:
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
    raise SystemExit(f"unsupported RKF action: {request.action}")
