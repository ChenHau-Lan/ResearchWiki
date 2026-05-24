#!/usr/bin/env python3
"""Prepare deterministic source fan-out candidates.

This tool stages possible multi-page impacts in maintenance/fanout_candidates.md.
It does not edit formal wiki pages.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "maintenance" / "fanout_candidates.md"
VALID_PRIORITIES = {"low", "medium", "high"}


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalize_targets(value: str) -> str:
    targets = [part.strip() for part in value.split(",") if part.strip()]
    return ", ".join(targets or ["concept", "synthesis", "overview", "hot"])


def candidate_id(source: str) -> str:
    digest = hashlib.sha256(f"{date.today().isoformat()}|{source}".encode("utf-8")).hexdigest()[:8]
    return f"FO-{date.today().strftime('%Y%m%d')}-{digest}"


def source_hash(source: str) -> str:
    path = Path(source)
    if not path.is_absolute():
        path = ROOT / source
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_file() -> str:
    today = date.today().isoformat()
    return "\n".join(
        [
            "---",
            "type: maintenance",
            "status: draft",
            "source_status: personal-note",
            "reading_status: mixed",
            "review_stage: ai-extracted",
            "topics: []",
            "subtopics: []",
            "keywords: [fan_out, candidates, compiler]",
            f"created: {today}",
            f"updated: {today}",
            "sources: []",
            "---",
            "",
            "# Fan-out Candidates",
            "",
            "This file holds deterministic candidate records for source impacts before an",
            "agent or human decides whether they should become formal wiki updates.",
            "",
            "## Candidates",
            "",
            "| ID | Priority | Source | Candidate Targets | Status |",
            "|---|---|---|---|---|",
            "",
            "## Candidate Details",
            "",
            "## Rules",
            "",
            "- This file is a compiler staging area, not stable knowledge.",
            "- A candidate may point to several pages, but it must not edit them directly.",
            "- Approved candidates should be copied or linked into `maintenance/review_queue.md` before formal wiki pages are changed.",
            "",
            "## Graph Links",
            "",
            "- Topics:",
            "- Subtopics:",
            "- Related literature:",
            "- Related concepts:",
            "- Related synthesis: [[synthesis/synthesis]]",
            "- Related seminars:",
            "- Related projects: [[project_synthesis/project_synthesis]]",
            "",
        ]
    )


def render_candidate(*, source: str, priority: str, targets: str, reason: str) -> tuple[str, str]:
    cid = candidate_id(source)
    shash = source_hash(source)
    row = f"| {cid} | {priority} | {source} | {targets} | pending |"
    detail = "\n".join(
        [
            f"### {cid}",
            "",
            f"- Priority: {priority}",
            f"- Source: {source}",
            f"- Source hash: {shash or 'not-available'}",
            f"- Candidate targets: {targets}",
            "- Supported claims:",
            "- Challenged claims:",
            "- Supersession candidates:",
            "- Counter-evidence needed:",
            "- Confidence: mixed",
            f"- Required review: {reason or 'identify source impact before formal wiki edits'}",
            "- Status: pending",
            "",
        ]
    )
    return row, detail


def insert_candidate(text: str, row: str, detail: str) -> str:
    cid = row.split("|")[1].strip()
    if cid in text:
        return text
    if "## Candidates\n\n" not in text or "## Candidate Details\n" not in text:
        text = default_file()
    text = text.replace("## Candidate Details\n", f"{row}\n\n## Candidate Details\n", 1)
    return text.replace("## Rules\n", f"{detail}\n## Rules\n", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="source page, DOI, citation key, or full_text path")
    parser.add_argument("--priority", default="medium", choices=sorted(VALID_PRIORITIES))
    parser.add_argument("--targets", default="concept,synthesis,overview,hot")
    parser.add_argument("--reason", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = normalize_targets(args.targets)
    row, detail = render_candidate(source=args.source, priority=args.priority, targets=targets, reason=args.reason)
    if args.dry_run:
        print(row)
        print()
        print(detail)
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = OUT.read_text(encoding="utf-8") if OUT.exists() else default_file()
    OUT.write_text(insert_candidate(text, row, detail), encoding="utf-8")
    print(f"Wrote {repo_relative(OUT)}")
    print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
