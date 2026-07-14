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
from .lineage import PROJECT_ID_RE, new_activation_id, utc_now
from .sync import run_connect_doctor


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
    project_id: str = ""
    project_name: str = ""
    marker_schema: str = ""
    connector_version: str = ""


@dataclass
class SessionState:
    session_id: str
    mode: SessionMode = SessionMode.OFF
    query_first: bool = False
    capture_mode: str = "off"
    machine_id: str = ""
    writer_role: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    project_id: str = ""
    project_name: str = ""
    activation_id: str = ""
    started_at: str = ""
    ended_at: str = ""


def new_session(session_id: str = "") -> SessionState:
    return SessionState(session_id=session_id or f"task-{uuid.uuid4().hex[:12]}")


def read_project_policy(project_root: Path | None) -> ProjectPolicy:
    if project_root is None:
        return ProjectPolicy(
            0, True, "manual", True, "active-aggressive",
            project_id="prj_000000000000000000000000",
            project_name="ResearchWiki",
            marker_schema="local",
            connector_version="builtin",
        )
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
            project_id = section.get("project_id", "")
            project_name = section.get("project_name", project_root.name)
            marker_schema = section.get("marker_schema", "rkf-connect-v2")
            connector_version = section.get("connector_version", "unknown")
            if (
                not isinstance(available, bool)
                or not isinstance(query_first, bool)
                or activation != "manual"
                or capture_mode not in {"active-aggressive", "active", "off"}
                or not isinstance(project_id, str)
                or not isinstance(project_name, str)
                or (bool(project_id) and PROJECT_ID_RE.fullmatch(project_id) is None)
            ):
                raise ValueError
            return ProjectPolicy(
                version, available, activation, query_first, capture_mode,
                project_id=project_id,
                project_name=project_name,
                marker_schema=str(marker_schema),
                connector_version=str(connector_version),
            )
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
            project_name=project_root.name,
            marker_schema="rkf-connect-v1-legacy",
            connector_version="legacy",
        )
    except (TypeError, ValueError):
        return ProjectPolicy(0, False, "manual", True, "off")


def _root_status(path: Path) -> dict[str, bool]:
    is_directory = path.is_dir()
    return {
        "exists": is_directory,
        "readable": is_directory and os.access(path, os.R_OK),
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
        "project_id": session.project_id,
        "project_name": session.project_name,
        "activation_id": session.activation_id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "paths_redacted": True,
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

    session.query_first = policy.query_first
    session.capture_mode = policy.capture_mode
    session.project_id = policy.project_id or f"prj_{uuid.uuid5(uuid.NAMESPACE_URL, 'rkf-project:' + (project_root.name if project_root else 'ResearchWiki')).hex[:24]}"
    session.project_name = policy.project_name
    session.activation_id = new_activation_id()
    session.started_at = utc_now()
    session.ended_at = ""
    session.warnings = []
    if project_root is not None and not policy.project_id:
        doctor = run_connect_doctor(ws)
        machine_id, _requested_writer = _machine_state(ws)
        warnings = [finding.code for finding in doctor.findings]
        if any(code.startswith("WRITER_REGISTRY_") for code in warnings):
            warnings.append("WRITER_REGISTRY_MISMATCH")
        warnings.append("LEGACY_PROJECT_ID_DERIVED_FROM_NAME")
        session.machine_id = machine_id
        session.writer_role = str(doctor.writer.get("role", "unknown"))
        session.warnings = list(dict.fromkeys(warnings))
        session.mode = SessionMode.ACTIVE_READ_ONLY if doctor.status == "blocked" else SessionMode.ACTIVE
    else:
        session.machine_id = "local"
        session.writer_role = "local"
        session.mode = SessionMode.ACTIVE
    return {
        **session_receipt(session),
        "roots": roots,
        "project_available": policy.available,
        "marker_schema": policy.marker_schema,
        "connector_version": policy.connector_version,
    }


def deactivate_session(session: SessionState) -> dict[str, Any]:
    session.ended_at = utc_now()
    session.mode = SessionMode.OFF
    session.query_first = False
    session.capture_mode = "off"
    session.machine_id = ""
    session.writer_role = "unknown"
    return session_receipt(session)
