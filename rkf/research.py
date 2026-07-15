"""The five RKF v1 research workflows built on canonical objects."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .core import Workspace, parse_frontmatter, read_json
from .lineage import (
    ACTIVATION_ID_RE,
    PROJECT_ID_RE,
    activation_timeline,
    activity_timeline,
    object_origin_lookup,
    utc_now,
)
from .providers import validate_paper_access_target
from .schema import (
    ACCESS_STATES,
    CLAIM_STATUSES,
    EVIDENCE_STANCES,
    LOCATOR_STATES,
    REVIEW_STATES,
    READING_SCOPES,
    VERIFICATION_STATES,
    enum_findings,
    normalize_paper_state,
)


LOCATOR_KINDS = {"page", "section", "figure", "table", "paragraph"}
CANONICAL_PAPER_SCHEMA = "rkf-paper-v1.1"
FINDING_SCHEMA = "rkf-finding-v1"
EVIDENCE_CARD_SCHEMA = "rkf-evidence-v1"
CLAIM_SCHEMA = "rkf-claim-v1"
SYNTHESIS_SCHEMA = "rkf-synthesis-v1"
FINDING_ID_RE = re.compile(r"^fd_[a-f0-9]{20}$")
EVIDENCE_ID_RE = re.compile(r"^ev_[a-f0-9]{20}$")
CLAIM_ID_RE = re.compile(r"^clm_[a-f0-9]{20}$")
SYNTHESIS_ID_RE = re.compile(r"^syn_[a-f0-9]{20}$")
READ_RUN_ID_RE = re.compile(r"^read_[a-f0-9]{24}$")
RETRIEVAL_RUN_ID_RE = re.compile(r"^rrun_[a-f0-9]{24}$")
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
FINDING_FINGERPRINT_FIELDS = (
    "schema",
    "finding_id",
    "paper_id",
    "summary",
    "reading_scope",
    "locator_state",
    "locator",
    "origin_project_id",
    "activation_id",
    "public_safe",
)
FINDING_CAPTURE_SEMANTIC_FIELDS = (
    "paper_id",
    "summary",
    "reading_scope",
    "locator_state",
    "locator",
)
EVIDENCE_FINGERPRINT_FIELDS = (
    "schema",
    "evidence_id",
    "paper_id",
    "locator",
    "summary",
    "stance",
    "verification_state",
    "reading_scope",
    "origin_project_id",
    "activation_id",
    "public_safe",
)
CLAIM_FINGERPRINT_FIELDS = (
    "schema",
    "claim_id",
    "statement",
    "supporting_evidence_ids",
    "opposing_evidence_ids",
    "context_evidence_ids",
    "status",
    "origin_project_id",
    "activation_id",
    "public_safe",
)
SYNTHESIS_FINGERPRINT_FIELDS = (
    "schema",
    "synthesis_id",
    "research_question",
    "included_claim_ids",
    "agreements",
    "contradictions",
    "evidence_gaps",
    "evidence_matrix",
    "provisional_conclusion",
    "next_action",
    "origin_project_id",
    "activation_id",
    "public_safe",
)


_QUERY_RECEIPTS: ContextVar[dict[str, Any] | None] = ContextVar(
    "rkf_query_receipts",
    default=None,
)


def _restore_finding_changes(
    changes: list[tuple[Path, dict[str, Any] | None]],
) -> None:
    rollback_errors: list[str] = []
    for path, original in reversed(changes):
        try:
            if original is None:
                if path.is_symlink():
                    raise ValueError("finding rollback target became a symlink")
                path.unlink(missing_ok=True)
            else:
                write_canonical_state_json(path, original, label="finding rollback")
        except (OSError, RuntimeError, ValueError):
            rollback_errors.append(path.stem)
    if rollback_errors:
        raise RuntimeError("finding batch rollback was incomplete")


@dataclass
class FindingBatchTransaction:
    """Rollback scope kept open until the batch ActionEvent is durable."""

    records: list[dict[str, Any]]
    _changes: list[tuple[Path, dict[str, Any] | None]] = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def commit(self) -> None:
        self._closed = True
        self._changes.clear()

    def rollback(self) -> None:
        if self._closed:
            return
        _restore_finding_changes(self._changes)
        self._changes.clear()
        self._closed = True


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, ValueError):
        return False
    return True


def _read_regular_text_no_follow(path: Path, *, label: str) -> str:
    """Read one regular file while rejecting symlinks and replacement races."""

    descriptor = -1
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise ValueError(f"canonical {label} entry must be a regular file")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
        ):
            raise ValueError(f"canonical {label} entry changed during read")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return handle.read()
    except OSError as error:
        raise ValueError(f"canonical {label} entry could not be read safely") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _canonical_paper_records(ws: Workspace) -> list[tuple[Path, dict[str, Any], str]]:
    """Enumerate Paper pages without following knowledge-tree symlinks."""

    root = ws.paths.knowledge
    try:
        relative = root.relative_to(ws.paths.wiki_root)
    except ValueError as error:
        raise ValueError("canonical Paper root escaped the configured wiki root") from error
    current = ws.paths.wiki_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("canonical Paper root cannot contain a symlink boundary")
    if not _path_is_within(ws.paths.wiki_root, root):
        raise ValueError("canonical Paper root escaped the configured wiki root")
    if not root.exists():
        return []
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("canonical Paper root must be a directory")

    records: list[tuple[Path, dict[str, Any], str]] = []
    for current_name, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_name)
        if current.is_symlink() or not _path_is_within(root, current):
            raise ValueError("canonical Paper collection contains an unsafe directory")
        safe_directories: list[str] = []
        for name in directory_names:
            candidate = current / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or not _path_is_within(root, candidate):
                raise ValueError("canonical Paper collection contains an unsafe directory")
            safe_directories.append(name)
        directory_names[:] = safe_directories
        for name in file_names:
            if not name.endswith(".md"):
                continue
            candidate = current / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or not _path_is_within(root, candidate):
                raise ValueError("canonical Paper collection contains an unsafe entry")
            meta, body = parse_frontmatter(_read_regular_text_no_follow(candidate, label="Paper"))
            if meta.get("type") == "paper":
                records.append((candidate, meta, body))
    return sorted(records, key=lambda item: item[0].as_posix())


def _canonical_retrieval_runs(ws: Workspace) -> list[dict[str, Any]]:
    """Load contained retrieval receipts without following state symlinks."""

    runs: list[dict[str, Any]] = []
    for path in _canonical_collection_paths(
        ws,
        collection=("retrieval_runs",),
        id_pattern=RETRIEVAL_RUN_ID_RE,
        label="retrieval run",
    ):
        try:
            payload = json.loads(_read_regular_text_no_follow(path, label="retrieval run"))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid canonical retrieval run: {path.stem}") from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != "rkf-retrieval-run-v1"
            or payload.get("retrieval_run_id") != path.stem
        ):
            raise ValueError(f"invalid canonical retrieval run: {path.stem}")
        runs.append(payload)
    return runs


def _state_collection_root(
    ws: Workspace,
    *,
    collection: tuple[str, ...],
    label: str,
    create: bool = False,
) -> Path:
    state_root = ws.paths.state
    if state_root.is_symlink() or not _path_is_within(ws.paths.wiki_root, state_root):
        raise ValueError(f"canonical {label} state root is unsafe")
    if state_root.exists() and not state_root.is_dir():
        raise ValueError(f"canonical {label} state root must be a directory")
    current = state_root
    for part in collection:
        if not part or part in {".", ".."} or "/" in part or "\\" in part:
            raise ValueError(f"canonical {label} collection is invalid")
        current = current / part
        if current.is_symlink():
            raise ValueError(f"canonical {label} root/parent cannot be a symlink")
        if current.exists() and not current.is_dir():
            raise ValueError(f"canonical {label} root/parent must be a directory")
    if not _path_is_within(state_root, current):
        raise ValueError(f"canonical {label} collection escaped state")
    if create:
        current.mkdir(parents=True, exist_ok=True)
        if current.is_symlink() or not current.is_dir():
            raise ValueError(f"canonical {label} root is unsafe")
    return current


def canonical_state_json_path(
    ws: Workspace,
    *,
    collection: tuple[str, ...],
    object_id: str,
    id_pattern: re.Pattern[str],
    label: str,
    must_exist: bool = False,
    create_parent: bool = False,
) -> Path:
    if not isinstance(object_id, str) or not id_pattern.fullmatch(object_id):
        raise ValueError(f"invalid {label} id: {object_id}")
    root = _state_collection_root(
        ws,
        collection=collection,
        label=label,
        create=create_parent,
    )
    target = root / f"{object_id}.json"
    if target.is_symlink() or not _path_is_within(root, target):
        raise ValueError(f"canonical {label} target is unsafe")
    if target.exists() and not target.is_file():
        raise ValueError(f"canonical {label} target must be a regular file")
    if must_exist and not target.is_file():
        raise ValueError(f"unknown {label}: {object_id}")
    return target


def read_canonical_state_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"canonical {label} target is unsafe")
        payload = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid canonical {label}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"invalid canonical {label}")
    return payload


def write_canonical_state_json(path: Path, payload: dict[str, Any], *, label: str) -> None:
    parent = path.parent
    if parent.is_symlink() or path.is_symlink():
        raise ValueError(f"canonical {label} path cannot be a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir() or path.is_symlink():
        raise ValueError(f"canonical {label} path is unsafe")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if parent.is_symlink() or path.is_symlink():
            raise ValueError(f"canonical {label} path changed during write")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _canonical_collection_paths(
    ws: Workspace,
    *,
    collection: tuple[str, ...],
    id_pattern: re.Pattern[str],
    label: str,
) -> list[Path]:
    root = _state_collection_root(ws, collection=collection, label=label)
    if not root.exists():
        return []
    paths: list[Path] = []
    for path in sorted(root.glob("*.json")):
        if path.is_symlink() or not path.is_file() or not id_pattern.fullmatch(path.stem):
            raise ValueError(f"canonical {label} collection contains an unsafe entry")
        paths.append(path)
    return paths


def _content_fingerprint(payload: dict[str, Any], fields: tuple[str, ...]) -> str:
    durable_content = {key: payload.get(key) for key in fields}
    encoded = json.dumps(
        durable_content,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_canonical_paper(ws: Workspace, *, paper_id: str) -> tuple[str, dict[str, Any]]:
    """Load one path-safe canonical Paper and reject incomplete state."""

    if not isinstance(paper_id, str):
        raise ValueError("paper_id must be a logical papers/<id> identifier")
    logical_id = validate_paper_access_target(ws, paper_id=paper_id)
    path = ws.paths.knowledge / f"{logical_id}.md"
    try:
        meta, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("canonical Paper could not be read") from error
    if meta.get("schema") != CANONICAL_PAPER_SCHEMA:
        raise ValueError("paper_id does not identify an rkf-paper-v1.1 canonical Paper")
    if meta.get("access_state") not in ACCESS_STATES:
        raise ValueError("canonical Paper access_state is missing or invalid")
    if meta.get("review_state") not in REVIEW_STATES:
        raise ValueError("canonical Paper review_state is missing or invalid")
    return logical_id, meta


def _evidence_content_fingerprint(payload: dict[str, Any]) -> str:
    return _content_fingerprint(payload, EVIDENCE_FINGERPRINT_FIELDS)


def _finding_content_fingerprint(payload: dict[str, Any]) -> str:
    return _content_fingerprint(payload, FINDING_FINGERPRINT_FIELDS)


def _finding_capture_semantics(payload: dict[str, Any]) -> dict[str, Any]:
    """Return fields an implicit Paper+summary capture is allowed to match."""

    return {key: payload.get(key) for key in FINDING_CAPTURE_SEMANTIC_FIELDS}


def _finding_without_timestamps(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"created", "updated"}
    }


def _claim_content_fingerprint(payload: dict[str, Any]) -> str:
    return _content_fingerprint(payload, CLAIM_FINGERPRINT_FIELDS)


def _synthesis_content_fingerprint(payload: dict[str, Any]) -> str:
    return _content_fingerprint(payload, SYNTHESIS_FINGERPRINT_FIELDS)


def _require_object_receipt(
    ws: Workspace,
    *,
    object_id: str,
    content_fingerprint: str,
    origin_project_id: str,
    activation_id: str,
    action: str,
) -> None:
    if not FINGERPRINT_RE.fullmatch(content_fingerprint):
        raise ValueError(f"canonical object fingerprint is invalid: {object_id}")
    lookup = _QUERY_RECEIPTS.get()
    if lookup is not None and lookup.get("workspace_root") == str(ws.root.resolve()):
        activation_key = (origin_project_id, activation_id)
        if activation_key not in lookup["activations"]:
            raise ValueError(f"canonical object activation receipt is missing: {object_id}")
        receipt_key = (
            origin_project_id,
            activation_id,
            action,
            object_id,
            content_fingerprint,
        )
        if receipt_key not in lookup["actions"]:
            raise ValueError(
                f"canonical object action receipt is missing or drifted: {object_id}"
            )
        return

    activations = activation_timeline(
        ws.root,
        project_id=origin_project_id,
        activation_id=activation_id,
    )
    if not any(
        event.get("schema") == "rkf-activation-event-v1"
        and event.get("transition") == "started"
        for event in activations
    ):
        raise ValueError(f"canonical object activation receipt is missing: {object_id}")
    events = activity_timeline(
        ws.root,
        project_id=origin_project_id,
        activation_id=activation_id,
        action=action,
        target_object_id=object_id,
    )
    if not any(
        event.get("schema") == "rkf-action-event-v1"
        and event.get("status") == "ok"
        and isinstance(event.get("object_fingerprints"), dict)
        and event["object_fingerprints"].get(object_id) == content_fingerprint
        for event in events
    ):
        raise ValueError(f"canonical object action receipt is missing or drifted: {object_id}")


@contextmanager
def query_local_receipt_lookup(ws: Workspace) -> Iterator[dict[str, int]]:
    """Load lineage once so one Ask does not rescan receipts per candidate.

    This cache is query-local and only accelerates the existing receipt checks;
    it does not relax activation, action, status, or fingerprint requirements.
    """

    activation_events = activation_timeline(ws.root)
    action_events = activity_timeline(ws.root)
    activations = {
        (str(event.get("project_id", "")), str(event.get("activation_id", "")))
        for event in activation_events
        if event.get("schema") == "rkf-activation-event-v1"
        and event.get("transition") == "started"
    }
    actions: set[tuple[str, str, str, str, str]] = set()
    for event in action_events:
        if event.get("schema") != "rkf-action-event-v1" or event.get("status") != "ok":
            continue
        fingerprints = event.get("object_fingerprints")
        if not isinstance(fingerprints, dict):
            continue
        for object_id, fingerprint in fingerprints.items():
            if not isinstance(object_id, str) or not isinstance(fingerprint, str):
                continue
            actions.add(
                (
                    str(event.get("origin_project_id", "")),
                    str(event.get("activation_id", "")),
                    str(event.get("action", "")),
                    object_id,
                    fingerprint,
                )
            )
    token = _QUERY_RECEIPTS.set(
        {
            "workspace_root": str(ws.root.resolve()),
            "activations": activations,
            "actions": actions,
        }
    )
    try:
        yield {
            "activation_receipt_count": len(activation_events),
            "action_receipt_count": len(action_events),
        }
    finally:
        _QUERY_RECEIPTS.reset(token)


def _normalize_finding_locator(
    *,
    locator_state: str,
    locator: Any,
) -> dict[str, str] | None:
    if locator_state not in LOCATOR_STATES:
        raise ValueError("finding locator_state must be missing, coarse, or exact")
    if locator_state == "missing":
        if locator is not None:
            raise ValueError("missing finding cannot contain a locator")
        return None
    if not isinstance(locator, dict) or set(locator) != {"kind", "value"}:
        raise ValueError(f"{locator_state} finding requires a locator object")
    kind = locator.get("kind")
    value = locator.get("value")
    if kind not in LOCATOR_KINDS or not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{locator_state} finding requires a page/section/figure/table/paragraph locator"
        )
    return {"kind": str(kind), "value": value.strip()}


def load_canonical_finding(ws: Workspace, finding_id: str) -> dict[str, Any]:
    """Load one FindingDraft and revalidate its source, lineage, and receipt."""

    path = canonical_state_json_path(
        ws,
        collection=("findings",),
        object_id=finding_id,
        id_pattern=FINDING_ID_RE,
        label="finding",
        must_exist=True,
    )
    finding = read_canonical_state_json(path, label="finding")
    if finding.get("schema") != FINDING_SCHEMA:
        raise ValueError(f"invalid finding schema: {finding_id}")
    if finding.get("finding_id") != finding_id:
        raise ValueError(f"finding id does not match its record: {finding_id}")

    paper_id = finding.get("paper_id")
    if not isinstance(paper_id, str):
        raise ValueError(f"finding requires a canonical Paper: {finding_id}")
    logical_paper_id, paper_meta = load_canonical_paper(ws, paper_id=paper_id)
    if logical_paper_id != paper_id:
        raise ValueError(f"finding paper_id is not canonical: {finding_id}")
    summary = finding.get("summary")
    if not isinstance(summary, str) or not summary.strip() or summary != summary.strip():
        raise ValueError(f"finding summary is invalid: {finding_id}")
    reading_scope = finding.get("reading_scope")
    if reading_scope not in READING_SCOPES:
        raise ValueError(f"finding reading scope is invalid: {finding_id}")
    scope_rank = {value: index for index, value in enumerate(READING_SCOPES)}
    if scope_rank[str(reading_scope)] > scope_rank[str(paper_meta["access_state"])]:
        raise ValueError(f"finding reading scope exceeds Paper access: {finding_id}")
    locator_state = finding.get("locator_state")
    locator = _normalize_finding_locator(
        locator_state=str(locator_state),
        locator=finding.get("locator") if "locator" in finding else None,
    )
    if locator_state == "missing" and "locator" in finding:
        raise ValueError(f"missing finding must omit locator: {finding_id}")
    if locator_state != "missing" and locator != finding.get("locator"):
        raise ValueError(f"finding locator is not normalized: {finding_id}")
    if not PROJECT_ID_RE.fullmatch(str(finding.get("origin_project_id", ""))) or not ACTIVATION_ID_RE.fullmatch(
        str(finding.get("activation_id", ""))
    ):
        raise ValueError(f"finding lineage is invalid: {finding_id}")
    if finding.get("public_safe") is not True:
        raise ValueError(f"finding is not public-safe: {finding_id}")
    expected_id = _stable_id("fd", paper_id, summary)
    if expected_id != finding_id:
        raise ValueError(f"finding content does not match its id: {finding_id}")
    content_fingerprint = str(finding.get("content_fingerprint", ""))
    if content_fingerprint != _finding_content_fingerprint(finding):
        raise ValueError(f"finding content fingerprint mismatch: {finding_id}")
    _require_object_receipt(
        ws,
        object_id=finding_id,
        content_fingerprint=content_fingerprint,
        origin_project_id=str(finding["origin_project_id"]),
        activation_id=str(finding["activation_id"]),
        action="workflow.read",
    )
    return finding


def _prepare_finding_payload(
    ws: Workspace,
    *,
    item: dict[str, Any],
    origin_project_id: str,
    activation_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    allowed = {
        "finding_id",
        "paper_id",
        "summary",
        "reading_scope",
        "locator_state",
        "locator",
    }
    unexpected = sorted(set(item) - allowed)
    if unexpected:
        raise ValueError(f"unsupported finding field(s): {', '.join(unexpected)}")
    requested_id = item.get("finding_id", "")
    if requested_id and not isinstance(requested_id, str):
        raise ValueError("finding_id must be text")
    existing = load_canonical_finding(ws, requested_id) if requested_id else None

    paper_id = item.get("paper_id", existing.get("paper_id") if existing else "")
    summary = item.get("summary", existing.get("summary") if existing else "")
    reading_scope = item.get(
        "reading_scope",
        existing.get("reading_scope") if existing else "",
    )
    locator_state = item.get(
        "locator_state",
        existing.get("locator_state") if existing else "missing",
    )
    locator = (
        item.get("locator")
        if "locator" in item
        else existing.get("locator") if existing else None
    )
    if not all(
        isinstance(value, str)
        for value in (paper_id, summary, reading_scope, locator_state)
    ):
        raise ValueError("finding paper_id, summary, reading_scope, and locator_state must be text")
    paper_id, paper_meta = load_canonical_paper(ws, paper_id=paper_id)
    summary = summary.strip()
    if not summary:
        raise ValueError("finding requires a source-grounded summary")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("finding requires valid project/activation lineage")
    reading_scope = reading_scope.strip() or str(paper_meta["access_state"])
    if reading_scope not in READING_SCOPES:
        raise ValueError("invalid finding reading_scope")
    scope_rank = {value: index for index, value in enumerate(READING_SCOPES)}
    if scope_rank[reading_scope] > scope_rank[str(paper_meta["access_state"])]:
        raise ValueError("finding reading_scope exceeds the canonical Paper access_state")
    locator_state = locator_state.strip()
    normalized_locator = _normalize_finding_locator(
        locator_state=locator_state,
        locator=locator,
    )
    finding_id = _stable_id("fd", paper_id, summary)
    if requested_id and requested_id != finding_id:
        raise ValueError("finding_id does not match the requested Paper and summary")
    payload: dict[str, Any] = {
        "schema": FINDING_SCHEMA,
        "finding_id": finding_id,
        "paper_id": paper_id,
        "summary": summary,
        "reading_scope": reading_scope,
        "locator_state": locator_state,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "public_safe": True,
    }
    if normalized_locator is not None:
        payload["locator"] = normalized_locator
    payload["content_fingerprint"] = _finding_content_fingerprint(payload)
    return payload, existing


def record_findings(
    ws: Workspace,
    *,
    findings: list[dict[str, Any]],
    origin_project_id: str,
    activation_id: str,
    keep_transaction_open: bool = False,
) -> list[dict[str, Any]] | FindingBatchTransaction:
    """Prevalidate a FindingDraft batch before writing any canonical object."""

    if not isinstance(findings, list) or not findings:
        raise ValueError("findings must be a non-empty list")
    if not all(isinstance(item, dict) for item in findings):
        raise ValueError("findings must contain objects")

    prepared: dict[
        str,
        tuple[dict[str, Any], Path, bool, dict[str, Any] | None],
    ] = {}
    order: list[str] = []
    for item in findings:
        explicit_finding_id = bool(item.get("finding_id", ""))
        payload, existing = _prepare_finding_payload(
            ws,
            item=item,
            origin_project_id=origin_project_id,
            activation_id=activation_id,
        )
        finding_id = str(payload["finding_id"])
        if finding_id in prepared:
            prior = prepared[finding_id][0]
            if _finding_without_timestamps(prior) != _finding_without_timestamps(payload):
                raise ValueError(f"conflicting duplicate finding in batch: {finding_id}")
            continue
        path = canonical_state_json_path(
            ws,
            collection=("findings",),
            object_id=finding_id,
            id_pattern=FINDING_ID_RE,
            label="finding",
            create_parent=True,
        )
        if existing is None and path.exists():
            existing = load_canonical_finding(ws, finding_id)
            if not explicit_finding_id:
                if _finding_capture_semantics(existing) != _finding_capture_semantics(payload):
                    raise ValueError(
                        "finding already exists; reading scope or locator changes "
                        "require an explicit finding_id"
                    )
                # An implicit semantic match is idempotent. Preserve the original
                # locator, lineage, fingerprint, and timestamps exactly.
                payload = existing
        should_write = True
        if existing is not None:
            if _finding_without_timestamps(existing) == _finding_without_timestamps(payload):
                payload = existing
                should_write = False
            else:
                payload["created"] = existing.get("created", utc_now())
                payload["updated"] = utc_now()
        else:
            payload["created"] = utc_now()
        original = dict(existing) if existing is not None else None
        prepared[finding_id] = (payload, path, should_write, original)
        order.append(finding_id)

    written: list[str] = []
    try:
        for finding_id in order:
            payload, path, should_write, _original = prepared[finding_id]
            if should_write:
                write_canonical_state_json(path, payload, label="finding")
                written.append(finding_id)
    except (OSError, RuntimeError, ValueError) as error:
        changes = [
            (prepared[finding_id][1], prepared[finding_id][3])
            for finding_id in written
        ]
        try:
            _restore_finding_changes(changes)
        except RuntimeError as rollback_error:
            raise RuntimeError(
                "finding batch write failed and rollback was incomplete"
            ) from rollback_error
        raise
    records = [prepared[finding_id][0] for finding_id in order]
    transaction = FindingBatchTransaction(
        records=records,
        _changes=[
            (prepared[finding_id][1], prepared[finding_id][3])
            for finding_id in written
        ],
    )
    if keep_transaction_open:
        return transaction
    transaction.commit()
    return records


def promote_finding_to_evidence(
    ws: Workspace,
    *,
    finding_id: str,
    origin_project_id: str,
    activation_id: str,
    stance: str = "contextualizes",
    verification_state: str = "unreviewed",
) -> dict[str, Any]:
    """Promote only a receipt-backed exact FindingDraft through the Evidence gate."""

    finding = load_canonical_finding(ws, finding_id)
    if finding.get("locator_state") != "exact":
        raise ValueError("only an exact-locator finding can promote to Evidence")
    locator = finding["locator"]
    return record_evidence(
        ws,
        paper_id=str(finding["paper_id"]),
        summary=str(finding["summary"]),
        locator_kind=str(locator["kind"]),
        locator_value=str(locator["value"]),
        stance=stance,
        verification_state=verification_state,
        governed_reading_scope=str(finding["reading_scope"]),
        origin_project_id=origin_project_id,
        activation_id=activation_id,
    )


def load_canonical_evidence(ws: Workspace, evidence_id: str) -> dict[str, Any]:
    """Fail closed when an Evidence card is missing, unsafe, or drifted."""

    path = canonical_state_json_path(
        ws,
        collection=("evidence", "cards"),
        object_id=evidence_id,
        id_pattern=EVIDENCE_ID_RE,
        label="evidence",
        must_exist=True,
    )
    evidence = read_canonical_state_json(path, label="evidence")
    if evidence.get("schema") != EVIDENCE_CARD_SCHEMA:
        raise ValueError(f"invalid evidence schema: {evidence_id}")
    if evidence.get("evidence_id") != evidence_id:
        raise ValueError(f"evidence id does not match its card: {evidence_id}")

    paper_id = evidence.get("paper_id")
    if not isinstance(paper_id, str):
        raise ValueError(f"evidence requires a canonical Paper: {evidence_id}")
    logical_paper_id, paper_meta = load_canonical_paper(ws, paper_id=paper_id)
    if logical_paper_id != paper_id:
        raise ValueError(f"evidence paper_id is not canonical: {evidence_id}")

    locator = evidence.get("locator")
    if not isinstance(locator, dict) or set(locator) != {"kind", "value"}:
        raise ValueError(f"evidence locator is invalid: {evidence_id}")
    locator_kind = locator.get("kind")
    locator_value = locator.get("value")
    if (
        locator_kind not in LOCATOR_KINDS
        or not isinstance(locator_value, str)
        or not locator_value.strip()
        or locator_value != locator_value.strip()
    ):
        raise ValueError(f"evidence locator is invalid: {evidence_id}")
    summary = evidence.get("summary")
    if not isinstance(summary, str) or not summary.strip() or summary != summary.strip():
        raise ValueError(f"evidence summary is invalid: {evidence_id}")
    if evidence.get("stance") not in EVIDENCE_STANCES:
        raise ValueError(f"evidence stance is invalid: {evidence_id}")
    if evidence.get("verification_state") not in VERIFICATION_STATES:
        raise ValueError(f"evidence verification state is invalid: {evidence_id}")
    reading_scope = evidence.get("reading_scope")
    if reading_scope not in READING_SCOPES:
        raise ValueError(f"evidence reading scope is invalid: {evidence_id}")
    scope_rank = {value: index for index, value in enumerate(READING_SCOPES)}
    if scope_rank[str(reading_scope)] > scope_rank[str(paper_meta["access_state"])]:
        raise ValueError(f"evidence reading scope exceeds Paper access: {evidence_id}")
    if evidence.get("verification_state") == "human-verified" and reading_scope != "fulltext":
        raise ValueError(f"human-verified evidence requires full-text Read scope: {evidence_id}")
    if not PROJECT_ID_RE.fullmatch(str(evidence.get("origin_project_id", ""))) or not ACTIVATION_ID_RE.fullmatch(
        str(evidence.get("activation_id", ""))
    ):
        raise ValueError(f"evidence lineage is invalid: {evidence_id}")
    if evidence.get("public_safe") is not True:
        raise ValueError(f"evidence is not public-safe: {evidence_id}")
    expected_id = _stable_id("ev", paper_id, str(locator_kind), locator_value, summary)
    if expected_id != evidence_id:
        raise ValueError(f"evidence content does not match its id: {evidence_id}")
    content_fingerprint = str(evidence.get("content_fingerprint", ""))
    if content_fingerprint != _evidence_content_fingerprint(evidence):
        raise ValueError(f"evidence content fingerprint mismatch: {evidence_id}")
    _require_object_receipt(
        ws,
        object_id=evidence_id,
        content_fingerprint=content_fingerprint,
        origin_project_id=str(evidence["origin_project_id"]),
        activation_id=str(evidence["activation_id"]),
        action="workflow.read",
    )
    return evidence


def record_evidence(
    ws: Workspace,
    *,
    paper_id: str,
    summary: str,
    locator_kind: str,
    locator_value: str,
    stance: str = "contextualizes",
    verification_state: str = "unreviewed",
    governed_reading_scope: str = "",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    if not all(
        isinstance(value, str)
        for value in (
            summary,
            locator_kind,
            locator_value,
            stance,
            verification_state,
            governed_reading_scope,
        )
    ):
        raise ValueError("evidence fields must be text")
    paper_id, paper_meta = load_canonical_paper(ws, paper_id=paper_id)
    summary = summary.strip()
    locator_value = locator_value.strip()
    if not paper_id or not summary:
        raise ValueError("evidence requires paper_id and a source-grounded summary")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("evidence requires valid project/activation lineage")
    if locator_kind not in LOCATOR_KINDS or not locator_value:
        raise ValueError("evidence requires an exact page/section/figure/table/paragraph locator")
    if stance not in EVIDENCE_STANCES:
        raise ValueError("invalid evidence stance")
    if verification_state not in VERIFICATION_STATES:
        raise ValueError("invalid evidence verification state")
    reading_scope = governed_reading_scope or str(paper_meta["access_state"])
    if reading_scope not in READING_SCOPES:
        raise ValueError("invalid governed Read scope")
    scope_rank = {value: index for index, value in enumerate(READING_SCOPES)}
    if scope_rank[reading_scope] > scope_rank[str(paper_meta["access_state"])]:
        raise ValueError("governed Read scope exceeds the canonical Paper access_state")
    if verification_state == "human-verified" and reading_scope != "fulltext":
        raise ValueError("human-verified evidence requires full-text governed Read scope")
    evidence_id = _stable_id("ev", paper_id, locator_kind, locator_value, summary)
    payload = {
        "schema": "rkf-evidence-v1",
        "evidence_id": evidence_id,
        "paper_id": paper_id,
        "locator": {"kind": locator_kind, "value": locator_value},
        "summary": summary,
        "stance": stance,
        "verification_state": verification_state,
        "reading_scope": reading_scope,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "public_safe": True,
    }
    payload["content_fingerprint"] = _evidence_content_fingerprint(payload)
    path = canonical_state_json_path(
        ws,
        collection=("evidence", "cards"),
        object_id=evidence_id,
        id_pattern=EVIDENCE_ID_RE,
        label="evidence",
        create_parent=True,
    )
    if path.exists():
        existing = read_canonical_state_json(path, label="evidence")
        comparable = {key: value for key, value in existing.items() if key not in {"created", "updated"}}
        if comparable == payload:
            return existing
        payload["created"] = existing.get("created", utc_now())
        payload["updated"] = utc_now()
    else:
        payload["created"] = utc_now()
    write_canonical_state_json(path, payload, label="evidence")
    return payload


def _validate_claim_evidence(
    ws: Workspace,
    claim: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for stance_key, stance in (
        ("supporting_evidence_ids", "supports"),
        ("opposing_evidence_ids", "opposes"),
        ("context_evidence_ids", "contextualizes"),
    ):
        evidence_ids = claim.get(stance_key)
        if not isinstance(evidence_ids, list) or not all(isinstance(item, str) for item in evidence_ids):
            raise ValueError(f"claim {stance_key} must be a string list")
        if len(evidence_ids) != len(set(evidence_ids)) or seen.intersection(evidence_ids):
            raise ValueError("claim evidence ids must be unique across stance lists")
        seen.update(evidence_ids)
        for evidence_id in evidence_ids:
            item = load_canonical_evidence(ws, evidence_id)
            if item["stance"] != stance:
                raise ValueError(f"claim evidence stance drifted: {evidence_id}")
            evidence.append(item)
    status = claim.get("status")
    if status in {"supported", "disputed", "verified"} and not evidence:
        raise ValueError(f"{status} claim requires locator-backed evidence")
    if status == "verified" and not any(
        item.get("verification_state") == "human-verified" for item in evidence
    ):
        raise ValueError("verified claim requires current human-verified evidence")
    return evidence


def load_canonical_claim(ws: Workspace, claim_id: str) -> dict[str, Any]:
    path = canonical_state_json_path(
        ws,
        collection=("claims",),
        object_id=claim_id,
        id_pattern=CLAIM_ID_RE,
        label="claim",
        must_exist=True,
    )
    claim = read_canonical_state_json(path, label="claim")
    if claim.get("schema") != CLAIM_SCHEMA or claim.get("claim_id") != claim_id:
        raise ValueError(f"invalid canonical claim schema/id: {claim_id}")
    statement = claim.get("statement")
    if not isinstance(statement, str) or not statement.strip() or statement != statement.strip():
        raise ValueError(f"invalid canonical claim statement: {claim_id}")
    if _stable_id("clm", statement) != claim_id:
        raise ValueError(f"canonical claim content does not match its id: {claim_id}")
    if claim.get("status") not in CLAIM_STATUSES:
        raise ValueError(f"invalid canonical claim status: {claim_id}")
    origin_project_id = str(claim.get("origin_project_id", ""))
    activation_id = str(claim.get("activation_id", ""))
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError(f"invalid canonical claim lineage: {claim_id}")
    if claim.get("public_safe") is not True:
        raise ValueError(f"canonical claim is not public-safe: {claim_id}")
    _validate_claim_evidence(ws, claim)
    content_fingerprint = str(claim.get("content_fingerprint", ""))
    if content_fingerprint != _claim_content_fingerprint(claim):
        raise ValueError(f"canonical claim content fingerprint mismatch: {claim_id}")
    _require_object_receipt(
        ws,
        object_id=claim_id,
        content_fingerprint=content_fingerprint,
        origin_project_id=origin_project_id,
        activation_id=activation_id,
        action="workflow.compare-synthesize",
    )
    return claim


def record_claim(
    ws: Workspace,
    *,
    statement: str,
    evidence_ids: list[str],
    status: str = "proposed",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    statement = statement.strip()
    if not statement:
        raise ValueError("claim statement is required")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("claim requires valid project/activation lineage")
    if status not in CLAIM_STATUSES:
        raise ValueError("invalid claim status")
    evidence: list[dict[str, Any]] = []
    for evidence_id in dict.fromkeys(evidence_ids):
        evidence.append(load_canonical_evidence(ws, evidence_id))
    if status in {"supported", "disputed", "verified"} and not evidence:
        raise ValueError(f"{status} claim requires locator-backed evidence")
    if status == "verified" and not any(item.get("verification_state") == "human-verified" for item in evidence):
        raise ValueError("verified claim requires human-verified evidence")
    claim_id = _stable_id("clm", statement)
    payload = {
        "schema": CLAIM_SCHEMA,
        "claim_id": claim_id,
        "statement": statement,
        "supporting_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "supports"],
        "opposing_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "opposes"],
        "context_evidence_ids": [item["evidence_id"] for item in evidence if item.get("stance") == "contextualizes"],
        "status": status,
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "public_safe": True,
    }
    payload["content_fingerprint"] = _claim_content_fingerprint(payload)
    path = canonical_state_json_path(
        ws,
        collection=("claims",),
        object_id=claim_id,
        id_pattern=CLAIM_ID_RE,
        label="claim",
        create_parent=True,
    )
    if path.exists():
        existing = read_canonical_state_json(path, label="claim")
        comparable = {key: value for key, value in existing.items() if key not in {"created", "updated"}}
        if comparable == payload:
            return existing
        payload["created"] = existing.get("created", utc_now())
        payload["updated"] = utc_now()
    else:
        payload["created"] = utc_now()
    write_canonical_state_json(path, payload, label="claim")
    return payload


def evidence_matrix(ws: Workspace, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for claim in claims:
        for stance_key, stance in (
            ("supporting_evidence_ids", "supports"),
            ("opposing_evidence_ids", "opposes"),
            ("context_evidence_ids", "contextualizes"),
        ):
            for evidence_id in claim.get(stance_key, []):
                evidence = load_canonical_evidence(ws, evidence_id)
                if evidence["stance"] != stance:
                    raise ValueError(f"claim evidence stance drifted: {evidence_id}")
                matrix.append(
                    {
                        "paper_id": evidence["paper_id"],
                        "claim_id": claim["claim_id"],
                        "evidence_id": evidence_id,
                        "locator": evidence["locator"],
                        "stance": stance,
                        "verification_state": evidence["verification_state"],
                    }
                )
    return matrix


def synthesize(
    ws: Workspace,
    *,
    research_question: str,
    claim_ids: list[str],
    provisional_conclusion: str = "",
    next_action: str = "",
    origin_project_id: str,
    activation_id: str,
) -> dict[str, Any]:
    research_question = research_question.strip()
    if not research_question:
        raise ValueError("research_question is required")
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError("synthesis requires valid project/activation lineage")
    claims: list[dict[str, Any]] = []
    for claim_id in dict.fromkeys(claim_ids):
        claims.append(load_canonical_claim(ws, claim_id))
    matrix = evidence_matrix(ws, claims)
    synthesis_id = _stable_id("syn", research_question)
    payload = {
        "schema": SYNTHESIS_SCHEMA,
        "synthesis_id": synthesis_id,
        "research_question": research_question,
        "included_claim_ids": list(dict.fromkeys(claim_ids)),
        "agreements": [item["claim_id"] for item in claims if item.get("status") in {"supported", "verified"}],
        "contradictions": [item["claim_id"] for item in claims if item.get("status") == "disputed"],
        "evidence_gaps": [item["claim_id"] for item in claims if item.get("status") == "proposed"],
        "evidence_matrix": matrix,
        "provisional_conclusion": provisional_conclusion.strip(),
        "next_action": next_action.strip(),
        "origin_project_id": origin_project_id,
        "activation_id": activation_id,
        "public_safe": True,
    }
    payload["content_fingerprint"] = _synthesis_content_fingerprint(payload)
    path = canonical_state_json_path(
        ws,
        collection=("syntheses",),
        object_id=synthesis_id,
        id_pattern=SYNTHESIS_ID_RE,
        label="synthesis",
        create_parent=True,
    )
    if path.exists():
        existing = read_canonical_state_json(path, label="synthesis")
        comparable = {key: value for key, value in existing.items() if key not in {"created", "updated"}}
        if comparable == payload:
            return existing
        payload["created"] = existing.get("created", utc_now())
        payload["updated"] = utc_now()
    else:
        payload["created"] = utc_now()
    write_canonical_state_json(path, payload, label="synthesis")
    return payload


def load_canonical_synthesis(ws: Workspace, synthesis_id: str) -> dict[str, Any]:
    path = canonical_state_json_path(
        ws,
        collection=("syntheses",),
        object_id=synthesis_id,
        id_pattern=SYNTHESIS_ID_RE,
        label="synthesis",
        must_exist=True,
    )
    synthesis = read_canonical_state_json(path, label="synthesis")
    if synthesis.get("schema") != SYNTHESIS_SCHEMA or synthesis.get("synthesis_id") != synthesis_id:
        raise ValueError(f"invalid canonical synthesis schema/id: {synthesis_id}")
    research_question = synthesis.get("research_question")
    if (
        not isinstance(research_question, str)
        or not research_question.strip()
        or research_question != research_question.strip()
        or _stable_id("syn", research_question) != synthesis_id
    ):
        raise ValueError(f"invalid canonical synthesis question/id: {synthesis_id}")
    claim_ids = synthesis.get("included_claim_ids")
    if (
        not isinstance(claim_ids, list)
        or not all(isinstance(item, str) for item in claim_ids)
        or len(claim_ids) != len(set(claim_ids))
    ):
        raise ValueError(f"invalid canonical synthesis claim ids: {synthesis_id}")
    claims = [load_canonical_claim(ws, claim_id) for claim_id in claim_ids]
    expected = {
        "agreements": [
            item["claim_id"] for item in claims if item.get("status") in {"supported", "verified"}
        ],
        "contradictions": [item["claim_id"] for item in claims if item.get("status") == "disputed"],
        "evidence_gaps": [item["claim_id"] for item in claims if item.get("status") == "proposed"],
        "evidence_matrix": evidence_matrix(ws, claims),
    }
    if any(synthesis.get(key) != value for key, value in expected.items()):
        raise ValueError(f"canonical synthesis projections drifted: {synthesis_id}")
    origin_project_id = str(synthesis.get("origin_project_id", ""))
    activation_id = str(synthesis.get("activation_id", ""))
    if not PROJECT_ID_RE.fullmatch(origin_project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
        raise ValueError(f"invalid canonical synthesis lineage: {synthesis_id}")
    if synthesis.get("public_safe") is not True:
        raise ValueError(f"canonical synthesis is not public-safe: {synthesis_id}")
    content_fingerprint = str(synthesis.get("content_fingerprint", ""))
    if content_fingerprint != _synthesis_content_fingerprint(synthesis):
        raise ValueError(f"canonical synthesis content fingerprint mismatch: {synthesis_id}")
    _require_object_receipt(
        ws,
        object_id=synthesis_id,
        content_fingerprint=content_fingerprint,
        origin_project_id=origin_project_id,
        activation_id=activation_id,
        action="workflow.compare-synthesize",
    )
    return synthesis


def review_home(
    ws: Workspace,
    *,
    project_id: str = "",
    activation_id: str = "",
    action: str = "",
    status: str = "",
    target_object_id: str = "",
) -> dict[str, Any]:
    canonical_findings = [
        load_canonical_finding(ws, path.stem)
        for path in _canonical_collection_paths(
            ws,
            collection=("findings",),
            id_pattern=FINDING_ID_RE,
            label="finding",
        )
    ]
    evidence = [
        load_canonical_evidence(ws, path.stem)
        for path in _canonical_collection_paths(
            ws,
            collection=("evidence", "cards"),
            id_pattern=EVIDENCE_ID_RE,
            label="evidence",
        )
    ]
    claims = [
        load_canonical_claim(ws, path.stem)
        for path in _canonical_collection_paths(
            ws,
            collection=("claims",),
            id_pattern=CLAIM_ID_RE,
            label="claim",
        )
    ]
    syntheses = [
        load_canonical_synthesis(ws, path.stem)
        for path in _canonical_collection_paths(
            ws,
            collection=("syntheses",),
            id_pattern=SYNTHESIS_ID_RE,
            label="synthesis",
        )
    ]
    paper_findings: list[dict[str, Any]] = []
    paper_actions: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    for path, meta, _ in _canonical_paper_records(ws):
        if meta.get("type") != "paper":
            continue
        state = normalize_paper_state(meta)
        state_counts[f"{state['access_state']}:{state['review_state']}"] += 1
        if state["review_state"] in {"unread", "skimmed", "read"}:
            paper_actions.append(
                {
                    "paper_id": path.relative_to(ws.paths.knowledge).with_suffix("").as_posix(),
                    "access_state": state["access_state"],
                    "review_state": state["review_state"],
                    "next_action": "read" if state["access_state"] == "fulltext" else "add-fulltext",
                }
            )
        schema_findings = enum_findings(meta)
        if schema_findings:
            paper_findings.append({"paper": path.stem, "findings": schema_findings})
    actions = activity_timeline(
        ws.root,
        project_id=project_id,
        activation_id=activation_id,
        action=action,
        status=status,
        target_object_id=target_object_id,
        effective_only=True,
    )
    activations = activation_timeline(ws.root, project_id=project_id, activation_id=activation_id)
    projects: dict[str, dict[str, str]] = {}
    for event in activations:
        event_project_id = str(event.get("project_id", ""))
        if event_project_id:
            projects[event_project_id] = {
                "project_id": event_project_id,
                "project_name": str(event.get("project_name", "")),
                "latest_transition": str(event.get("transition", "")),
                "latest_at": str(event.get("timestamp", "")),
            }
    read_runs = []
    for path in _canonical_collection_paths(
        ws,
        collection=("read_runs",),
        id_pattern=READ_RUN_ID_RE,
        label="read run",
    ):
        read_run = read_canonical_state_json(path, label="read run")
        if read_run.get("schema") != "rkf-read-run-v1" or read_run.get("read_run_id") != path.stem:
            raise ValueError(f"invalid canonical Read run: {path.stem}")
        read_runs.append(read_run)
    retrieval_runs = _canonical_retrieval_runs(ws)
    retrieval_runs.sort(key=lambda item: (str(item.get("created", "")), str(item.get("retrieval_run_id", ""))))
    if project_id:
        retrieval_runs = [item for item in retrieval_runs if item.get("project_id") == project_id]
    if activation_id:
        retrieval_runs = [item for item in retrieval_runs if item.get("activation_id") == activation_id]
    return {
        "schema": "rkf-review-home-v1",
        "paper_state_counts": dict(state_counts),
        "next_papers": sorted(
            paper_actions,
            key=lambda item: (
                {"unread": 0, "skimmed": 1, "read": 2}.get(item["review_state"], 3),
                item["paper_id"],
            ),
        )[:10],
        "paper_schema_findings": paper_findings,
        "finding_locator_debt": [
            {
                "finding_id": item["finding_id"],
                "paper_id": item["paper_id"],
                "reading_scope": item["reading_scope"],
                "locator_state": item["locator_state"],
                "missing": ["locator" if item["locator_state"] == "missing" else "exact-locator"],
                "next_action": (
                    "add-locator"
                    if item["locator_state"] == "missing"
                    else "refine-locator"
                ),
            }
            for item in canonical_findings
            if item.get("locator_state") in {"missing", "coarse"}
        ],
        "evidence_pending_verification": [item["evidence_id"] for item in evidence if item.get("verification_state") == "unreviewed"],
        "claims_missing_locator": [item["claim_id"] for item in claims if item.get("status") in {"proposed", "supported"} and not any(item.get(key) for key in ("supporting_evidence_ids", "opposing_evidence_ids", "context_evidence_ids"))],
        "disputed_claims": [item["claim_id"] for item in claims if item.get("status") == "disputed"],
        "syntheses_with_gaps": [item["synthesis_id"] for item in syntheses if item.get("evidence_gaps")],
        "read_runs_with_failed_checks": [item["read_run_id"] for item in read_runs if item.get("failed_checks")],
        "retrieval_lineage": retrieval_runs[-20:],
        "semantic_index_health": [
            {
                "provider": item.get("provider", "none"),
                "provider_version": item.get("provider_version", ""),
                "index_generation": item.get("index_generation", "none"),
                "elapsed_ms": item.get("elapsed_ms", 0),
                "status": "fallback" if str(item.get("provider", "")).endswith(":fallback") else "available",
            }
            for item in retrieval_runs[-5:]
        ],
        "connected_projects": sorted(projects.values(), key=lambda item: item["project_id"]),
        "activations": activations,
        "activity": actions,
        "blocked_or_failed_activity": [item for item in actions if item.get("status") in {"blocked", "failed", "error", "partial"}],
        "acquisition_needs_attention": [
            item
            for item in actions
            if item.get("action") == "workflow.add"
            and item.get("status") in {"manual-required", "retryable", "unavailable", "blocked", "failed"}
        ],
        "object_origin": (
            object_origin_lookup(ws.root, target_object_id, effective_only=True)
            if target_object_id
            else []
        ),
        "public_safe": True,
    }
