"""Session-scoped activation and read-only RKF preflight checks."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from datetime import datetime

from .core import Workspace, load_toml, read_json


SUPPORTED_SCHEMA_VERSIONS = {"", "rkf-v1", "rkf-v1.1"}
CONFLICT_NAME_RE = re.compile(
    r"conflicted copy|conflict copy|sync-conflict|\.sync-conflict",
    re.IGNORECASE,
)


class SessionMode(str, Enum):
    OFF = "OFF"
    PREFLIGHT = "PREFLIGHT"
    ACTIVE = "ACTIVE"
    ACTIVE_READ_ONLY = "ACTIVE_READ_ONLY"


@dataclass(frozen=True)
class ProjectPolicy:
    version: int
    available: bool
    activation: str
    query_first: bool
    capture_mode: str


@dataclass
class SessionState:
    session_id: str
    mode: SessionMode = SessionMode.OFF
    query_first: bool = False
    capture_mode: str = "off"
    machine_id: str = ""
    writer_role: str = "unknown"
    warnings: list[str] = field(default_factory=list)


def new_session(session_id: str = "") -> SessionState:
    return SessionState(session_id=session_id or f"task-{uuid.uuid4().hex[:12]}")


def read_project_policy(project_root: Path | None) -> ProjectPolicy:
    if project_root is None:
        return ProjectPolicy(0, True, "manual", True, "active-aggressive")
    marker = project_root / ".rkf-connect.toml"
    try:
        data = load_toml(marker)
    except (OSError, ValueError, TypeError):
        return ProjectPolicy(0, False, "manual", True, "off")
    if not data:
        return ProjectPolicy(0, True, "manual", True, "active-aggressive")
    try:
        version = int(data.get("version", 1))
        if version not in {1, 2}:
            raise ValueError
        if version == 2:
            section = data.get("rkf", {})
            if not isinstance(section, dict):
                raise ValueError
            available = section.get("available", False)
            query_first = section.get("query_first", True)
            activation = section.get("activation", "manual")
            capture_mode = section.get("capture_mode", "active-aggressive")
            if (
                not isinstance(available, bool)
                or not isinstance(query_first, bool)
                or activation != "manual"
                or capture_mode not in {"active-aggressive", "active", "off"}
            ):
                raise ValueError
            return ProjectPolicy(version, available, activation, query_first, capture_mode)
        legacy = data.get("rkf_auto_connect", {})
        if not isinstance(legacy, dict) or not isinstance(legacy.get("enabled", False), bool):
            raise ValueError
        legacy_mode = legacy.get("mode", "active-aggressive")
        if legacy_mode not in {"active-aggressive", "active", "off"}:
            raise ValueError
        return ProjectPolicy(
            version=1,
            available=legacy.get("enabled", False),
            activation="manual",
            query_first=True,
            capture_mode=str(legacy_mode),
        )
    except (TypeError, ValueError):
        return ProjectPolicy(0, False, "manual", True, "off")


def _root_status(path: Path) -> dict[str, bool]:
    return {
        "exists": path.exists(),
        "readable": path.exists() and os.access(path, os.R_OK),
    }


def _conflicts(wiki_root: Path) -> list[str]:
    if not wiki_root.exists():
        return []
    return [
        path.name
        for path in wiki_root.rglob("*")
        if path.is_file() and CONFLICT_NAME_RE.search(path.name)
    ]


def _machine_state(ws: Workspace) -> tuple[str, bool]:
    section = ws.config.get("machine", {}) if isinstance(ws.config, dict) else {}
    if not isinstance(section, dict):
        return "", False
    return str(section.get("id", "")).strip(), bool(section.get("maintenance_writer", False))


def _writer_role(ws: Workspace, machine_id: str, requested_writer: bool) -> str:
    registry_path = ws.paths.sync_state / "maintenance-writer.json"
    if not registry_path.exists():
        return "unregistered"
    try:
        registry = read_json(registry_path)
    except (OSError, ValueError, TypeError):
        return "conflict"
    registered = registry.get("machine_id")
    assigned_at = registry.get("assigned_at")
    if (
        set(registry) != {"schema", "machine_id", "assigned_at"}
        or registry.get("schema") != "rkf-writer-registry-v1"
        or not isinstance(registered, str)
        or not re.fullmatch(r"[a-z0-9-]+", registered)
        or not isinstance(assigned_at, str)
    ):
        return "conflict"
    try:
        parsed = datetime.fromisoformat(assigned_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return "conflict"
    except ValueError:
        return "conflict"
    if requested_writer and registered == machine_id:
        return "designated"
    if requested_writer and registered != machine_id:
        return "conflict"
    return "other"


def session_receipt(session: SessionState) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "mode": session.mode.value,
        "query_first": session.query_first,
        "capture_mode": session.capture_mode,
        "writer_role": session.writer_role,
        "warnings": list(session.warnings),
    }


def activate_session(
    session: SessionState,
    ws: Workspace,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    session.mode = SessionMode.PREFLIGHT
    policy = read_project_policy(project_root)
    if not policy.available:
        session.mode = SessionMode.OFF
        return {**session_receipt(session), "error_code": "RKF_PROJECT_UNAVAILABLE"}

    roots = {
        "wiki_root": _root_status(ws.paths.wiki_root),
        "raw_root": _root_status(ws.paths.raw_root),
    }
    if not all(value["exists"] and value["readable"] for value in roots.values()):
        session.mode = SessionMode.OFF
        return {
            **session_receipt(session),
            "roots": roots,
            "error_code": "RKF_PREFLIGHT_FAILED",
        }

    machine_id, requested_writer = _machine_state(ws)
    knowledge = ws.config.get("knowledge", {}) if isinstance(ws.config, dict) else {}
    schema = str(knowledge.get("schema_version", "")) if isinstance(knowledge, dict) else ""
    warnings: list[str] = []
    if not machine_id:
        warnings.append("MACHINE_ID_MISSING")
    if _conflicts(ws.paths.wiki_root):
        warnings.append("SYNC_CONFLICT")
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        warnings.append("SCHEMA_INCOMPATIBLE")

    session.query_first = policy.query_first
    session.capture_mode = policy.capture_mode
    session.machine_id = machine_id
    session.writer_role = (
        _writer_role(ws, machine_id, requested_writer) if machine_id else "unknown"
    )
    if session.writer_role == "conflict":
        warnings.append("WRITER_REGISTRY_MISMATCH")
    session.warnings = warnings
    blocking_read_only = {
        "MACHINE_ID_MISSING",
        "SYNC_CONFLICT",
        "SCHEMA_INCOMPATIBLE",
        "WRITER_REGISTRY_MISMATCH",
    }
    session.mode = (
        SessionMode.ACTIVE_READ_ONLY
        if blocking_read_only.intersection(warnings)
        else SessionMode.ACTIVE
    )
    return {
        **session_receipt(session),
        "roots": roots,
        "project_available": policy.available,
    }


def deactivate_session(session: SessionState) -> dict[str, Any]:
    session.mode = SessionMode.OFF
    session.query_first = False
    session.capture_mode = "off"
    session.machine_id = ""
    session.writer_role = "unknown"
    session.warnings = []
    return session_receipt(session)
