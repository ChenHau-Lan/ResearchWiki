"""Shared-workspace safety checks and named-file write primitives for RKF."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .core import Workspace


CONFLICT_NAME_RE = re.compile(
    r"conflicted copy|conflict copy|sync-conflict|\.sync-conflict",
    re.IGNORECASE,
)
SUPPORTED_SCHEMA_VERSIONS = {"", "rkf-v1", "rkf-v1.1"}
DEFAULT_STALE_HOURS = 48
SAFE_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SAFE_RECEIPT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*$")


def _safe_receipt_id(value: Any) -> str:
    """Return a deliberately narrow public-safe logical identifier."""

    candidate = str(value)
    return candidate if SAFE_RECEIPT_ID_RE.fullmatch(candidate) else "redacted"


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    """Keep doctor receipts useful without serializing untrusted path-like values."""

    safe: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, (bool, int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = _safe_receipt_id(value)
        else:
            safe[key] = "redacted"
    return safe


@dataclass(frozen=True)
class DoctorFinding:
    code: str
    severity: str
    message: str
    details: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "details": _safe_details(self.details),
        }


@dataclass(frozen=True)
class DoctorReport:
    checked_at: str
    roots: dict[str, dict[str, bool]]
    writer: dict[str, str]
    findings: tuple[DoctorFinding, ...]

    @property
    def status(self) -> str:
        if any(item.severity == "blocker" for item in self.findings):
            return "blocked"
        if self.findings:
            return "warning"
        return "ok"

    def as_payload(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at,
            "status": self.status,
            "roots": {name: dict(status) for name, status in self.roots.items()},
            "writer": dict(self.writer),
            "findings": [item.as_payload() for item in self.findings],
        }


@dataclass(frozen=True)
class AtomicWriteResult:
    written: bool
    reason: str
    previous_checksum: str
    output_checksum: str


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 checksum without loading large source files at once."""

    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _root_status(path: Path) -> dict[str, bool]:
    is_directory = path.is_dir()
    return {"exists": is_directory, "readable": is_directory and os.access(path, os.R_OK)}


def _sync_config(ws: Workspace) -> dict[str, Any]:
    config = ws.config.get("sync", {}) if isinstance(ws.config, dict) else {}
    return config if isinstance(config, dict) else {}


def writer_registry_path(ws: Workspace) -> Path:
    configured = _sync_config(ws).get("writer_registry")
    if isinstance(configured, str) and configured.strip():
        candidate = Path(os.path.expanduser(configured))
        return candidate.resolve() if candidate.is_absolute() else (ws.paths.wiki_root / candidate).resolve()
    return ws.paths.sync_state / "maintenance-writer.json"


def _machine_config(ws: Workspace) -> tuple[str, bool]:
    machine = ws.config.get("machine", {}) if isinstance(ws.config, dict) else {}
    if not isinstance(machine, dict):
        return "", False
    return str(machine.get("id", "")).strip(), bool(machine.get("maintenance_writer", False))


def _registry_writer_state(ws: Workspace) -> tuple[dict[str, str], list[DoctorFinding]]:
    machine_id, requested_writer = _machine_config(ws)
    state = {"role": "unknown", "machine": "configured" if machine_id else "missing"}
    findings: list[DoctorFinding] = []
    if not machine_id:
        findings.append(DoctorFinding("MACHINE_ID_MISSING", "blocker", "Machine identity is not configured.", {}))
        return state, findings
    path = writer_registry_path(ws)
    if not path.exists():
        state["role"] = "unregistered"
        if requested_writer:
            findings.append(
                DoctorFinding("WRITER_REGISTRY_MISSING", "blocker", "Maintenance writer is not registered.", {})
            )
        return state, findings
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        findings.append(DoctorFinding("WRITER_REGISTRY_INVALID", "blocker", "Writer registry is unreadable.", {}))
        state["role"] = "conflict"
        return state, findings
    registered = registry.get("machine_id") if isinstance(registry, dict) else None
    assigned_at = registry.get("assigned_at") if isinstance(registry, dict) else None
    valid = (
        isinstance(registry, dict)
        and set(registry) == {"schema", "machine_id", "assigned_at"}
        and registry.get("schema") == "rkf-writer-registry-v1"
        and isinstance(registered, str)
        and bool(re.fullmatch(r"[a-z0-9-]+", registered))
        and isinstance(assigned_at, str)
    )
    if valid:
        try:
            parsed = datetime.fromisoformat(assigned_at.replace("Z", "+00:00"))
            valid = parsed.tzinfo is not None
        except ValueError:
            valid = False
    if not valid:
        findings.append(DoctorFinding("WRITER_REGISTRY_INVALID", "blocker", "Writer registry schema is invalid.", {}))
        state["role"] = "conflict"
        return state, findings
    if requested_writer and registered == machine_id:
        state["role"] = "designated"
    elif requested_writer:
        state["role"] = "conflict"
        findings.append(
            DoctorFinding(
                "WRITER_REGISTRY_MISMATCH",
                "blocker",
                "Configured maintenance writer does not match the shared registry.",
                {},
            )
        )
    else:
        state["role"] = "other"
    return state, findings


