"""Optional provider contracts for RKF v1; implementations remain adapters.

The default runtime has no browser, institutional-login, vector-database, or
external-LLM dependency. Providers return typed, public-safe envelopes that are
mapped into canonical RKF objects by the five v1 workflows.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol, Sequence

from .core import Workspace, frontmatter, parse_frontmatter
from .lineage import ACTIVATION_ID_RE, PROJECT_ID_RE, utc_now
from .processes import run_bounded_process
from .schema import (
    ACCESS_STATES,
    APPRAISAL_STATUSES,
    PROVIDER_STATUSES,
    REVIEW_STATES,
    normalize_paper_state,
)


ABSOLUTE_PROVIDER_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
ACQUISITION_RUN_ID_RE = re.compile(r"^acq_[a-f0-9]{24}$")
RELATED_ARTIFACT_ID_RE = re.compile(r"^rel_[a-f0-9]{24}$")
ACQUISITION_ATTEMPT_STATUSES = frozenset((*PROVIDER_STATUSES, "resolved", "no-result"))
RELATED_ARTIFACT_TYPES = frozenset(
    {
        "publisher-html",
        "jats-xml",
        "preprint",
        "supplement",
        "figure",
        "table",
        "dataset-link",
        "software-link",
        "correction",
        "retraction-notice",
        "report",
        "pdf",
    }
)
ARTIFACT_RELATIONSHIPS = frozenset(
    {"related", "is-version-of", "supplements", "corrects", "retracts"}
)
RELATED_POINTER_RE = re.compile(r"^(?:url|doi)-sha256:[a-f0-9]{16,64}$")


@dataclass(frozen=True)
class AcquisitionAttempt:
    """One public-safe route outcome within an acquisition run."""

    route: str
    status: str
    reason_code: str = ""
    host: str = ""
    http_status: int = 0
    elapsed_ms: int = 0

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,95}", self.route):
            raise ValueError("acquisition attempt route is invalid")
        if self.status not in ACQUISITION_ATTEMPT_STATUSES:
            raise ValueError(f"invalid acquisition attempt status: {self.status}")
        if self.reason_code and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,127}", self.reason_code):
            raise ValueError("acquisition attempt reason code is invalid")
        if self.host and (
            "/" in self.host
            or "\\" in self.host
            or "@" in self.host
            or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", self.host)
        ):
            raise ValueError("acquisition attempt host must be a public-safe hostname")
        if self.http_status < 0 or self.http_status > 599:
            raise ValueError("acquisition attempt HTTP status is invalid")
        if self.elapsed_ms < 0:
            raise ValueError("acquisition attempt elapsed_ms cannot be negative")

    def public_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullTextProviderResult:
    status: str
    provider: str
    provider_version: str
    route: str = ""
    tried_routes: tuple[str, ...] = ()
    artifact_sha256: str = ""
    private_artifact_handle: str = ""
    elapsed_ms: int = 0
    entitlement_state: str = "unknown"
    pdf_magic_validated: bool = False
    blocker_codes: tuple[str, ...] = ()
    acquisition_run_id: str = ""
    identifier_types: tuple[str, ...] = ()
    attempts: tuple[AcquisitionAttempt, ...] = ()
    artifact_type: str = "pdf"
    artifact_version: str = "unknown"
    artifact_license: str = ""
    source_host: str = ""
    byte_count: int = 0
    mime_type: str = ""
    quality_state: str = "pending"
    identity_state: str = "unverified"
    page_count: int = 0
    text_layer_state: str = "unknown"
    locator_readiness: str = "unknown"
    related_artifacts: tuple[dict[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.status not in PROVIDER_STATUSES:
            raise ValueError(f"invalid provider status: {self.status}")
        if not self.provider.strip() or not self.provider_version.strip():
            raise ValueError("provider and provider_version are required")
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative")
        if self.entitlement_state not in {"unknown", "covered", "not-covered"}:
            raise ValueError("invalid entitlement_state")
        if self.acquisition_run_id and not ACQUISITION_RUN_ID_RE.fullmatch(self.acquisition_run_id):
            raise ValueError("invalid acquisition_run_id")
        if self.byte_count < 0 or self.page_count < 0:
            raise ValueError("artifact byte/page counts cannot be negative")
        if self.artifact_type not in {
            "version-of-record-pdf",
            "accepted-manuscript",
            "preprint",
            "publisher-html",
            "jats-xml",
            "supplement",
            "figure",
            "table",
            "dataset-link",
            "software-link",
            "correction",
            "retraction-notice",
            "report",
            "pdf",
        }:
            raise ValueError("invalid artifact_type")
        if self.artifact_version not in {
            "version-of-record",
            "accepted-manuscript",
            "preprint",
            "unknown",
        }:
            raise ValueError("invalid artifact_version")
        if self.quality_state not in {
            "pending",
            "readable",
            "partial",
            "ocr-required",
            "corrupt",
            "identity-mismatch",
        }:
            raise ValueError("invalid artifact quality_state")
        if self.identity_state not in {"verified", "unverified", "mismatch"}:
            raise ValueError("invalid artifact identity_state")
        if self.text_layer_state not in {"available", "missing", "unknown"}:
            raise ValueError("invalid artifact text_layer_state")
        if self.locator_readiness not in {"ready", "partial", "not-ready", "unknown"}:
            raise ValueError("invalid artifact locator_readiness")
        if self.source_host and (
            "/" in self.source_host
            or "\\" in self.source_host
            or "@" in self.source_host
            or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", self.source_host)
        ):
            raise ValueError("source_host must be a public-safe hostname")
        if any(not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", item) for item in self.identifier_types):
            raise ValueError("invalid canonical identifier type")
        for relation in self.related_artifacts:
            if not isinstance(relation, dict) or set(relation) - {
                "relationship",
                "artifact_type",
                "host",
                "identifier",
            }:
                raise ValueError("related artifact exceeds the public-safe contract")
            if relation.get("host") and not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", relation["host"]):
                raise ValueError("related artifact host is invalid")
            if relation.get("relationship") not in ARTIFACT_RELATIONSHIPS:
                raise ValueError("related artifact relationship is invalid")
            if relation.get("artifact_type") not in RELATED_ARTIFACT_TYPES:
                raise ValueError("related artifact type is invalid")
            if not RELATED_POINTER_RE.fullmatch(str(relation.get("identifier", ""))):
                raise ValueError("related artifact identifier must be a public-safe fingerprint")
        if self.artifact_sha256 and (
            len(self.artifact_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.artifact_sha256)
        ):
            raise ValueError("artifact_sha256 must be a lowercase SHA-256 digest")
        if self.status == "obtained" and (not self.artifact_sha256 or not self.pdf_magic_validated):
            raise ValueError("obtained provider result requires artifact_sha256 and PDF magic validation")
        if self.status == "obtained" and self.quality_state in {"corrupt", "identity-mismatch"}:
            raise ValueError("obtained provider result cannot contain a rejected artifact")
        if any(
            ABSOLUTE_PROVIDER_PATH_RE.match(value.strip())
            for value in (self.route, *self.tried_routes)
            if value
        ):
            raise ValueError("public provider routes cannot contain absolute paths")

    def public_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("private_artifact_handle", None)
        payload["tried_routes"] = list(self.tried_routes)
        payload["blocker_codes"] = list(self.blocker_codes)
        payload["identifier_types"] = list(self.identifier_types)
        payload["attempts"] = [attempt.public_payload() for attempt in self.attempts]
        payload["related_artifacts"] = [dict(item) for item in self.related_artifacts]
        payload["private_artifact_available"] = bool(self.private_artifact_handle)
        return payload


def ensure_acquisition_run_id(
    result: FullTextProviderResult,
    *,
    identity: dict[str, str] | None = None,
) -> FullTextProviderResult:
    """Attach one run identity without changing an adapter's typed outcome."""

    if identity:
        seed = {
            "identity": identity,
            "status": result.status,
            "provider": result.provider,
            "provider_version": result.provider_version,
            "route": result.route,
            "tried_routes": result.tried_routes,
            "artifact_sha256": result.artifact_sha256,
            "blocker_codes": result.blocker_codes,
        }
        if result.acquisition_run_id:
            seed["provider_acquisition_run_id"] = result.acquisition_run_id
        digest = hashlib.sha256(
            json.dumps(seed, ensure_ascii=True, sort_keys=True).encode("utf-8")
        ).hexdigest()[:24]
        return replace(result, acquisition_run_id=f"acq_{digest}")
    if result.acquisition_run_id:
        return result
    return replace(result, acquisition_run_id=f"acq_{uuid.uuid4().hex[:24]}")


