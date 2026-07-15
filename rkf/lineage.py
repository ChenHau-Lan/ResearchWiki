"""Append-only, path-redacted project/activation/action lineage for RKF v1."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ID_RE = re.compile(r"^prj_[a-f0-9]{24}$")
ACTIVATION_ID_RE = re.compile(r"^act_[a-f0-9]{24}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_project_id() -> str:
    return f"prj_{uuid.uuid4().hex[:24]}"


def new_activation_id() -> str:
    return f"act_{uuid.uuid4().hex[:24]}"


def input_fingerprint(params: dict[str, Any]) -> str:
    safe_shape = {
        key: value
        for key, value in params.items()
        if key not in {"raw_prompt", "text", "clip", "reader_note", "agent_note"}
    }
    encoded = json.dumps(safe_shape, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def lineage_root(workspace_root: Path) -> Path:
    private_root = workspace_root / ".rkf_private"
    if private_root.is_symlink():
        return workspace_root / ".rkf_lineage"
    return private_root / "lineage"


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != payload:
                raise RuntimeError("lineage event id collision")
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        temporary.unlink(missing_ok=True)


def record_activation(workspace_root: Path, payload: dict[str, Any]) -> Path:
    activation_id = str(payload["activation_id"])
    if not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("invalid activation_id")
    safe = {**payload, "schema": "rkf-activation-event-v1", "paths_redacted": True}
    path = lineage_root(workspace_root) / "activations" / f"{activation_id}.json"
    _write_once(path, safe)
    return path


def update_activation(workspace_root: Path, activation_id: str, **updates: Any) -> dict[str, Any]:
    path = lineage_root(workspace_root) / "activations" / f"{activation_id}.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    current.update(updates)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(current, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return current


def record_action(workspace_root: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    activation_id = str(payload["activation_id"])
    idempotency_key = str(payload.get("idempotency_key") or input_fingerprint(payload))
    event_id = "aevt_" + hashlib.sha256(f"{activation_id}\0{idempotency_key}".encode()).hexdigest()[:24]
    safe = {
        **payload,
        "schema": "rkf-action-event-v1",
        "event_id": event_id,
        "idempotency_key": idempotency_key,
        "paths_redacted": True,
    }
    path = lineage_root(workspace_root) / "actions" / f"{event_id}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        return path, existing
    _write_once(path, safe)
    return path, safe


def activity_timeline(workspace_root: Path, *, project_id: str = "", activation_id: str = "") -> list[dict[str, Any]]:
    root = lineage_root(workspace_root) / "actions"
    events: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        event = json.loads(path.read_text(encoding="utf-8"))
        if project_id and event.get("origin_project_id") != project_id:
            continue
        if activation_id and event.get("activation_id") != activation_id:
            continue
        events.append(event)
    return sorted(events, key=lambda item: str(item.get("timestamp", "")))