def _conflict_findings(*roots: Path) -> list[DoctorFinding]:
    count = 0
    checked: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in checked or not root.exists():
            continue
        checked.add(resolved)
        count += sum(1 for path in root.rglob("*") if path.is_file() and CONFLICT_NAME_RE.search(path.name))
    if not count:
        return []
    return [
        DoctorFinding(
            "SYNC_CONFLICT",
            "blocker",
            "Potential cloud-sync conflict copies were found.",
            {"count": count},
        )
    ]


def _safe_raw_storage_path(raw_root: Path, value: Any) -> Path | None:
    """Resolve an evidence storage reference only when it stays under raw_root."""

    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return None
    resolved = (raw_root / candidate).resolve()
    try:
        resolved.relative_to(raw_root.resolve())
    except ValueError:
        return None
    return resolved


def _governed_pdf_identity_map(ws: Workspace) -> tuple[dict[Path, set[str]], list[DoctorFinding], int]:
    """Map raw PDFs to governed source IDs, never inferring identity from names."""

    mapped: dict[Path, set[str]] = {}
    findings: list[DoctorFinding] = []
    unverified_count = 0
    root = ws.paths.evidence_index
    if not root.exists():
        return mapped, findings, unverified_count
    for path in sorted(root.glob("*.json")):
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            findings.append(DoctorFinding("EVIDENCE_RECORD_INVALID", "blocker", "Evidence record is unreadable.", {}))
            continue
        if not isinstance(artifact, dict) or artifact.get("artifact_type") != "pdf":
            continue
        source_id = str(artifact.get("source_id") or "")
        raw_path = _safe_raw_storage_path(ws.paths.raw_root, artifact.get("storage_path"))
        if not SAFE_SOURCE_ID_RE.fullmatch(source_id) or raw_path is None:
            unverified_count += 1
            continue
        mapped.setdefault(raw_path, set()).add(source_id)
    for identities in mapped.values():
        if len(identities) > 1:
            findings.append(
                DoctorFinding(
                    "PDF_IDENTITY_CONFLICT",
                    "blocker",
                    "One raw PDF is mapped to multiple governed source identities.",
                    {"identity_count": len(identities)},
                )
            )
    return mapped, findings, unverified_count


def _pdf_findings(ws: Workspace) -> list[DoctorFinding]:
    raw_root = ws.paths.raw_root
    if not raw_root.exists():
        return []
    mapped, findings, record_unverified_count = _governed_pdf_identity_map(ws)
    groups: dict[str, set[str]] = {}
    raw_unverified_count = 0
    for path in raw_root.rglob("*.pdf"):
        if not path.is_file():
            continue
        identities = mapped.get(path.resolve(), set())
        if len(identities) != 1:
            raw_unverified_count += 1
            continue
        identity = next(iter(identities))
        groups.setdefault(identity, set()).add(sha256_file(path))
    unverified_count = max(record_unverified_count, raw_unverified_count)
    if unverified_count:
        findings.append(
            DoctorFinding(
                "PDF_IDENTITY_UNVERIFIED",
                "warning",
                "Some raw PDFs have no governed source-identity mapping.",
                {"count": unverified_count},
            )
        )
    findings.extend(
        DoctorFinding(
            "PDF_CHECKSUM_CONFLICT",
            "blocker",
            "One source identity has divergent PDF checksums.",
            {"identity": _safe_receipt_id(identity), "checksum_count": len(checksums)},
        )
        for identity, checksums in sorted(groups.items())
        if len(checksums) > 1
    )
    return findings