def _acquisition_run_semantic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove volatile timings before checking an idempotent run collision."""

    semantic = {
        key: value
        for key, value in payload.items()
        if key not in {"created", "elapsed_ms"}
    }
    semantic["attempts"] = [
        {
            key: value
            for key, value in attempt.items()
            if key != "elapsed_ms"
        }
        for attempt in payload.get("attempts", [])
        if isinstance(attempt, dict)
    ]
    return semantic


class FullTextProvider(Protocol):
    def obtain(
        self,
        *,
        source_id: str,
        identifier: str,
        project_id: str,
        activation_id: str,
    ) -> FullTextProviderResult: ...


class ExternalCommandFullTextProvider:
    """Minimal JSON adapter for an explicitly configured local command.

    The adapter uses ``shell=False`` and never persists command configuration,
    credentials, stderr, or private paths into public RKF state.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        provider: str = "external-command",
        provider_version: str = "unknown",
        timeout_seconds: int = 300,
        max_stdout_bytes: int = 1024 * 1024,
        max_stderr_bytes: int = 256 * 1024,
    ) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("external provider command must be a non-empty string sequence")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if min(max_stdout_bytes, max_stderr_bytes) <= 0:
            raise ValueError("external provider output limits must be positive")
        self.command = tuple(command)
        self.provider = provider
        self.provider_version = provider_version
        self.timeout_seconds = timeout_seconds
        self.max_stdout_bytes = max_stdout_bytes
        self.max_stderr_bytes = max_stderr_bytes

    def obtain(
        self,
        *,
        source_id: str,
        identifier: str,
        project_id: str,
        activation_id: str,
    ) -> FullTextProviderResult:
        if not PROJECT_ID_RE.fullmatch(project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
            raise ValueError("external acquisition requires valid project/activation lineage")
        request = {
            "source_id": source_id,
            "identifier": identifier,
            "project_id": project_id,
            "activation_id": activation_id,
        }
        try:
            completed = run_bounded_process(
                self.command,
                input_text=json.dumps(request, ensure_ascii=True),
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=self.max_stdout_bytes,
                max_stderr_bytes=self.max_stderr_bytes,
            )
        except OSError:
            return FullTextProviderResult(
                status="provider-error",
                provider=self.provider,
                provider_version=self.provider_version,
                blocker_codes=("PROVIDER_EXECUTION_ERROR",),
            )
        if completed.timed_out:
            return FullTextProviderResult(
                status="retryable",
                provider=self.provider,
                provider_version=self.provider_version,
                blocker_codes=("PROVIDER_TIMEOUT",),
            )
        if completed.stdout_overflow or completed.stderr_overflow:
            return FullTextProviderResult(
                status="blocked",
                provider=self.provider,
                provider_version=self.provider_version,
                blocker_codes=(
                    "PROVIDER_STDOUT_LIMIT" if completed.stdout_overflow else "PROVIDER_STDERR_LIMIT",
                ),
            )
        try:
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict):
                raise ValueError
            status = str(payload.get("status", "blocked"))
            if status not in PROVIDER_STATUSES:
                status = "blocked"
                blocker_codes = ("PROVIDER_STATUS_INVALID",)
            else:
                blocker_codes = tuple(str(item) for item in payload.get("blocker_codes", []))
            if completed.returncode != 0 and status == "obtained":
                status = "blocked"
                blocker_codes = (*blocker_codes, "PROVIDER_EXIT_NONZERO")
            return FullTextProviderResult(
                status=status,
                provider=str(payload.get("provider") or self.provider),
                provider_version=str(payload.get("provider_version") or self.provider_version),
                route=str(payload.get("route", "")),
                tried_routes=tuple(str(item) for item in payload.get("tried_routes", [])),
                artifact_sha256=str(payload.get("artifact_sha256", "")),
                private_artifact_handle=str(payload.get("private_artifact_handle", "")),
                elapsed_ms=int(payload.get("elapsed_ms", 0)),
                entitlement_state=str(payload.get("entitlement_state", "unknown")),
                pdf_magic_validated=payload.get("pdf_magic_validated") is True,
                blocker_codes=tuple(dict.fromkeys(blocker_codes)),
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return FullTextProviderResult(
                status="blocked",
                provider=self.provider,
                provider_version=self.provider_version,
                blocker_codes=("PROVIDER_OUTPUT_INVALID",),
            )


def _artifact_relation_ids(paper_id: str) -> tuple[str, str]:
    """Return canonical Paper and source IDs for one artifact relation."""

    logical_id = paper_id.removeprefix("knowledge/").removesuffix(".md").strip()
    parts = logical_id.split("/")
    if len(parts) < 2 or parts[0] != "papers" or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("artifact paper_id must be a logical papers/<id> identifier")
    return logical_id, logical_id.removeprefix("papers/")


def _merge_artifact_relation(
    payload: dict[str, Any],
    *,
    array_key: str,
    legacy_key: str,
    current: str,
) -> list[str]:
    """Merge an optional v1 relation array with its legacy singular mirror."""

    raw_values = payload.get(array_key, [])
    if not isinstance(raw_values, list) or any(
        not isinstance(value, str) or not value.strip() for value in raw_values
    ):
        raise ValueError(f"existing artifact {array_key} must be an array of non-empty strings")
    values = list(dict.fromkeys(value.strip() for value in raw_values))
    legacy_value = payload.get(legacy_key)
    if legacy_value is not None:
        if not isinstance(legacy_value, str) or not legacy_value.strip():
            raise ValueError(f"existing artifact {legacy_key} must be a non-empty string")
        if legacy_value.strip() not in values:
            values.append(legacy_value.strip())
    if current not in values:
        values.append(current)
    return values


def _path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _tighten_directory(path: Path, *, mode: int) -> None:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError("private artifact path must be a directory")
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _tighten_regular_file(path: Path, *, mode: int) -> None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("private artifact target must be a regular file")
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _atomic_write_artifact_json(
    path: Path,
    payload: dict[str, Any],
    *,
    mode: int,
    target_label: str,
) -> None:
    """Atomically replace one preflighted artifact JSON without following its target."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    descriptor_open = True
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor_open = False
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise ValueError(f"{target_label} target cannot be a symlink")
        os.replace(temporary, path)
    finally:
        if descriptor_open:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_artifact_json(path: Path, *, target_label: str) -> dict[str, Any]:
    """Read one regular artifact file without following a target symlink."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if path.is_symlink():
            raise ValueError(f"{target_label} target cannot be a symlink") from error
        raise
    descriptor_open = True
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"{target_label} target must be a regular file")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor_open = False
            payload = json.load(handle)
    finally:
        if descriptor_open:
            os.close(descriptor)
    if not isinstance(payload, dict):
        raise ValueError(f"{target_label} payload must be an object")
    return payload


