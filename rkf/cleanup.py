"""Read-only cleanup inventory and approval-manifest support for RKF."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .sync import sha256_file


class CleanupReportRootError(ValueError):
    """Raised when a local cleanup report would overlap canonical storage."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_cleanup_report_root(
    report_root: Path,
    *,
    workspace_root: Path,
    wiki_root: Path,
    raw_root: Path,
) -> Path:
    """Resolve and confine a report root outside both canonical storage planes."""

    resolved = report_root.expanduser().resolve()
    physical_workspace = workspace_root.resolve()
    private_root = (workspace_root / ".rkf_private").resolve()
    if not _is_within(private_root, physical_workspace):
        raise CleanupReportRootError("cleanup manifest private root must remain inside the local workspace")
    if not _is_within(resolved, private_root):
        raise CleanupReportRootError("cleanup manifest report root must stay inside local .rkf_private")
    if _is_within(resolved, wiki_root.resolve()) or _is_within(resolved, raw_root.resolve()):
        raise CleanupReportRootError("cleanup manifest report root must not be inside canonical wiki_root or raw_root")
    return resolved


@dataclass(frozen=True)
class CleanupCandidate:
    logical_id: str
    kind: str
    reason: str
    owner: str
    references: tuple[str, ...]
    recommended_action: str
    replacement_or_archive: str
    risk: str
    rollback: str
    dry_run: str = "no-change"
    approval_status: str = "pending"

    def as_payload(self) -> dict[str, Any]:
        return {
            "logical_id": self.logical_id,
            "kind": self.kind,
            "reason": self.reason,
            "owner": self.owner,
            "references": list(self.references),
            "recommended_action": self.recommended_action,
            "replacement_or_archive": self.replacement_or_archive,
            "risk": self.risk,
            "rollback": self.rollback,
            "dry_run": self.dry_run,
            "approval_status": self.approval_status,
        }


