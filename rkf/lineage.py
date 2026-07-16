"""Append-only, path-redacted project/activation/action lineage for RKF v1."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ID_RE = re.compile(r"^prj_[a-f0-9]{24}$")
ACTIVATION_ID_RE = re.compile(r"^act_[a-f0-9]{24}$")
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
FORBIDDEN_TRACE_KEYS = {
    "article_text",
    "cookie",
    "credentials",
    "password",
    "pdf_path",
    "private_drive_path",
    "private_path",
    "raw_prompt",
    "secret",
    "token",
}
SENSITIVE_FINGERPRINT_KEYS = FORBIDDEN_TRACE_KEYS | {
    "agent_note",
    "clip",
    "reader_note",
    "text",
}
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


class LineageStorageError(RuntimeError):
    """Raised when private lineage storage cannot be accessed safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_project_id() -> str:
    return f"prj_{uuid.uuid4().hex[:24]}"


def new_activation_id() -> str:
    return f"act_{uuid.uuid4().hex[:24]}"


def _fingerprint_shape(value: Any, *, key: str = "") -> Any:
    if key in SENSITIVE_FINGERPRINT_KEYS:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
        return {
            "redacted": True,
            "type": type(value).__name__,
            "value_sha256": hashlib.sha256(encoded).hexdigest(),
        }
    if isinstance(value, dict):
        return {
            str(item_key): _fingerprint_shape(item_value, key=str(item_key))
            for item_key, item_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_fingerprint_shape(item) for item in value]
    return value