def _public_artifact_path(ws: Workspace, artifact_id: str) -> Path:
    """Return a contained public artifact path only when no boundary is a symlink."""

    public_root = ws.paths.evidence_index
    parent = public_root / "artifacts"
    target = parent / f"{artifact_id}.json"
    for label, path in (
        ("root", public_root),
        ("parent", parent),
        ("target", target),
    ):
        if path.is_symlink():
            raise ValueError(f"public artifact {label} cannot be a symlink")
    if not _path_is_within(ws.paths.wiki_root, public_root):
        raise ValueError("public artifact root escaped the configured wiki root")
    if public_root.exists() and not public_root.is_dir():
        raise ValueError("public artifact root must be a directory")
    if parent.exists() and not parent.is_dir():
        raise ValueError("public artifact parent must be a directory")
    if target.exists() and not target.is_file():
        raise ValueError("public artifact target must be a regular file")
    public_root.mkdir(parents=True, exist_ok=True)
    parent.mkdir(mode=0o755, exist_ok=True)
    for label, path in (("root", public_root), ("parent", parent), ("target", target)):
        if path.is_symlink():
            raise ValueError(f"public artifact {label} cannot be a symlink")
    return target


def _private_artifact_path(ws: Workspace, artifact_id: str) -> Path:
    """Return a contained owner-only handle path with no symlink boundary."""

    private_root = ws.root / ".rkf_private"
    parent = private_root / "artifacts"
    target = parent / f"{artifact_id}.json"
    for label, path in (
        ("root", private_root),
        ("parent", parent),
        ("target", target),
    ):
        if path.is_symlink():
            raise ValueError(f"private artifact {label} cannot be a symlink")
    if not _path_is_within(ws.root, private_root):
        raise ValueError("private artifact root escaped the workspace")
    if private_root.exists() and not private_root.is_dir():
        raise ValueError("private artifact root must be a directory")
    if parent.exists() and not parent.is_dir():
        raise ValueError("private artifact parent must be a directory")
    if target.exists() and not target.is_file():
        raise ValueError("private artifact target must be a regular file")
    private_root.mkdir(mode=0o700, exist_ok=True)
    parent.mkdir(mode=0o700, exist_ok=True)
    for label, path in (("root", private_root), ("parent", parent), ("target", target)):
        if path.is_symlink():
            raise ValueError(f"private artifact {label} cannot be a symlink")
    _tighten_directory(private_root, mode=0o700)
    _tighten_directory(parent, mode=0o700)
    if target.exists():
        _tighten_regular_file(target, mode=0o600)
    return target


