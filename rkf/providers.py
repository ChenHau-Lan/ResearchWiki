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
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from .core import Workspace, frontmatter, parse_frontmatter
from .lineage import ACTIVATION_ID_RE, PROJECT_ID_RE, utc_now
from .schema import (
    ACCESS_STATES,
    APPRAISAL_STATUSES,
    PROVIDER_STATUSES,
    REVIEW_STATES,
    normalize_paper_state,
)


ABSOLUTE_PROVIDER_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/])")


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

    def __post_init__(self) -> None:
        if self.status not in PROVIDER_STATUSES:
            raise ValueError(f"invalid provider status: {self.status}")
        if not self.provider.strip() or not self.provider_version.strip():
            raise ValueError("provider and provider_version are required")
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative")
        if self.entitlement_state not in {"unknown", "covered", "not-covered"}:
            raise ValueError("invalid entitlement_state")
        if self.artifact_sha256 and (
            len(self.artifact_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.artifact_sha256)
        ):
            raise ValueError("artifact_sha256 must be a lowercase SHA-256 digest")
        if self.status == "obtained" and (not self.artifact_sha256 or not self.pdf_magic_validated):
            raise ValueError("obtained provider result requires artifact_sha256 and PDF magic validation")
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
        payload["private_artifact_available"] = bool(self.private_artifact_handle)
        return payload


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
    ) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("external provider command must be a non-empty string sequence")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(command)
        self.provider = provider
        self.provider_version = provider_version
        self.timeout_seconds = timeout_seconds

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
            completed = subprocess.run(
                self.command,
                input=json.dumps(request, ensure_ascii=True),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return FullTextProviderResult(
                status="retryable",
                provider=self.provider,
                provider_version=self.provider_version,
                blocker_codes=("PROVIDER_TIMEOUT",),
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
        "status": result.status,
        "qc_status": "pending",
        "sha256": result.artifact_sha256,
        "provider": result.provider,
        "provider_version": result.provider_version,
        "route": result.route,
        "authorized_route": result.route,
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