def input_fingerprint(params: dict[str, Any]) -> str:
    encoded = json.dumps(
        _fingerprint_shape(params),
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def result_fingerprint(result: dict[str, Any]) -> str:
    """Fingerprint the durable outcome state and affected object identities.

    A request retry that returns the same status/result code is idempotent even
    when transport timing changes. A changed durable outcome (for example
    ``retryable`` to ``obtained`` or a different artifact) must append a
    successor event.
    """

    blocker_codes = result.get("blocker_codes", [])
    if not isinstance(blocker_codes, (list, tuple, set)):
        blocker_codes = [str(blocker_codes)]
    raw_object_fingerprints = result.get("object_fingerprints", {})
    object_fingerprints = (
        {
            str(object_id): str(fingerprint)
            for object_id, fingerprint in sorted(
                raw_object_fingerprints.items(), key=lambda item: str(item[0])
            )
        }
        if isinstance(raw_object_fingerprints, dict)
        else {}
    )
    durable_result = {
        "status": str(result.get("status", "")),
        "result_code": str(result.get("result_code", "")),
        "blocker_codes": sorted({str(item) for item in blocker_codes if str(item)}),
        "affected_object_ids": sorted(
            {
                str(item)
                for item in result.get("affected_object_ids", [])
                if str(item)
            }
        ),
        "promotion": str(result.get("promotion", "none")),
    }
    if object_fingerprints:
        durable_result["object_fingerprints"] = object_fingerprints
    return input_fingerprint(durable_result)


def _resolved_workspace_root(workspace_root: Path) -> Path:
    supplied = Path(workspace_root)
    if supplied.is_symlink():
        raise LineageStorageError("workspace root must not be a symlink")
    try:
        resolved = supplied.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise LineageStorageError("workspace root is unavailable") from exc
    if not resolved.is_dir():
        raise LineageStorageError("workspace root must be a directory")
    return resolved


def _assert_contained(workspace_root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(workspace_root)
    except ValueError as exc:
        raise LineageStorageError("lineage path escapes the workspace") from exc


def _validate_existing_directory_chain(workspace_root: Path, parts: tuple[str, ...]) -> None:
    current = workspace_root
    for part in parts:
        current = current / part
        _assert_contained(workspace_root, current)
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise LineageStorageError("lineage directory must not be a symlink")
        if not stat.S_ISDIR(metadata.st_mode):
            raise LineageStorageError("lineage path must contain directories only")
        try:
            current.resolve(strict=True).relative_to(workspace_root)
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise LineageStorageError("lineage directory escapes the workspace") from exc


def _lineage_location(workspace_root: Path) -> tuple[Path, Path, tuple[str, ...]]:
    workspace = _resolved_workspace_root(workspace_root)
    private_root = workspace / ".rkf_private"
    try:
        private_metadata = private_root.lstat()
    except FileNotFoundError:
        private_metadata = None
    if private_metadata is not None and stat.S_ISLNK(private_metadata.st_mode):
        parts = (".rkf_lineage",)
    else:
        parts = (".rkf_private", "lineage")
    _validate_existing_directory_chain(workspace, parts)
    root = workspace.joinpath(*parts)
    _assert_contained(workspace, root)
    return workspace, root, parts


def lineage_root(workspace_root: Path) -> Path:
    """Return the private lineage root after fail-closed path validation."""

    _, root, _ = _lineage_location(workspace_root)
    return root


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _file_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_child_directory(parent_fd: int, name: str, *, create: bool) -> int | None:
    if not name or Path(name).name != name or name in {".", ".."}:
        raise LineageStorageError("invalid lineage directory component")
    flags = _directory_open_flags()
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            return None
        try:
            os.mkdir(name, PRIVATE_DIRECTORY_MODE, dir_fd=parent_fd)
        except FileExistsError:
            pass
        try:
            descriptor = os.open(name, flags, dir_fd=parent_fd)
        except OSError as exc:
            raise LineageStorageError("cannot create a safe lineage directory") from exc
    except OSError as exc:
        raise LineageStorageError("lineage directory is unsafe") from exc
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise LineageStorageError("lineage path must contain directories only")
    if os.name == "posix":
        try:
            os.fchmod(descriptor, PRIVATE_DIRECTORY_MODE)
        except OSError as exc:
            os.close(descriptor)
            raise LineageStorageError("cannot restrict lineage directory permissions") from exc
    return descriptor


def _open_lineage_directory(
    workspace_root: Path,
    subdirectory: str,
    *,
    create: bool,
) -> tuple[Path, int | None]:
    workspace, root, parts = _lineage_location(workspace_root)
    if not subdirectory or Path(subdirectory).name != subdirectory:
        raise LineageStorageError("invalid lineage subdirectory")
    desired = root / subdirectory
    _assert_contained(workspace, desired)
    try:
        current_fd = os.open(workspace, _directory_open_flags())
    except OSError as exc:
        raise LineageStorageError("cannot open workspace boundary") from exc
    current_path = workspace
    try:
        for part in (*parts, subdirectory):
            child_fd = _open_child_directory(current_fd, part, create=create)
            if child_fd is None:
                os.close(current_fd)
                return desired, None
            os.close(current_fd)
            current_fd = child_fd
            current_path = current_path / part
        try:
            current_path.resolve(strict=True).relative_to(workspace)
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise LineageStorageError("lineage directory escapes the workspace") from exc
        return desired, current_fd
    except Exception:
        try:
            os.close(current_fd)
        except OSError:
            pass
        raise


def _validate_event_filename(filename: str) -> None:
    if not filename or Path(filename).name != filename or not filename.endswith(".json"):
        raise LineageStorageError("invalid lineage event filename")


def _read_json_at(directory_fd: int, filename: str) -> dict[str, Any] | None:
    _validate_event_filename(filename)
    try:
        before = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LineageStorageError("cannot inspect lineage event") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise LineageStorageError("lineage event must be a regular non-symlink file")
    if before.st_nlink != 1:
        raise LineageStorageError("lineage event must not be hard-linked")
    try:
        descriptor = os.open(filename, _file_open_flags(), dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LineageStorageError("cannot safely open lineage event") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LineageStorageError("lineage event must be a private regular file")
        if os.name == "posix":
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            payload = json.load(handle)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(payload, dict):
        raise LineageStorageError("lineage event must contain a JSON object")
    return payload


def _iter_json_at(directory_fd: int) -> list[tuple[str, dict[str, Any]]]:
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as exc:
        raise LineageStorageError("cannot list lineage events") from exc
    events: list[tuple[str, dict[str, Any]]] = []
    for name in names:
        if not name.endswith(".json"):
            continue
        payload = _read_json_at(directory_fd, name)
        if payload is not None:
            events.append((name, payload))
    return events


def _write_json_temp(directory_fd: int, filename: str, payload: dict[str, Any]) -> str:
    temporary_name = f".{filename}.{uuid.uuid4().hex}.tmp"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(temporary_name, flags, PRIVATE_FILE_MODE, dir_fd=directory_fd)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, PRIVATE_FILE_MODE)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = -1
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except Exception:
        _unlink_at(directory_fd, temporary_name)
        raise
    return temporary_name


def _unlink_at(directory_fd: int, filename: str) -> None:
    try:
        os.unlink(filename, dir_fd=directory_fd)
    except FileNotFoundError:
        pass


def _write_once(directory_fd: int, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_trace_value(payload)
    filename = path.name
    _validate_event_filename(filename)
    existing = _read_json_at(directory_fd, filename)
    if existing is not None:
        if existing != payload:
            raise RuntimeError("lineage event id collision")
        return existing
    temporary_name = _write_json_temp(directory_fd, filename, payload)
    try:
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            existing = _read_json_at(directory_fd, filename)
            if existing != payload:
                raise RuntimeError("lineage event id collision")
            return existing
        return payload
    finally:
        _unlink_at(directory_fd, temporary_name)


def _replace_json(
    directory_fd: int,
    path: Path,
    *,
    previous: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    filename = path.name
    _validate_event_filename(filename)
    temporary_name = _write_json_temp(directory_fd, filename, payload)
    try:
        current = _read_json_at(directory_fd, filename)
        if current is None:
            raise FileNotFoundError(str(path))
        if current != previous:
            raise RuntimeError("activation snapshot changed during update")
        os.replace(
            temporary_name,
            filename,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        _unlink_at(directory_fd, temporary_name)


def _validate_trace_value(value: Any, *, key: str = "") -> None:
    if key.casefold() in FORBIDDEN_TRACE_KEYS:
        raise ValueError(f"lineage excludes private field: {key}")
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            _validate_trace_value(item_value, key=str(item_key))
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_trace_value(item, key=key)
        return
    if isinstance(value, Path):
        raise ValueError("lineage excludes filesystem paths")
    if isinstance(value, str) and (
        value.startswith("/") or WINDOWS_ABSOLUTE_PATH_RE.match(value)
    ):
        raise ValueError("lineage excludes absolute paths")


def record_activation_transition(workspace_root: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    activation_id = str(payload.get("activation_id", ""))
    project_id = str(payload.get("project_id", ""))
    transition = str(payload.get("transition", ""))
    if not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("invalid activation_id")
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("invalid project_id")
    if transition not in {"started", "closed", "expired", "failed"}:
        raise ValueError("invalid activation transition")
    timestamp = str(payload.get("timestamp") or utc_now())
    event_id = "actevt_" + hashlib.sha256(
        f"{activation_id}\0{transition}".encode("utf-8")
    ).hexdigest()[:24]
    safe = {
        **payload,
        "schema": "rkf-activation-event-v1",
        "event_id": event_id,
        "timestamp": timestamp,
        "paths_redacted": True,
    }
    root, directory_fd = _open_lineage_directory(
        workspace_root,
        "activation_events",
        create=True,
    )
    if directory_fd is None:  # pragma: no cover - create=True guarantees a descriptor
        raise LineageStorageError("cannot create activation event storage")
    path = root / f"{event_id}.json"
    try:
        stored = _write_once(directory_fd, path, safe)
    finally:
        os.close(directory_fd)
    return path, stored


def record_activation(workspace_root: Path, payload: dict[str, Any]) -> Path:
    """Record an immutable activation-start snapshot and append-only transition."""

    activation_id = str(payload.get("activation_id", ""))
    project_id = str(payload.get("project_id", ""))
    if not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("invalid activation_id")
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("invalid project_id")
    started_at = str(payload.get("started_at") or utc_now())
    safe = {
        **payload,
        "schema": "rkf-activation-snapshot-v1",
        "started_at": started_at,
        "paths_redacted": True,
    }
    root, directory_fd = _open_lineage_directory(
        workspace_root,
        "activations",
        create=True,
    )
    if directory_fd is None:  # pragma: no cover - create=True guarantees a descriptor
        raise LineageStorageError("cannot create activation snapshot storage")
    path = root / f"{activation_id}.json"
    try:
        _write_once(directory_fd, path, safe)
    finally:
        os.close(directory_fd)
    record_activation_transition(
        workspace_root,
        {
            "activation_id": activation_id,
            "project_id": project_id,
            "project_name": str(payload.get("project_name", "")),
            "timestamp": started_at,
            "transition": "started" if payload.get("result") != "failed" else "failed",
            "mode": str(payload.get("mode", "OFF")),
            "marker_schema": str(payload.get("marker_schema", "")),
            "connector_version": str(payload.get("connector_version", "")),
            "rkf_version": str(payload.get("rkf_version", "")),
            "blocker_codes": sorted(set(payload.get("blocker_codes", []))),
        },
    )
    return path


def close_activation(
    workspace_root: Path,
    *,
    activation_id: str,
    project_id: str,
    project_name: str,
    ended_at: str,
    transition: str = "closed",
) -> dict[str, Any]:
    _, event = record_activation_transition(
        workspace_root,
        {
            "activation_id": activation_id,
            "project_id": project_id,
            "project_name": project_name,
            "timestamp": ended_at,
            "transition": transition,
            "mode": "OFF",
            "blocker_codes": [],
        },
    )
    return event


def update_activation(workspace_root: Path, activation_id: str, **updates: Any) -> dict[str, Any]:
    """Compatibility helper for migration-only callers.

    New v1 runtime code must use ``close_activation`` so activation history stays
    append-only. This helper remains until the migration backup window closes.
    """

    if not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("invalid activation_id")
    root, directory_fd = _open_lineage_directory(
        workspace_root,
        "activations",
        create=False,
    )
    path = root / f"{activation_id}.json"
    if directory_fd is None:
        raise FileNotFoundError(str(path))
    try:
        current = _read_json_at(directory_fd, path.name)
        if current is None:
            raise FileNotFoundError(str(path))
        previous = dict(current)
        current.update(updates)
        _validate_trace_value(current)
        _replace_json(
            directory_fd,
            path,
            previous=previous,
            payload=current,
        )
    finally:
        os.close(directory_fd)
    return current


def record_action(workspace_root: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    activation_id = str(payload.get("activation_id", ""))
    project_id = str(payload.get("origin_project_id", ""))
    if not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("invalid activation_id")
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("invalid origin_project_id")
    fingerprint = str(payload.get("input_fingerprint") or input_fingerprint(payload))
    if not FINGERPRINT_RE.fullmatch(fingerprint):
        raise ValueError("invalid input_fingerprint")
    idempotency_key = str(payload.get("idempotency_key") or fingerprint)
    if not idempotency_key:
        raise ValueError("idempotency_key is required")
    affected = payload.get("affected_object_ids", [])
    if not isinstance(affected, list) or not all(isinstance(item, str) for item in affected):
        raise ValueError("affected_object_ids must be a string list")
    raw_object_fingerprints = payload.get("object_fingerprints", {})
    if not isinstance(raw_object_fingerprints, dict) or not all(
        isinstance(object_id, str)
        and isinstance(object_fingerprint, str)
        and FINGERPRINT_RE.fullmatch(object_fingerprint)
        for object_id, object_fingerprint in raw_object_fingerprints.items()
    ):
        raise ValueError("object_fingerprints must map string ids to sha256 fingerprints")
    if not set(raw_object_fingerprints).issubset(set(affected)):
        raise ValueError("object_fingerprints keys must be affected_object_ids")
    object_fingerprints = {
        object_id: raw_object_fingerprints[object_id]
        for object_id in sorted(raw_object_fingerprints)
    }
    outcome_fingerprint = str(payload.get("result_fingerprint") or result_fingerprint(payload))
    if not FINGERPRINT_RE.fullmatch(outcome_fingerprint):
        raise ValueError("invalid result_fingerprint")
    root, directory_fd = _open_lineage_directory(
        workspace_root,
        "actions",
        create=True,
    )
    if directory_fd is None:  # pragma: no cover - create=True guarantees a descriptor
        raise LineageStorageError("cannot create action event storage")
    prior: list[tuple[Path, dict[str, Any]]] = []
    try:
        for filename, event in _iter_json_at(directory_fd):
            if (
                event.get("activation_id") == activation_id
                and event.get("idempotency_key") == idempotency_key
            ):
                prior.append((root / filename, event))
        latest_path: Path | None = None
        latest_event: dict[str, Any] | None = None
        if prior:
            latest_path, latest_event = max(prior, key=lambda item: _action_attempt_key(item[1]))
            existing_fingerprint = str(
                latest_event.get("result_fingerprint") or result_fingerprint(latest_event)
            )
            if existing_fingerprint == outcome_fingerprint:
                return latest_path, latest_event
        attempt = max((_action_attempt_number(event) for _, event in prior), default=0) + 1
        supersedes_event_id = str(latest_event.get("event_id", "")) if latest_event else ""
        if latest_event is None:
            event_identity = f"{activation_id}\0{idempotency_key}"
        else:
            event_identity = (
                f"{activation_id}\0{idempotency_key}\0{attempt}\0"
                f"{supersedes_event_id}\0{outcome_fingerprint}"
            )
        event_id = "aevt_" + hashlib.sha256(event_identity.encode("utf-8")).hexdigest()[:24]
        safe = {
            **payload,
            "schema": "rkf-action-event-v1",
            "event_id": event_id,
            "input_fingerprint": fingerprint,
            "idempotency_key": idempotency_key,
            "result_fingerprint": outcome_fingerprint,
            "attempt": attempt,
            "supersedes_event_id": supersedes_event_id,
            "affected_object_ids": list(dict.fromkeys(affected)),
            "object_fingerprints": object_fingerprints,
            "paths_redacted": True,
        }
        path = root / f"{event_id}.json"
        stored = _write_once(directory_fd, path, safe)
        return path, stored
    finally:
        os.close(directory_fd)


def _action_attempt_number(event: dict[str, Any]) -> int:
    try:
        return max(1, int(event.get("attempt", 1)))
    except (TypeError, ValueError):
        return 1


def _action_attempt_key(event: dict[str, Any]) -> tuple[int, str, str]:
    return (
        _action_attempt_number(event),
        str(event.get("timestamp", "")),
        str(event.get("event_id", "")),
    )


def _effective_action_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        key = (
            str(event.get("activation_id", "")),
            str(event.get("idempotency_key") or event.get("event_id", "")),
        )
        current = latest.get(key)
        if current is None or _action_attempt_key(event) > _action_attempt_key(current):
            latest[key] = event
    return list(latest.values())


def activity_timeline(
    workspace_root: Path,
    *,
    project_id: str = "",
    activation_id: str = "",
    action: str = "",
    status: str = "",
    target_object_id: str = "",
    effective_only: bool = False,
) -> list[dict[str, Any]]:
    _, directory_fd = _open_lineage_directory(
        workspace_root,
        "actions",
        create=False,
    )
    if directory_fd is None:
        return []
    events: list[dict[str, Any]] = []
    try:
        for _, event in _iter_json_at(directory_fd):
            if project_id and event.get("origin_project_id") != project_id:
                continue
            if activation_id and event.get("activation_id") != activation_id:
                continue
            if action and event.get("action") != action:
                continue
            events.append(event)
    finally:
        os.close(directory_fd)
    if effective_only:
        events = _effective_action_events(events)
    filtered: list[dict[str, Any]] = []
    for event in events:
        if status and event.get("status") != status:
            continue
        if target_object_id and target_object_id not in event.get("affected_object_ids", []):
            continue
        filtered.append(event)
    return sorted(
        filtered,
        key=lambda item: (
            str(item.get("timestamp", "")),
            _action_attempt_number(item),
            str(item.get("event_id", "")),
        ),
    )


def activation_timeline(
    workspace_root: Path,
    *,
    project_id: str = "",
    activation_id: str = "",
) -> list[dict[str, Any]]:
    _, directory_fd = _open_lineage_directory(
        workspace_root,
        "activation_events",
        create=False,
    )
    if directory_fd is None:
        return []
    events: list[dict[str, Any]] = []
    try:
        for _, event in _iter_json_at(directory_fd):
            if project_id and event.get("project_id") != project_id:
                continue
            if activation_id and event.get("activation_id") != activation_id:
                continue
            events.append(event)
    finally:
        os.close(directory_fd)
    return sorted(events, key=lambda item: (str(item.get("timestamp", "")), str(item.get("event_id", ""))))


def open_activation_projects(
    workspace_root: Path,
    *,
    current_activation_id: str = "",
) -> list[dict[str, Any]]:
    """Summarize projects whose latest activation transition is ``started``.

    Activation is task-scoped, so this is an append-only lineage view rather
    than a process-liveness probe. An interrupted task can remain open until a
    later closure or expiry event is recorded.
    """

    if current_activation_id and not ACTIVATION_ID_RE.fullmatch(current_activation_id):
        raise ValueError("invalid current_activation_id")
    latest_by_activation: dict[str, dict[str, Any]] = {}
    for event in activation_timeline(workspace_root):
        activation_id = str(event.get("activation_id", ""))
        project_id = str(event.get("project_id", ""))
        transition = str(event.get("transition", ""))
        if not ACTIVATION_ID_RE.fullmatch(activation_id):
            raise ValueError("invalid activation_id in activation lineage")
        if not PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError("invalid project_id in activation lineage")
        if transition not in {"started", "closed", "expired", "failed"}:
            raise ValueError("invalid transition in activation lineage")
        latest_by_activation[activation_id] = event

    projects: dict[str, dict[str, Any]] = {}
    for activation_id, event in latest_by_activation.items():
        if event.get("transition") != "started":
            continue
        mode = str(event.get("mode", ""))
        if mode not in {"ACTIVE", "ACTIVE_READ_ONLY"}:
            continue
        project_id = str(event["project_id"])
        project_name = str(event.get("project_name", ""))
        started_at = str(event.get("timestamp", ""))
        project = projects.setdefault(
            project_id,
            {
                "project_id": project_id,
                "project_name": project_name,
                "open_activation_count": 0,
                "modes": set(),
                "latest_started_at": "",
                "includes_current_task": False,
                "paths_redacted": True,
            },
        )
        project["open_activation_count"] += 1
        project["modes"].add(mode)
        project["latest_started_at"] = max(project["latest_started_at"], started_at)
        project["includes_current_task"] = (
            project["includes_current_task"]
            or activation_id == current_activation_id
        )

    summaries: list[dict[str, Any]] = []
    for project in projects.values():
        summary = dict(project)
        summary["modes"] = sorted(project["modes"])
        _validate_trace_value(summary)
        summaries.append(summary)
    return sorted(
        summaries,
        key=lambda item: (
            str(item["latest_started_at"]),
            str(item["project_name"]),
            str(item["project_id"]),
        ),
        reverse=True,
    )


def object_origin_lookup(
    workspace_root: Path,
    object_id: str,
    *,
    effective_only: bool = False,
) -> list[dict[str, Any]]:
    if not object_id.strip():
        raise ValueError("object_id is required")
    return activity_timeline(
        workspace_root,
        target_object_id=object_id.strip(),
        effective_only=effective_only,
    )
