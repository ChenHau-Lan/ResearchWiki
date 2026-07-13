"""Canonical, public-safe Obsidian Base renderers for the RKF wiki."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .core import Workspace
from .sync import atomic_write_text, sha256_file


BASE_FILENAMES = (
    "papers.base",
    "reading-queue.base",
    "inbox.base",
    "questions.base",
    "synthesis.base",
)


def _base_text(
    *,
    name: str,
    folder: str,
    note_type: str,
    properties: tuple[tuple[str, str], ...],
    order: tuple[str, ...],
) -> str:
    lines = [
        "filters:",
        "  and:",
        f"    - 'file.inFolder(\"{folder}\")'",
        f"    - 'type == \"{note_type}\"'",
        "properties:",
    ]
    for property_name, display_name in properties:
        lines.extend((f"  {property_name}:", f"    displayName: \"{display_name}\""))
    lines.extend(("views:", "  - type: table", f"    name: \"{name}\"", "    order:"))
    lines.extend(f"      - {property_name}" for property_name in order)
    return "\n".join(lines) + "\n"


def render_base_views(ws: Workspace) -> dict[str, str]:
    """Render the five Bases without reading or modifying private local state."""

    del ws
    return {
        "papers.base": _base_text(
            name="Papers",
            folder="knowledge/papers",
            note_type="paper",
            properties=(
                ("file.name", "Paper"),
                ("source_id", "Source ID"),
                ("reading_state", "Reading state"),
                ("fulltext_status", "Full text"),
                ("claim_readiness", "Claim readiness"),
                ("updated", "Updated"),
            ),
            order=("file.name", "source_id", "reading_state", "updated"),
        ),
        "reading-queue.base": _base_text(
            name="Reading queue",
            folder="knowledge/papers",
            note_type="paper",
            properties=(
                ("file.name", "Paper"),
                ("reading_state", "Reading state"),
                ("fulltext_status", "Full text"),
                ("human_feedback_level", "Human feedback"),
                ("claim_readiness", "Claim readiness"),
                ("updated", "Updated"),
            ),
            order=("reading_state", "fulltext_status", "claim_readiness", "updated"),
        ),
        "inbox.base": _base_text(
            name="Inbox",
            folder="knowledge/inbox",
            note_type="inbox",
            properties=(
                ("file.name", "Capture"),
                ("origin", "Origin"),
                ("topic_id", "Topic"),
                ("created", "Captured"),
            ),
            order=("created", "topic_id", "file.name"),
        ),
        "questions.base": _base_text(
            name="Questions",
            folder="knowledge/questions",
            note_type="question",
            properties=(
                ("file.name", "Question"),
                ("status", "Status"),
                ("topics", "Topics"),
                ("updated", "Updated"),
            ),
            order=("status", "updated", "file.name"),
        ),
        "synthesis.base": _base_text(
            name="Synthesis",
            folder="knowledge/synthesis",
            note_type="synthesis",
            properties=(
                ("file.name", "Synthesis"),
                ("synthesis_maturity", "Maturity"),
                ("source_coverage", "Coverage"),
                ("claim_readiness", "Claim readiness"),
                ("updated", "Updated"),
            ),
            order=("synthesis_maturity", "claim_readiness", "updated"),
        ),
    }


def preview_base_views(ws: Workspace) -> dict[str, Any]:
    """Return deterministic logical view metadata without creating a view file."""

    views = render_base_views(ws)
    return {
        "count": len(views),
        "files": [
            {
                "logical_path": f"views/{filename}",
                "checksum": sha256(text.encode("utf-8")).hexdigest(),
            }
            for filename, text in views.items()
        ],
    }


def write_base_views(ws: Workspace) -> dict[str, Any]:
    """Atomically write the canonical Base files after an external role guard."""

    views = render_base_views(ws)
    files: list[dict[str, str]] = []
    for filename, text in views.items():
        target = ws.paths.wiki_root / "views" / filename
        expected_checksum = sha256_file(target) if target.exists() else ""
        result = atomic_write_text(target, text, expected_checksum=expected_checksum)
        if not result.written:
            raise RuntimeError(f"cannot write {filename}: {result.reason}")
        files.append({"logical_path": f"views/{filename}", "checksum": result.output_checksum})
    return {"count": len(files), "files": files}
