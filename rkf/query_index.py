"""Private, rebuildable snapshot storage for deterministic RKF retrieval.

The query index is a derived performance projection, never a trust authority.
Callers must validate canonical candidates against their source objects and
lineage receipts before returning them as evidence-ready results.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


QUERY_INDEX_SCHEMA = "rkf-query-index-v1"
QUERY_INDEX_FILENAME = "query-index-v1.sqlite3"


@dataclass(frozen=True)
class QueryIndexResult:
    """Outcome of one index read or write without exposing local paths."""

    state: str
    reason: str
    generation: str = "none"
    payload: dict[str, Any] | None = None


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def source_manifest_fingerprint(
    entries: Iterable[tuple[str, Path]],
) -> str:
    """Fingerprint safe source metadata without reading source contents.

    Retrieval performs its own no-follow collection checks before supplying
    entries. Device, inode, size, mtime, and ctime make same-path replacements
    invalidate the projection even when a filename remains unchanged.
    """

    manifest: list[dict[str, object]] = []
    for logical_path, path in sorted(entries, key=lambda item: item[0]):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("query index source entry must be a regular file")
        manifest.append(
            {
                "path": logical_path,
                "device": info.st_dev,
                "inode": info.st_ino,
                "size": info.st_size,
                "mtime_ns": info.st_mtime_ns,
                "ctime_ns": info.st_ctime_ns,
            }
        )
    return _fingerprint(manifest)


class RetrievalQueryIndex:
    """Session-owned access to a private SQLite retrieval projection."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        enabled: bool = True,
        allow_write: bool = True,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.enabled = enabled
        self.allow_write = allow_write
        self.private_root = self.workspace_root / ".rkf_private"
        self.path = self.private_root / QUERY_INDEX_FILENAME

    def _safe_state(self, *, create_parent: bool = False) -> tuple[bool, str]:
        try:
            root_info = self.workspace_root.lstat()
        except OSError:
            return False, "workspace-unavailable"
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            return False, "unsafe-workspace-root"

        if self.private_root.exists() or self.private_root.is_symlink():
            try:
                private_info = self.private_root.lstat()
            except OSError:
                return False, "private-root-unavailable"
            if stat.S_ISLNK(private_info.st_mode) or not stat.S_ISDIR(private_info.st_mode):
                return False, "unsafe-private-root"
        elif create_parent:
            try:
                self.private_root.mkdir(mode=0o700)
            except OSError:
                return False, "private-root-unavailable"

        if self.path.exists() or self.path.is_symlink():
            try:
                index_info = self.path.lstat()
            except OSError:
                return False, "index-unavailable"
            if (
                stat.S_ISLNK(index_info.st_mode)
                or not stat.S_ISREG(index_info.st_mode)
                or index_info.st_nlink != 1
            ):
                return False, "unsafe-index-file"
        return True, "ok"

    @staticmethod
    def _open(path: Path, *, read_only: bool) -> sqlite3.Connection:
        if read_only:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            connection.execute("PRAGMA query_only = ON")
        else:
            connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _integrity_ok(connection: sqlite3.Connection) -> bool:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return row is not None and str(row[0]).lower() == "ok"

    def load(self, *, source_fingerprint: str) -> QueryIndexResult:
        if not self.enabled:
            return QueryIndexResult("disabled", "disabled-by-caller")
        safe, reason = self._safe_state()
        if not safe:
            return QueryIndexResult("fallback", reason)
        if not self.path.exists():
            return QueryIndexResult("miss", "index-missing")

        try:
            with self._open(self.path, read_only=True) as connection:
                if not self._integrity_ok(connection):
                    return QueryIndexResult("fallback", "integrity-check-failed")
                meta = connection.execute(
                    "SELECT schema_version, source_fingerprint, payload_fingerprint, "
                    "generation FROM query_index_meta WHERE singleton = 1"
                ).fetchone()
                snapshot = connection.execute(
                    "SELECT payload FROM query_index_snapshot WHERE singleton = 1"
                ).fetchone()
        except (OSError, sqlite3.DatabaseError):
            return QueryIndexResult("fallback", "corrupt-or-unreadable")

        if meta is None or snapshot is None:
            return QueryIndexResult("fallback", "incomplete-index")
        if meta["schema_version"] != QUERY_INDEX_SCHEMA:
            return QueryIndexResult("fallback", "schema-version-mismatch")
        if meta["source_fingerprint"] != source_fingerprint:
            return QueryIndexResult("stale", "source-fingerprint-mismatch")
        try:
            payload = json.loads(str(snapshot["payload"]))
        except (TypeError, json.JSONDecodeError):
            return QueryIndexResult("fallback", "invalid-index-payload")
        if not isinstance(payload, dict):
            return QueryIndexResult("fallback", "invalid-index-payload")
        if _fingerprint(payload) != meta["payload_fingerprint"]:
            return QueryIndexResult("fallback", "payload-fingerprint-mismatch")
        expected_generation = "qidx_" + _fingerprint(
            {
                "schema": QUERY_INDEX_SCHEMA,
                "source_fingerprint": source_fingerprint,
                "payload_fingerprint": meta["payload_fingerprint"],
            }
        )[:24]
        if meta["generation"] != expected_generation:
            return QueryIndexResult("fallback", "generation-fingerprint-mismatch")
        return QueryIndexResult(
            "hit",
            "fingerprints-match",
            generation=expected_generation,
            payload=payload,
        )

    def store(
        self,
        *,
        source_fingerprint: str,
        payload: dict[str, Any],
    ) -> QueryIndexResult:
        if not self.enabled:
            return QueryIndexResult("disabled", "disabled-by-caller")
        if not self.allow_write:
            return QueryIndexResult("disabled", "writes-disabled")
        safe, reason = self._safe_state(create_parent=True)
        if not safe:
            return QueryIndexResult("fallback", reason)
        try:
            os.chmod(self.private_root, 0o700)
        except OSError:
            return QueryIndexResult("fallback", "private-root-unavailable")

        existed = self.path.exists()
        payload_text = _canonical_json(payload)
        payload_fingerprint = _fingerprint(payload)
        generation = "qidx_" + _fingerprint(
            {
                "schema": QUERY_INDEX_SCHEMA,
                "source_fingerprint": source_fingerprint,
                "payload_fingerprint": payload_fingerprint,
            }
        )[:24]
        try:
            with self._open(self.path, read_only=False) as connection:
                if existed and not self._integrity_ok(connection):
                    return QueryIndexResult("fallback", "integrity-check-failed")
                if existed:
                    table = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' "
                        "AND name = 'query_index_meta'"
                    ).fetchone()
                    if table is None:
                        return QueryIndexResult("fallback", "schema-version-mismatch")
                    current = connection.execute(
                        "SELECT schema_version FROM query_index_meta WHERE singleton = 1"
                    ).fetchone()
                    if current is not None and current["schema_version"] != QUERY_INDEX_SCHEMA:
                        return QueryIndexResult("fallback", "schema-version-mismatch")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS query_index_meta (
                        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                        schema_version TEXT NOT NULL,
                        source_fingerprint TEXT NOT NULL,
                        payload_fingerprint TEXT NOT NULL,
                        generation TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS query_index_snapshot (
                        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                        payload TEXT NOT NULL
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO query_index_meta "
                    "(singleton, schema_version, source_fingerprint, payload_fingerprint, generation) "
                    "VALUES (1, ?, ?, ?, ?) "
                    "ON CONFLICT(singleton) DO UPDATE SET "
                    "schema_version=excluded.schema_version, "
                    "source_fingerprint=excluded.source_fingerprint, "
                    "payload_fingerprint=excluded.payload_fingerprint, "
                    "generation=excluded.generation",
                    (
                        QUERY_INDEX_SCHEMA,
                        source_fingerprint,
                        payload_fingerprint,
                        generation,
                    ),
                )
                connection.execute(
                    "INSERT INTO query_index_snapshot (singleton, payload) VALUES (1, ?) "
                    "ON CONFLICT(singleton) DO UPDATE SET payload=excluded.payload",
                    (payload_text,),
                )
                connection.commit()
                try:
                    os.chmod(self.path, 0o600)
                except OSError:
                    pass
        except (OSError, sqlite3.DatabaseError):
            return QueryIndexResult("fallback", "corrupt-or-unwritable")
        return QueryIndexResult(
            "rebuilt",
            "source-scan-projected",
            generation=generation,
        )