def _stale_aggregate_findings(ws: Workspace, now: datetime) -> list[DoctorFinding]:
    status_path = ws.paths.sync_state / "aggregate-status.json"
    if not status_path.exists():
        return []
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return [DoctorFinding("AGGREGATE_STATUS_INVALID", "blocker", "Aggregate status is unreadable.", {})]
    items = payload.get("aggregates", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return [DoctorFinding("AGGREGATE_STATUS_INVALID", "blocker", "Aggregate status format is invalid.", {})]
    cadence_hours = int(_sync_config(ws).get("aggregate_cadence_hours", 24) or 24)
    stale_after_hours = max(cadence_hours * 2, DEFAULT_STALE_HOURS if cadence_hours == 24 else cadence_hours * 2)
    findings: list[DoctorFinding] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("generated_at"), str):
            findings.append(DoctorFinding("AGGREGATE_STATUS_INVALID", "blocker", "Aggregate timestamp is invalid.", {}))
            continue
        try:
            generated = datetime.fromisoformat(item["generated_at"].replace("Z", "+00:00"))
            current = now.astimezone(generated.tzinfo) if generated.tzinfo else now.replace(tzinfo=None)
        except ValueError:
            findings.append(DoctorFinding("AGGREGATE_STATUS_INVALID", "blocker", "Aggregate timestamp is invalid.", {}))
            continue
        age_hours = (current - generated).total_seconds() / 3600
        if age_hours > stale_after_hours:
            findings.append(
                DoctorFinding(
                    "STALE_AGGREGATE",
                    "warning",
                    "A generated aggregate is older than its allowed cadence.",
                    {"logical_id": _safe_receipt_id(item.get("logical_id", "aggregate")), "age_hours": int(age_hours)},
                )
            )
    return findings


def run_connect_doctor(ws: Workspace, *, now: datetime | None = None) -> DoctorReport:
    """Inspect shared-workspace safety without creating or changing any file."""

    checked = now or datetime.now()
    roots = {
        "wiki_root": _root_status(ws.paths.wiki_root),
        "raw_root": _root_status(ws.paths.raw_root),
    }
    findings: list[DoctorFinding] = []
    for name, status in roots.items():
        if not status["exists"] or not status["readable"]:
            findings.append(DoctorFinding("ROOT_UNAVAILABLE", "blocker", "Configured storage root is unavailable.", {"root": name}))
    writer, writer_findings = _registry_writer_state(ws)
    findings.extend(writer_findings)
    knowledge = ws.config.get("knowledge", {}) if isinstance(ws.config, dict) else {}
    schema = str(knowledge.get("schema_version", "")) if isinstance(knowledge, dict) else ""
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        findings.append(DoctorFinding("SCHEMA_INCOMPATIBLE", "blocker", "Knowledge schema version is incompatible.", {}))
    findings.extend(_conflict_findings(ws.paths.wiki_root, ws.paths.raw_root))
    findings.extend(_pdf_findings(ws))
    findings.extend(_stale_aggregate_findings(ws, checked))
    return DoctorReport(
        checked_at=checked.isoformat(timespec="seconds"),
        roots=roots,
        writer=writer,
        findings=tuple(findings),
    )


def atomic_write_text(path: Path, text: str, *, expected_checksum: str | None) -> AtomicWriteResult:
    """Replace one named text file only when its expected checksum still matches."""

    previous = sha256_file(path) if path.exists() else ""
    if expected_checksum is not None and previous != expected_checksum:
        return AtomicWriteResult(False, "checksum-mismatch", previous, previous)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        output = sha256_file(path)
        expected_output = sha256(text.encode("utf-8")).hexdigest()
        if output != expected_output:
            return AtomicWriteResult(False, "post-write-checksum-mismatch", previous, output)
        return AtomicWriteResult(True, "ok", previous, output)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