@dataclass(frozen=True)
class CleanupManifest:
    entries: tuple[CleanupCandidate, ...]
    generated_at: str
    approval_status: str = "pending"

    @property
    def manifest_hash(self) -> str:
        core = {"schema": "rkf-cleanup-manifest-v1", "entries": [item.as_payload() for item in self.entries]}
        encoded = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def as_payload(self) -> dict[str, Any]:
        return {
            "schema": "rkf-cleanup-manifest-v1",
            "generated_at": self.generated_at,
            "approval_status": self.approval_status,
            "manifest_hash": self.manifest_hash,
            "entries": [item.as_payload() for item in self.entries],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _iter_public_files(root: Path) -> list[Path]:
    ignored_names = {".git", ".rkf_private", "__pycache__"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in ignored_names for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def _find_references(root: Path, logical_id: str, *, exclude: Path | None = None) -> tuple[str, ...]:
    references: list[str] = []
    leaf = Path(logical_id).name
    for path in _iter_public_files(root):
        if exclude is not None and path == exclude:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if logical_id in text or leaf in text:
            references.append(path.relative_to(root).as_posix())
    return tuple(sorted(set(references)))


def _cache_candidates(root: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for path in sorted(root.rglob("*")):
        if any(part in {".git", ".rkf_private"} for part in path.relative_to(root).parts) or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.name == ".DS_Store" or path.suffix == ".pyc":
            candidates.append(
                CleanupCandidate(
                    logical_id=relative,
                    kind="ignored-cache",
                    reason="Ignored local cache metadata is not a research artifact.",
                    owner="local machine",
                    references=(),
                    recommended_action="review-delete",
                    replacement_or_archive="none",
                    risk="low; rebuildable local cache",
                    rollback="regenerated by the operating system or Python runtime",
                )
            )
    return candidates


def _duplicate_asset_candidates(root: Path) -> list[CleanupCandidate]:
    files = _iter_public_files(root)
    checksums: dict[str, list[Path]] = {}
    for path in files:
        checksums.setdefault(sha256_file(path), []).append(path)
    candidates: list[CleanupCandidate] = []
    manual_root = root / "docs" / "manuals" / "assets"
    if not manual_root.exists():
        return candidates
    for path in sorted(item for item in manual_root.rglob("*") if item.is_file()):
        matches = checksums.get(sha256_file(path), [])
        copies = [item for item in matches if item != path]
        if not copies:
            continue
        relative = path.relative_to(root).as_posix()
        references = _find_references(root, relative, exclude=path)
        candidates.append(
            CleanupCandidate(
                logical_id=relative,
                kind="duplicate-asset",
                reason="Byte-identical asset has another repository copy.",
                owner="RKF manuals",
                references=references,
                recommended_action="retain" if references else "review-delete",
                replacement_or_archive="retain canonical example or active referenced copy",
                risk="medium; documentation may contain implicit references",
                rollback="restore the exact file from Git history before a commit",
            )
        )
    return candidates


def _log_candidate(root: Path) -> CleanupCandidate | None:
    path = root / "log.md"
    if not path.exists():
        return None
    references = _find_references(root, "log.md", exclude=path)
    return CleanupCandidate(
        logical_id="log.md",
        kind="stale-document",
        reason="Root log content may describe retired architecture and needs a reference-aware review.",
        owner="RKF framework",
        references=references,
        recommended_action="retain" if references else "review-archive",
        replacement_or_archive="PROJECT_MEMORY.md and current runtime log surface",
        risk="high if runtime or changelog references remain",
        rollback="keep file unchanged until one approved archive/delete batch",
    )


def _empty_full_text_candidate(root: Path, raw_root: Path) -> CleanupCandidate | None:
    path = raw_root / "full_txt"
    if not path.exists() or any(path.iterdir()):
        return None
    references = _find_references(root, "raw/full_txt", exclude=path)
    return CleanupCandidate(
        logical_id="raw/full_txt",
        kind="empty-directory",
        reason="Retired empty full-text staging directory.",
        owner="private source plane",
        references=references,
        recommended_action="retain" if references else "review-delete",
        replacement_or_archive="per-machine rebuildable cache only",
        risk="medium; verify no configured ingest route depends on this directory",
        rollback="recreate empty directory if a legacy local tool still requires it",
    )


def _automation_candidates(candidates: list[dict[str, str]] | None) -> list[CleanupCandidate]:
    result: list[CleanupCandidate] = []
    for item in candidates or []:
        automation_id = str(item.get("id", "")).strip()
        if not automation_id or str(item.get("status", "")).upper() != "PAUSED":
            continue
        is_replacement = str(item.get("role", "")).strip().lower() == "replacement"
        result.append(
            CleanupCandidate(
                logical_id=f"automation:{automation_id}",
                kind="paused-automation",
                reason=(
                    "Current paused RKF maintenance replacement must remain paused until activation review."
                    if is_replacement
                    else "Paused RKF-related automation requires replacement or retirement review."
                ),
                owner="Codex automation",
                references=(),
                recommended_action="retain" if is_replacement else "review-replace-or-remove",
                replacement_or_archive=(
                    "current paused RKF maintenance preview automation"
                    if is_replacement
                    else "paused RKF maintenance preview automation"
                ),
                risk="high; external scheduler state",
                rollback="keep automation paused; any activation or deletion requires a separate verified update",
            )
        )
    return result


def inventory_cleanup(
    root: Path,
    *,
    raw_root: Path | None = None,
    automation_candidates: list[dict[str, str]] | None = None,
) -> CleanupManifest:
    """Create a no-change cleanup manifest; this function never deletes or moves files."""

    resolved_root = root.resolve()
    entries = [*_cache_candidates(resolved_root), *_duplicate_asset_candidates(resolved_root)]
    log_candidate = _log_candidate(resolved_root)
    if log_candidate is not None:
        entries.append(log_candidate)
    full_text_candidate = _empty_full_text_candidate(resolved_root, (raw_root or resolved_root / "raw").resolve())
    if full_text_candidate is not None:
        entries.append(full_text_candidate)
    entries.extend(_automation_candidates(automation_candidates))
    return CleanupManifest(
        entries=tuple(sorted(entries, key=lambda item: item.logical_id)),
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )


def write_cleanup_manifest(manifest: CleanupManifest, report_root: Path) -> Path:
    """Write one JSON review artifact; no cleanup operation is available here."""

    report_root.mkdir(parents=True, exist_ok=True)
    path = report_root / f"cleanup-manifest-{manifest.manifest_hash}.json"
    path.write_text(manifest.to_json(), encoding="utf-8")
    return path
