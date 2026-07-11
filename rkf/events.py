"""Immutable public-safe operational events for cross-machine RKF capture."""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import LOCAL_PATH_PATTERNS, Workspace, read_json


EVENT_SCHEMA = "rkf-operational-event-v1"
MAX_EVENT_BYTES = 16_384
ALLOWED_ACTIONS = {"capture.route", "capture.review"}
ALLOWED_ACTORS = {"codex", "human", "codex-handoff", "automation"}
SENSITIVE_RE = re.compile(
    r"\b(api[_ -]?key|access[_ -]?token|password|private[_ -]?key|secret)\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LOCAL_ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s=:(])(?:~[/\\]|/(?!/)[^\s\"']+|[A-Z]:[/\\][^\s\"']+|\\\\[^\s\"']+)",
    re.IGNORECASE,
)
COMMON_TOKEN_RE = re.compile(
    r"\b(?:sk-(?:proj-)?|ghp_|github_pat_|xox[baprs]-)[A-Z0-9_-]{12,}\b|"
    r"\bAKIA[A-Z0-9]{16}\b|\bBearer\s+[A-Z0-9._~-]{12,}",
    re.IGNORECASE,
)
HIGH_ENTROPY_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]{32,}\b)(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+\b"
)
EVENT_ID_RE = re.compile(r"^evt_[0-9]{8}T[0-9]{6}Z_[a-z0-9-]+_[a-z0-9]+$")
MACHINE_ID_RE = re.compile(r"^[a-z0-9-]+$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


@dataclass(frozen=True)
class OperationalEvent:
    schema: str
    event_id: str
    action: str
    actor: str
    origin: str
    machine_id: str
    created: str
    target_identity: str
    idempotency_key: str
    public_safe: bool
    payload: dict[str, Any]


def _safe_machine_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not normalized:
        raise SystemExit("operational event requires machine_id")
    return normalized


def _strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            result.extend([str(key), *_strings(item)])
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_strings(item))
        return result
    return [value] if isinstance(value, str) else []


def public_safety_violations(value: Any) -> list[str]:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    violations: list[str] = []
    if SENSITIVE_RE.search(serialized):
        violations.append("sensitive-material")
    strings = _strings(value)
    if any(EMAIL_RE.search(item) for item in strings):
        violations.append("personal-data")
    if any(
        LOCAL_ABSOLUTE_PATH_RE.search(item)
        or item.strip().lower().startswith("file://")
        or any(pattern.search(item) for pattern in LOCAL_PATH_PATTERNS)
        for item in strings
    ):
        violations.append("private-path")
    if any(
        COMMON_TOKEN_RE.search(item)
        or (
            HIGH_ENTROPY_RE.search(item)
            and not item.startswith("evt_")
            and not re.fullmatch(r"[0-9a-f]{32,}", item)
        )
        for item in strings
    ):
        if "sensitive-material" not in violations:
            violations.append("sensitive-material")
    return violations


def valid_event_envelope(event: dict[str, Any]) -> bool:
    required = {
        "schema",
        "event_id",
        "action",
        "actor",
        "origin",
        "machine_id",
        "created",
        "target_identity",
        "idempotency_key",
        "public_safe",
        "payload",
    }
    if set(event) != required:
        return False
    if event.get("schema") != EVENT_SCHEMA:
        return False
    if not isinstance(event.get("event_id"), str) or not EVENT_ID_RE.fullmatch(event["event_id"]):
        return False
    if event.get("action") not in ALLOWED_ACTIONS or event.get("actor") not in ALLOWED_ACTORS:
        return False
    for key in ("origin", "machine_id", "created", "target_identity", "idempotency_key"):
        if not isinstance(event.get(key), str) or not event[key].strip():
            return False
    if not MACHINE_ID_RE.fullmatch(event["machine_id"]):
        return False
    if not RFC3339_RE.fullmatch(event["created"]):
        return False
    try:
        parsed_created = datetime.fromisoformat(event["created"].replace("Z", "+00:00"))
        if parsed_created.tzinfo is None:
            return False
    except ValueError:
        return False
    if event.get("public_safe") is not True or not isinstance(event.get("payload"), dict):
        return False
    return not public_safety_violations(event)


def _assert_public_safe(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(serialized.encode("utf-8")) > MAX_EVENT_BYTES:
        raise SystemExit("operational event payload is too large")
    violations = public_safety_violations(payload)
    if violations:
        raise SystemExit(
            "operational event is not public-safe: " + ",".join(violations)
        )


def build_operational_event(
    *,
    action: str,
    actor: str,
    origin: str,
    machine_id: str,
    target_identity: str,
    idempotency_key: str,
    payload: dict[str, Any],
    created: datetime | None = None,
    nonce: str = "",
) -> OperationalEvent:
    if action not in ALLOWED_ACTIONS:
        raise SystemExit(f"unsupported operational event action: {action}")
    if actor not in ALLOWED_ACTORS:
        raise SystemExit(f"unsupported operational event actor: {actor}")
    if not origin.strip() or not target_identity.strip() or not idempotency_key.strip():
        raise SystemExit("operational event origin, target identity, and idempotency key are required")
    _assert_public_safe(
        {
            "action": action,
            "actor": actor,
            "origin": origin,
            "machine_id": machine_id,
            "target_identity": target_identity,
            "idempotency_key": idempotency_key,
            "payload": payload,
        }
    )
    instant = created or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise SystemExit("operational event created time requires a timezone")
    instant = instant.astimezone(timezone.utc)
    machine = _safe_machine_id(machine_id)
    raw_suffix = nonce or secrets.token_hex(6)
    suffix = re.sub(r"[^a-z0-9]+", "", raw_suffix.lower()) or secrets.token_hex(6)
    event_id = f"evt_{instant.strftime('%Y%m%dT%H%M%SZ')}_{machine}_{suffix}"
    event = OperationalEvent(
        schema=EVENT_SCHEMA,
        event_id=event_id,
        action=action,
        actor=actor,
        origin=origin.strip(),
        machine_id=machine,
        created=instant.isoformat().replace("+00:00", "Z"),
        target_identity=target_identity.strip(),
        idempotency_key=idempotency_key.strip(),
        public_safe=True,
        payload=payload,
    )
    if not valid_event_envelope(asdict(event)):
        raise SystemExit("operational event envelope is invalid or unsafe")
    return event


def write_operational_event(ws: Workspace, event: OperationalEvent) -> Path:
    event_day = event.created[:10]
    destination = ws.paths.events / event_day / f"{event.event_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(asdict(event), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    temporary = destination.with_name(
        f".{destination.name}.tmp-{secrets.token_hex(6)}"
    )
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_operational_events(ws: Workspace) -> list[dict[str, Any]]:
    if not ws.paths.events.exists():
        return []
    events: list[dict[str, Any]] = []
    for path in sorted(ws.paths.events.rglob("evt_*.json")):
        try:
            event = read_json(path)
        except (OSError, ValueError, TypeError):
            continue
        if not valid_event_envelope(event):
            continue
        events.append(event)
    return events


def load_recent_operational_events(
    ws: Workspace,
    *,
    since: datetime,
) -> list[dict[str, Any]]:
    cutoff = since.astimezone(timezone.utc)
    return [
        event
        for event in load_operational_events(ws)
        if datetime.fromisoformat(str(event["created"]).replace("Z", "+00:00"))
        >= cutoff
    ]
