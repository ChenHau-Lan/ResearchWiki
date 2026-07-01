"""Structured RKF action API for Codex app workflows.

This module is the app-facing runtime layer between natural-language Codex
workflows and the lower-level RKF core helpers. The legacy CLI can keep using
the same core behavior, but new integrations should prefer ActionRequest over
building command strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import (
    Workspace,
    create_inbox_item,
    record_hot_query,
    refresh_hot_markdown,
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


def execute_action_request(request: ActionRequest, *, workspace: Workspace | Path | None = None) -> ActionResult:
    params = dict(request.params)
    if request.action == "inbox.capture":
        return capture_inbox(workspace=workspace, **params)
    if request.action == "hot.record":
        return record_hot(workspace=workspace, **params)
    raise SystemExit(f"unsupported RKF action: {request.action}")
