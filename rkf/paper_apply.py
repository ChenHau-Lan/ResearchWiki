"""Approval-bound RKF paper migration apply and rollback operations."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .core import Workspace
from .paper_migration import MigrationPreviewError, SAFE_SOURCE_ID_RE, validate_paper_v1_1


class MigrationApplyError(RuntimeError):
    """Raised when apply or rollback cannot preserve the reviewed contract."""


@dataclass(frozen=True)
class MigrationApplyResult:
    manifest_hash: str
    backup_id: str
    page_count: int
    ledger_count: int
    status: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "manifest_hash": self.manifest_hash,
            "backup_id": self.backup_id,
            "page_count": self.page_count,
            "ledger_count": self.ledger_count,
            "status": self.status,
            "promotion": "none",
        }


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _stable_manifest_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _safe_report_dir(ws: Workspace, report_dir: Path) -> Path:
    resolved = report_dir.expanduser().resolve()
    private_root = (ws.root / ".rkf_private").resolve()
    if not _within(resolved, private_root):
        raise MigrationApplyError("migration report must stay inside local .rkf_private")
    if _within(resolved, ws.paths.wiki_root) or _within(resolved, ws.paths.raw_root):
        raise MigrationApplyError("migration report must be outside canonical wiki/raw roots")
    return resolved


def _safe_logical_target(ws: Workspace, logical_path: str) -> Path:
    if not logical_path.startswith("knowledge/papers/") or not logical_path.endswith(".md"):
        raise MigrationApplyError("migration manifest contains an invalid paper path")
    target = (ws.paths.wiki_root / logical_path).resolve()
    paper_root = (ws.paths.knowledge / "papers").resolve()
    if not _within(target, paper_root):
        raise MigrationApplyError("migration paper path escaped the canonical paper root")
    return target


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        if _sha256_bytes(path.read_bytes()) != _sha256_bytes(data):
            raise MigrationApplyError("post-write checksum verification failed")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_bytes(
        path,
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _load_reviewed_manifest(ws: Workspace, report_dir: Path, approved_manifest_hash: str) -> tuple[Path, dict[str, Any]]:
    safe_report = _safe_report_dir(ws, report_dir)
    manifest_path = safe_report / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationApplyError("reviewed migration manifest is unavailable") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != "rkf-paper-migration-preview-v1":
        raise MigrationApplyError("reviewed migration manifest schema is invalid")
    recorded_hash = str(manifest.get("manifest_hash", ""))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    computed_hash = _stable_manifest_hash(core)
    if not approved_manifest_hash or approved_manifest_hash != recorded_hash or computed_hash != recorded_hash:
        raise MigrationApplyError("approved manifest hash does not match the reviewed preview")
    if not manifest.get("ready_for_live_apply") or manifest.get("unresolved_count") or manifest.get("validation_error_count"):
        raise MigrationApplyError("reviewed migration manifest is not ready for live apply")
    return safe_report, manifest


def _backup_id(manifest_hash: str) -> str:
    return f"paper-v1.1-{manifest_hash}"


def _journal_path(ws: Workspace, backup_id: str) -> Path:
    if not re.fullmatch(r"paper-v1\.1-[0-9a-f]{64}", backup_id):
        raise MigrationApplyError("invalid migration backup id")
    root = (ws.paths.raw_root / "migration_backups").resolve()
    path = (root / backup_id / "apply-journal.json").resolve()
    if not _within(path, root):
        raise MigrationApplyError("migration backup path escaped the private backup root")
    return path


def _restore_from_journal(ws: Workspace, journal: dict[str, Any]) -> None:
    backup_dir = _journal_path(ws, str(journal.get("backup_id", ""))).parent
    entries = journal.get("entries", [])
    if not isinstance(entries, list):
        raise MigrationApplyError("migration journal entries are invalid")
    for entry in reversed(entries):
        if not isinstance(entry, dict) or entry.get("state") != "applied":
            continue
        logical_path = str(entry.get("logical_path", ""))
        if logical_path.startswith("knowledge/papers/"):
            target = _safe_logical_target(ws, logical_path)
        elif logical_path.startswith("state/reading/") and logical_path.endswith(".json"):
            target = (ws.paths.wiki_root / logical_path).resolve()
            if not _within(target, ws.paths.reading):
                raise MigrationApplyError("ledger rollback path escaped reading state")
        else:
            raise MigrationApplyError("migration journal contains an invalid target")
        if entry.get("original_existed"):
            backup_rel = str(entry.get("backup_path", ""))
            backup_path = (backup_dir / backup_rel).resolve()
            if not _within(backup_path, backup_dir) or not backup_path.exists():
                raise MigrationApplyError("migration backup artifact is missing")
            original = backup_path.read_bytes()
            if _sha256_bytes(original) != entry.get("original_checksum"):
                raise MigrationApplyError("migration backup checksum mismatch")
            _atomic_write_bytes(target, original)
        elif target.exists():
            target.unlink()


def apply_migration(
    ws: Workspace,
    *,
    report_dir: Path,
    approved_manifest_hash: str,
    fail_after: int | None = None,
) -> MigrationApplyResult:
    """Atomically apply one reviewed preview, rolling back every partial write."""

    safe_report, manifest = _load_reviewed_manifest(ws, report_dir, approved_manifest_hash)
    pages = manifest.get("pages", [])
    if not isinstance(pages, list) or len(pages) != manifest.get("input_count"):
        raise MigrationApplyError("migration manifest page inventory is incomplete")
    backup_id = _backup_id(approved_manifest_hash)
    journal_path = _journal_path(ws, backup_id)
    if journal_path.parent.exists():
        raise MigrationApplyError("migration backup already exists; refuse duplicate apply")

    planned: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise MigrationApplyError("migration manifest page entry is invalid")
        logical_path = str(page.get("source_page", ""))
        target = _safe_logical_target(ws, logical_path)
        if not target.exists() or _sha256_bytes(target.read_bytes()) != page.get("input_checksum"):
            raise MigrationApplyError("live paper checksum drift invalidated the reviewed preview")
        relative = logical_path.removeprefix("knowledge/papers/")
        output = (safe_report / "workspace" / "knowledge" / "papers" / relative).resolve()
        if not _within(output, safe_report / "workspace" / "knowledge" / "papers") or not output.exists():
            raise MigrationApplyError("reviewed paper output is missing")
        output_bytes = output.read_bytes()
        if _sha256_bytes(output_bytes) != page.get("output_checksum") or validate_paper_v1_1(output_bytes.decode("utf-8")):
            raise MigrationApplyError("reviewed paper output failed checksum or v1.1 validation")
        planned.append({"logical_path": logical_path, "target": target, "output": output, "output_bytes": output_bytes})

    ledger_root = safe_report / "workspace" / "state" / "reading"
    for ledger_output in sorted(ledger_root.glob("*.json")) if ledger_root.exists() else []:
        payload = json.loads(ledger_output.read_text(encoding="utf-8"))
        source_id = str(payload.get("source_id", "")) if isinstance(payload, dict) else ""
        if not SAFE_SOURCE_ID_RE.fullmatch(source_id):
            raise MigrationApplyError("reviewed ledger has an unsafe source id")
        planned.append(
            {
                "logical_path": f"state/reading/{source_id}.json",
                "target": ws.paths.reading / f"{source_id}.json",
                "output": ledger_output,
                "output_bytes": ledger_output.read_bytes(),
            }
        )

    journal: dict[str, Any] = {
        "schema": "rkf-paper-migration-apply-journal-v1",
        "backup_id": backup_id,
        "manifest_hash": approved_manifest_hash,
        "status": "applying",
        "entries": [],
    }
    journal_path.parent.mkdir(parents=True)
    _write_json_atomic(journal_path, journal)
    applied = 0
    try:
        for item in planned:
            target = Path(item["target"])
            logical_path = str(item["logical_path"])
            original_existed = target.exists()
            original = target.read_bytes() if original_existed else b""
            backup_rel = f"originals/{logical_path}"
            if original_existed:
                backup_path = journal_path.parent / backup_rel
                _atomic_write_bytes(backup_path, original)
            entry = {
                "logical_path": logical_path,
                "backup_path": backup_rel,
                "original_existed": original_existed,
                "original_checksum": _sha256_bytes(original) if original_existed else "",
                "output_checksum": _sha256_bytes(item["output_bytes"]),
                "state": "pending",
            }
            journal["entries"].append(entry)
            _write_json_atomic(journal_path, journal)
            _atomic_write_bytes(target, item["output_bytes"])
            entry["state"] = "applied"
            applied += 1
            _write_json_atomic(journal_path, journal)
            if fail_after is not None and applied >= fail_after:
                raise MigrationApplyError("injected migration apply failure")
        journal["status"] = "applied"
        _write_json_atomic(journal_path, journal)
    except Exception as error:
        try:
            _restore_from_journal(ws, journal)
            journal["status"] = "rolled-back-after-failure"
            _write_json_atomic(journal_path, journal)
        except Exception as rollback_error:
            journal["status"] = "rollback-failed"
            journal["rollback_error"] = str(rollback_error)
            _write_json_atomic(journal_path, journal)
            raise MigrationApplyError("migration apply and automatic rollback both failed") from rollback_error
        raise MigrationApplyError(str(error)) from error

    return MigrationApplyResult(
        manifest_hash=approved_manifest_hash,
        backup_id=backup_id,
        page_count=len(pages),
        ledger_count=len(planned) - len(pages),
        status="applied",
    )


def rollback_migration(ws: Workspace, *, backup_id: str, approved_manifest_hash: str) -> MigrationApplyResult:
    """Restore one applied migration from its exact private backup journal."""

    journal_path = _journal_path(ws, backup_id)
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationApplyError("migration rollback journal is unavailable") from error
    if journal.get("manifest_hash") != approved_manifest_hash or backup_id != _backup_id(approved_manifest_hash):
        raise MigrationApplyError("rollback approval does not match the applied manifest")
    if journal.get("status") != "applied":
        raise MigrationApplyError("migration backup is not in an applied state")
    _restore_from_journal(ws, journal)
    for entry in journal.get("entries", []):
        logical_path = str(entry.get("logical_path", ""))
        if logical_path.startswith("knowledge/papers/"):
            target = _safe_logical_target(ws, logical_path)
        else:
            target = ws.paths.wiki_root / logical_path
        if entry.get("original_existed"):
            if not target.exists() or _sha256_bytes(target.read_bytes()) != entry.get("original_checksum"):
                raise MigrationApplyError("rollback checksum verification failed")
        elif target.exists():
            raise MigrationApplyError("rollback failed to remove a newly created target")
    journal["status"] = "rolled-back"
    _write_json_atomic(journal_path, journal)
    page_count = sum(1 for entry in journal["entries"] if str(entry.get("logical_path", "")).startswith("knowledge/papers/"))
    return MigrationApplyResult(
        manifest_hash=approved_manifest_hash,
        backup_id=backup_id,
        page_count=page_count,
        ledger_count=len(journal["entries"]) - page_count,
        status="rolled-back",
    )