def _public_related_artifact_path(ws: Workspace, related_artifact_id: str) -> Path:
    if not RELATED_ARTIFACT_ID_RE.fullmatch(related_artifact_id):
        raise ValueError("related artifact ID is invalid")
    public_root = ws.paths.evidence_index
    parent = public_root / "artifacts" / "related"
    target = parent / f"{related_artifact_id}.json"
    for label, path in (("root", public_root), ("parent", parent), ("target", target)):
        if path.is_symlink():
            raise ValueError(f"related artifact {label} cannot be a symlink")
    if not _path_is_within(ws.paths.wiki_root, target):
        raise ValueError("related artifact path escaped the configured wiki root")
    public_root.mkdir(parents=True, exist_ok=True)
    parent.mkdir(parents=True, mode=0o755, exist_ok=True)
    if target.exists() and not target.is_file():
        raise ValueError("related artifact target must be a regular file")
    return target


def register_evidence_artifact(
    ws: Workspace,
    *,
    paper_id: str,
    result: FullTextProviderResult,
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    """Register one obtained artifact by checksum without exposing its handle."""

    if result.status != "obtained":
        raise ValueError("only obtained provider results can create an artifact")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("artifact registration requires valid project/activation lineage")
    artifact_id = "art_" + hashlib.sha256(result.artifact_sha256.encode("ascii")).hexdigest()[:24]
    paper_id, source_id = _artifact_relation_ids(paper_id)
    created = utc_now()
    public_payload = {
        "schema": "rkf-evidence-artifact-v1",
        "evidence_id": artifact_id,
        "artifact_id": artifact_id,
        "source_id": source_id,
        "paper_id": paper_id,
        "source_ids": [source_id],
        "paper_ids": [paper_id],
        "artifact_type": "pdf",
        "scientific_artifact_type": result.artifact_type,
        "artifact_version": result.artifact_version,
        "artifact_license": result.artifact_license,
        "status": result.status,
        "qc_status": "pending",
        "quality_state": result.quality_state,
        "identity_state": result.identity_state,
        "page_count": result.page_count,
        "text_layer_state": result.text_layer_state,
        "locator_readiness": result.locator_readiness,
        "sha256": result.artifact_sha256,
        "byte_count": result.byte_count,
        "mime_type": result.mime_type,
        "provider": result.provider,
        "provider_version": result.provider_version,
        "route": result.route,
        "authorized_route": result.route,
        "source_host": result.source_host,
        "acquisition_run_id": result.acquisition_run_id,
        "related_artifacts": [dict(item) for item in result.related_artifacts],
        "public_safe_pointer": f"artifact:{artifact_id}",
        "locators": [],
        "readability_state": "unreviewed",
        "locator_state": "unreviewed",
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "created": created,
        "updated": created,
        "public_safe": True,
    }
    public_path = _public_artifact_path(ws, artifact_id)
    if result.private_artifact_handle:
        private_payload = {
            "schema": "rkf-private-artifact-handle-v1",
            "artifact_id": artifact_id,
            "private_artifact_handle": result.private_artifact_handle,
        }
        private_path = _private_artifact_path(ws, artifact_id)
        if not private_path.exists():
            _atomic_write_artifact_json(
                private_path,
                private_payload,
                mode=0o600,
                target_label="private artifact",
            )
        else:
            _tighten_regular_file(private_path, mode=0o600)
    public_path = _public_artifact_path(ws, artifact_id)
    if public_path.exists():
        existing = _read_artifact_json(public_path, target_label="public artifact")
        if not isinstance(existing, dict) or existing.get("schema") != "rkf-evidence-artifact-v1":
            raise ValueError("existing checksum artifact has an invalid schema")
        if existing.get("evidence_id") != artifact_id or existing.get("artifact_id", artifact_id) != artifact_id:
            raise ValueError("existing checksum artifact identity does not match its path")
        existing_sha256 = existing.get("sha256")
        if existing_sha256 not in {None, "", result.artifact_sha256}:
            raise ValueError("existing checksum artifact digest does not match")
        existing["artifact_id"] = artifact_id
        existing["sha256"] = result.artifact_sha256
        existing["paper_ids"] = _merge_artifact_relation(
            existing,
            array_key="paper_ids",
            legacy_key="paper_id",
            current=paper_id,
        )
        existing["source_ids"] = _merge_artifact_relation(
            existing,
            array_key="source_ids",
            legacy_key="source_id",
            current=source_id,
        )
        # Singular fields remain a backward-compatible mirror of the relation
        # requested by this registration. Consumers that need every relation use
        # the canonical arrays above.
        existing["paper_id"] = paper_id
        existing["source_id"] = source_id
        existing["updated"] = created
        public_path = _public_artifact_path(ws, artifact_id)
        _atomic_write_artifact_json(
            public_path,
            existing,
            mode=0o644,
            target_label="public artifact",
        )
        return existing
    public_path = _public_artifact_path(ws, artifact_id)
    _atomic_write_artifact_json(
        public_path,
        public_payload,
        mode=0o644,
        target_label="public artifact",
    )
    return public_payload


def register_related_artifact_records(
    ws: Workspace,
    *,
    paper_id: str,
    result: FullTextProviderResult,
    origin_project_id: str,
    activation_id: str,
) -> list[dict[str, Any]]:
    """Register public-safe related pointers independently from the PDF record."""

    if result.status != "obtained":
        raise ValueError("related artifacts require an obtained source artifact")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("related artifact registration requires valid lineage")
    paper_id, _source_id = _artifact_relation_ids(paper_id)
    source_artifact_id = "art_" + hashlib.sha256(
        result.artifact_sha256.encode("ascii")
    ).hexdigest()[:24]
    records: list[dict[str, Any]] = []
    now = utc_now()
    for relation in result.related_artifacts:
        seed = {
            "artifact_type": relation["artifact_type"],
            "host": relation["host"],
            "identifier": relation["identifier"],
        }
        related_id = "rel_" + hashlib.sha256(
            json.dumps(seed, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()[:24]
        target = _public_related_artifact_path(ws, related_id)
        payload = {
            "schema": "rkf-related-artifact-v1",
            "related_artifact_id": related_id,
            "source_artifact_ids": [source_artifact_id],
            "paper_ids": [paper_id],
            "acquisition_run_ids": [result.acquisition_run_id],
            "relationship": relation["relationship"],
            "artifact_type": relation["artifact_type"],
            "host": relation["host"],
            "identifier_fingerprint": relation["identifier"],
            "registration_state": "pointer-only",
            "provenance_review_state": "pending",
            "provenance_gaps": ["relationship-validation", "artifact-identity"],
            "promotion": "none",
            "public_safe": True,
            "created": now,
            "updated": now,
        }
        if target.exists():
            existing = _read_artifact_json(target, target_label="related artifact")
            if (
                existing.get("schema") != "rkf-related-artifact-v1"
                or existing.get("related_artifact_id") != related_id
                or existing.get("identifier_fingerprint") != relation["identifier"]
            ):
                raise ValueError("existing related artifact has an identity collision")
            for key, value in (
                ("source_artifact_ids", source_artifact_id),
                ("paper_ids", paper_id),
                ("acquisition_run_ids", result.acquisition_run_id),
            ):
                values = existing.get(key, [])
                if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                    raise ValueError(f"existing related artifact {key} is invalid")
                existing[key] = list(dict.fromkeys((*values, value)))
            existing["updated"] = now
            payload = existing
        _atomic_write_artifact_json(
            target,
            payload,
            mode=0o644,
            target_label="related artifact",
        )
        records.append(payload)
    return records


def load_related_artifact_records(
    ws: Workspace,
    *,
    paper_id: str = "",
    review_state: str = "",
) -> list[dict[str, Any]]:
    root = ws.paths.evidence_index / "artifacts" / "related"
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir() or not _path_is_within(ws.paths.wiki_root, root):
        raise ValueError("related artifact collection is invalid")
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("rel_*.json")):
        if path.is_symlink() or not path.is_file() or not RELATED_ARTIFACT_ID_RE.fullmatch(path.stem):
            raise ValueError("related artifact collection contains an invalid entry")
        payload = _read_artifact_json(path, target_label="related artifact")
        if (
            payload.get("schema") != "rkf-related-artifact-v1"
            or payload.get("related_artifact_id") != path.stem
            or payload.get("public_safe") is not True
            or payload.get("promotion") != "none"
        ):
            raise ValueError(f"invalid related artifact: {path.stem}")
        if paper_id and paper_id not in payload.get("paper_ids", []):
            continue
        if review_state and payload.get("provenance_review_state") != review_state:
            continue
        records.append(payload)
    return records


def load_artifact_provenance_gaps(ws: Workspace) -> list[dict[str, Any]]:
    root = ws.paths.evidence_index / "artifacts"
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir() or not _path_is_within(ws.paths.wiki_root, root):
        raise ValueError("artifact collection is invalid")
    gaps: list[dict[str, Any]] = []
    for path in sorted(root.glob("art_*.json")):
        payload = _read_artifact_json(path, target_label="public artifact")
        if payload.get("schema") != "rkf-evidence-artifact-v1":
            raise ValueError(f"invalid public artifact: {path.stem}")
        missing: list[str] = []
        if payload.get("artifact_version") in {None, "", "unknown"}:
            missing.append("artifact-version")
        if not str(payload.get("artifact_license", "")).strip():
            missing.append("artifact-license")
        if missing:
            gaps.append(
                {
                    "artifact_id": payload.get("artifact_id", path.stem),
                    "paper_ids": list(payload.get("paper_ids", [])),
                    "missing": missing,
                    "next_action": "human-provenance-review",
                }
            )
    return gaps


def _acquisition_run_root(ws: Workspace) -> Path:
    private_root = ws.root / ".rkf_private"
    acquisition_root = private_root / "acquisition"
    run_root = acquisition_root / "runs"
    for label, path in (
        ("private root", private_root),
        ("acquisition root", acquisition_root),
        ("acquisition run root", run_root),
    ):
        if path.is_symlink():
            raise ValueError(f"{label} cannot be a symlink")
    if not _path_is_within(ws.root, run_root):
        raise ValueError("acquisition run root escaped the workspace")
    private_root.mkdir(mode=0o700, exist_ok=True)
    acquisition_root.mkdir(mode=0o700, exist_ok=True)
    run_root.mkdir(mode=0o700, exist_ok=True)
    for path in (private_root, acquisition_root, run_root):
        if path.is_symlink() or not path.is_dir():
            raise ValueError("acquisition run directory is invalid")
        _tighten_directory(path, mode=0o700)
    return run_root


def register_acquisition_run(
    ws: Workspace,
    *,
    result: FullTextProviderResult,
    identifier: str,
    source_id: str,
    paper_id: str,
    origin_project_id: str,
    activation_id: str,
    artifact_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Persist one path-redacted acquisition trace under private RKF state."""

    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("acquisition run requires valid project/activation lineage")
    result = ensure_acquisition_run_id(result)
    identifier_fingerprint = hashlib.sha256(identifier.strip().encode("utf-8")).hexdigest()
    created = utc_now()
    payload = {
        "schema": "rkf-acquisition-run-v1",
        "acquisition_run_id": result.acquisition_run_id,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "source_id": source_id,
        "paper_id": paper_id,
        "identifier_fingerprint": identifier_fingerprint,
        "identifier_types": list(result.identifier_types),
        "status": result.status,
        "provider": result.provider,
        "provider_version": result.provider_version,
        "selected_route": result.route,
        "attempts": [attempt.public_payload() for attempt in result.attempts],
        "entitlement_state": result.entitlement_state,
        "artifact_ids": list(dict.fromkeys(str(item) for item in artifact_ids if str(item))),
        "blocker_codes": list(result.blocker_codes),
        "elapsed_ms": result.elapsed_ms,
        "retry_class": (
            "serial-retry"
            if result.status == "retryable"
            else "manual"
            if result.status in {"manual-required", "not-entitled"}
            else "none"
        ),
        "promotion": "none",
        "paths_redacted": True,
        "public_safe": True,
        "created": created,
    }
    run_root = _acquisition_run_root(ws)
    target = run_root / f"{result.acquisition_run_id}.json"
    if target.is_symlink():
        raise ValueError("acquisition run target cannot be a symlink")
    if target.exists():
        existing = _read_artifact_json(target, target_label="acquisition run")
        existing_semantic = _acquisition_run_semantic_payload(existing)
        payload_semantic = _acquisition_run_semantic_payload(payload)
        if existing_semantic != payload_semantic:
            raise ValueError("acquisition run identity collision")
        return existing
    _atomic_write_artifact_json(
        target,
        payload,
        mode=0o600,
        target_label="acquisition run",
    )
    return payload


def load_acquisition_runs(
    ws: Workspace,
    *,
    project_id: str = "",
    activation_id: str = "",
    status: str = "",
    target_object_id: str = "",
) -> list[dict[str, Any]]:
    """Load private acquisition traces for Review without following symlinks."""

    root = ws.root / ".rkf_private" / "acquisition" / "runs"
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir() or not _path_is_within(ws.root, root):
        raise ValueError("acquisition run root is invalid")
    runs: list[dict[str, Any]] = []
    for path in sorted(root.glob("acq_*.json")):
        if path.is_symlink() or not path.is_file() or not ACQUISITION_RUN_ID_RE.fullmatch(path.stem):
            raise ValueError("acquisition run collection contains an invalid entry")
        payload = _read_artifact_json(path, target_label="acquisition run")
        if (
            payload.get("schema") != "rkf-acquisition-run-v1"
            or payload.get("acquisition_run_id") != path.stem
            or payload.get("paths_redacted") is not True
            or payload.get("public_safe") is not True
        ):
            raise ValueError(f"invalid acquisition run: {path.stem}")
        if project_id and payload.get("origin_project_id") != project_id:
            continue
        if activation_id and payload.get("activation_id") != activation_id:
            continue
        if status and payload.get("status") != status:
            continue
        if target_object_id and target_object_id not in {
            payload.get("source_id"),
            payload.get("paper_id"),
            *payload.get("artifact_ids", []),
        }:
            continue
        runs.append(payload)
    return runs


def summarize_acquisition_route_health(
    runs: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a path-free route scorecard from canonical acquisition attempts."""

    by_route: dict[str, dict[str, Any]] = {}
    for run in runs:
        created = str(run.get("created", ""))
        for attempt in run.get("attempts", []):
            if not isinstance(attempt, dict):
                continue
            route = str(attempt.get("route", ""))
            status = str(attempt.get("status", ""))
            if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,95}", route):
                continue
            entry = by_route.setdefault(
                route,
                {
                    "route": route,
                    "attempt_count": 0,
                    "obtained_count": 0,
                    "retryable_count": 0,
                    "manual_count": 0,
                    "last_observed": "",
                },
            )
            entry["attempt_count"] += 1
            entry["obtained_count"] += int(status == "obtained")
            entry["retryable_count"] += int(status == "retryable")
            entry["manual_count"] += int(status in {"manual-required", "not-entitled"})
            entry["last_observed"] = max(entry["last_observed"], created)
    return sorted(by_route.values(), key=lambda item: item["route"])


def validate_paper_access_target(ws: Workspace, *, paper_id: str) -> str:
    """Return a normalized Paper ID after a read-only path/type preflight."""

    if not isinstance(paper_id, str):
        raise ValueError("paper_id must be a logical papers/<id> identifier")
    logical_id = paper_id.removeprefix("knowledge/").removesuffix(".md").strip()
    if not logical_id.startswith("papers/") or ".." in logical_id.split("/"):
        raise ValueError("paper_id must be a logical papers/<id> identifier")
    knowledge_root = ws.paths.knowledge
    paper_root = knowledge_root / "papers"
    path = knowledge_root / f"{logical_id}.md"
    for label, candidate in (
        ("knowledge root", knowledge_root),
        ("paper root", paper_root),
        ("paper target", path),
    ):
        if candidate.is_symlink():
            raise ValueError(f"canonical {label} cannot be a symlink")
    current_parent = paper_root
    for part in path.relative_to(paper_root).parts[:-1]:
        current_parent = current_parent / part
        if current_parent.is_symlink():
            raise ValueError("canonical paper parent cannot be a symlink")
    if not _path_is_within(ws.paths.wiki_root, knowledge_root):
        raise ValueError("canonical knowledge root escaped the configured wiki root")
    if not _path_is_within(knowledge_root, paper_root) or not _path_is_within(paper_root, path):
        raise ValueError("paper_id escaped the canonical paper root")
    if not paper_root.is_dir() or not path.is_file():
        raise ValueError("obtained full text requires an existing canonical Paper")
    meta, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
    if meta.get("schema") != "rkf-paper-v1.1" or meta.get("type") != "paper":
        raise ValueError("paper_id does not identify a canonical Paper")
    if meta.get("access_state") not in ACCESS_STATES or meta.get("review_state") not in REVIEW_STATES:
        raise ValueError("canonical Paper access_state/review_state is missing or invalid")
    return logical_id


def update_paper_access_from_artifact(
    ws: Workspace,
    *,
    paper_id: str,
) -> dict[str, str]:
    """Atomically mark an existing canonical Paper as full-text available."""

    logical_id = validate_paper_access_target(ws, paper_id=paper_id)
    path = (ws.paths.knowledge / f"{logical_id}.md").resolve()
    before = path.read_bytes()
    meta, body = parse_frontmatter(before.decode("utf-8"))
    state = normalize_paper_state(meta)
    meta["access_state"] = "fulltext"
    meta["review_state"] = state["review_state"]
    meta["fulltext_status"] = "fulltext-available"
    legacy_mirror = {
        "unread": "fulltext-available",
        "skimmed": "first-pass-pdf-qc",
        "read": "fulltext-read",
        "annotated": "human-reviewed",
        "reproduced": "reproduced",
    }[state["review_state"]]
    if "reading_state" in meta or "reading_status" in meta:
        meta["reading_state"] = legacy_mirror
        meta["reading_status"] = legacy_mirror
    rendered = (frontmatter(meta) + body).encode("utf-8")
    if path.read_bytes() != before:
        raise RuntimeError("paper changed while applying acquisition result")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "paper_id": logical_id,
        "access_state": "fulltext",
        "review_state": state["review_state"],
    }


@dataclass(frozen=True)
class RetrievalHit:
    object_id: str
    locator: str = ""
    score: float = 0.0
    match_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.object_id.strip() or not self.match_reason.strip():
            raise ValueError("retrieval hit requires object_id and match_reason")
        if not isinstance(self.locator, str):
            raise ValueError("retrieval hit locator must be text")
        if not math.isfinite(float(self.score)) or float(self.score) < 0:
            raise ValueError("retrieval hit score must be finite and non-negative")
        if not isinstance(self.metadata, dict):
            raise ValueError("retrieval hit metadata must be an object")


class RetrievalProvider(Protocol):
    name: str
    version: str

    def search(
        self,
        *,
        query: str,
        limit: int = 10,
        project_id: str,
        activation_id: str,
        index_scope: str = "public-safe",
    ) -> list[RetrievalHit]: ...


class ExternalCommandRetrievalProvider:
    """Structured shell-free adapter for an optional local semantic index."""

    _METADATA_KEYS = {
        "object_type",
        "index_scope",
        "path",
        "title",
        "source_id",
        "reading_maturity",
        "evidence_boundary",
        "evidence_use",
        "claim_readiness",
        "missing",
        "summary",
    }

    def __init__(
        self,
        command: Sequence[str],
        *,
        name: str = "external-semantic",
        version: str = "unknown",
        timeout_seconds: int = 60,
    ) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("external retrieval command must be a non-empty string sequence")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(command)
        self.name = name
        self.version = version
        self.timeout_seconds = timeout_seconds
        self.index_generation = "unknown"
        self.elapsed_ms = 0

    def search(
        self,
        *,
        query: str,
        limit: int = 10,
        project_id: str,
        activation_id: str,
        index_scope: str = "public-safe",
    ) -> list[RetrievalHit]:
        if not PROJECT_ID_RE.fullmatch(project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
            raise ValueError("external retrieval requires valid project/activation lineage")
        if index_scope not in {"public-safe", "private-fulltext"}:
            raise ValueError("external retrieval index scope is invalid")
        try:
            completed = subprocess.run(
                self.command,
                input=json.dumps(
                    {
                        "query": query,
                        "limit": limit,
                        "project_id": project_id,
                        "activation_id": activation_id,
                        "index_scope": index_scope,
                    },
                    ensure_ascii=True,
                ),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            self.index_generation = "timeout"
            raise RuntimeError("external retrieval command timed out") from error
        if completed.returncode != 0:
            raise RuntimeError("external retrieval command failed")
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict) or not isinstance(payload.get("hits"), list):
            raise ValueError("external retrieval output is invalid")
        self.index_generation = str(payload.get("index_generation", "unknown"))[:128]
        self.elapsed_ms = max(0, int(payload.get("elapsed_ms", 0)))
        hits: list[RetrievalHit] = []
        for item in payload["hits"]:
            if not isinstance(item, dict):
                raise ValueError("external retrieval hit is invalid")
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict) or set(metadata) - self._METADATA_KEYS:
                raise ValueError("external retrieval metadata exceeds the public-safe allowlist")
            if metadata.get("index_scope") not in {"public-safe", "private-fulltext"}:
                raise ValueError("external retrieval index scope is invalid")
            hits.append(
                RetrievalHit(
                    object_id=str(item.get("object_id", "")),
                    locator=str(item.get("locator", "")),
                    score=float(item.get("score", 0)),
                    match_reason="semantic",
                    metadata=dict(metadata),
                )
            )
        return hits[:limit]


class AppraisalProvider(Protocol):
    def appraise(
        self,
        *,
        paper_id: str,
        profile: str = "generic",
        project_id: str,
        activation_id: str,
    ) -> "AppraisalProviderResult": ...


@dataclass(frozen=True)
class AppraisalProviderResult:
    status: str
    provider: str
    provider_version: str
    profile: str
    flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in APPRAISAL_STATUSES:
            raise ValueError("invalid appraisal provider status")
        if not self.provider.strip() or not self.provider_version.strip():
            raise ValueError("appraisal provider and version are required")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", self.profile):
            raise ValueError("invalid appraisal profile")
        for code in (*self.flags, *self.warnings, *self.failures):
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,127}", code):
                raise ValueError("appraisal findings must be public-safe codes")
        if self.status != "completed" and not self.failures:
            raise ValueError("non-completed appraisal requires an explicit failure code")

    def public_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "provider_version": self.provider_version,
            "profile": self.profile,
            "flags": list(self.flags),
            "warnings": list(self.warnings),
            "failures": list(self.failures),
        }
