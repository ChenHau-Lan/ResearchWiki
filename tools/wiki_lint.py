#!/usr/bin/env python3
"""Strict structural checks for Research Wiki."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOI_LIST = ROOT / "raw" / "doi_list.md"
PAPER_SOURCES = ROOT / "raw" / "paper_sources.md"
DOI_DASHBOARD = ROOT / "raw" / "doi_dashboard.md"
FULL_TEXT_INDEX_MD = ROOT / "raw" / "full_text_index.md"
FULL_TEXT_INDEX_JSON = ROOT / "raw" / "full_text_index.json"
FULL_TEXT_DIR = ROOT / "raw" / "full_text"
WIKI_LIT = ROOT / "wiki" / "literature"
WIKI_SYNTHESIS = ROOT / "wiki" / "synthesis"
WIKI_MEETINGS = ROOT / "wiki" / "meetings"
WIKI_PROJECT_SYNTHESIS = ROOT / "wiki" / "project_synthesis"
WIKI_SEMINARS = ROOT / "wiki" / "seminars"

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
COPERNICUS_FILENAME_COPY_DOI_RE = re.compile(r"^(10\.5194/[a-z][a-z0-9]*-\d+-\d+-(?:19|20)\d{2})-\d+$")
STATUSES = {
    "new",
    "metadata_ok",
    "full_text_needed",
    "full_text_done",
    "wiki_done",
    "abstract_only",
    "blocked",
}
OLD_BOARD_HEADER = "| DOI | Status | Title | Full Text | Wiki Page | Next Action | Updated | Note |"
LEGACY_BOARD_HEADER = "| Paper | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_DETAIL_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_COMPACT_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text |"
BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text |"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    value = value.lower()
    copy_suffix = COPERNICUS_FILENAME_COPY_DOI_RE.fullmatch(value)
    return copy_suffix.group(1) if copy_suffix else value


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    result: dict[str, str] = {}
    for line in text[4:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [part.strip().replace(r"\|", "|") for part in stripped.strip("|").split("|")]


def lint_doi_board(errors: list[str]) -> None:
    if not PAPER_SOURCES.exists():
        errors.append("raw/paper_sources.md is missing")
    else:
        source_text = read(PAPER_SOURCES)
        if "## Add Sources Here" not in source_text:
            errors.append("raw/paper_sources.md is missing the '## Add Sources Here' section")

    intake_text = ""
    if not DOI_LIST.exists():
        errors.append("raw/doi_list.md is missing")
    else:
        intake_text = read(DOI_LIST)
        if "## Add DOI Here" not in intake_text:
            errors.append("raw/doi_list.md is missing the '## Add DOI Here' section")
        if BOARD_HEADER in intake_text or LEGACY_BOARD_HEADER in intake_text or LEGACY_DETAIL_BOARD_HEADER in intake_text or LEGACY_COMPACT_BOARD_HEADER in intake_text or OLD_BOARD_HEADER in intake_text:
            errors.append("raw/doi_list.md should not contain the DOI Status Board; use raw/doi_dashboard.md")
    if not DOI_DASHBOARD.exists():
        errors.append("raw/doi_dashboard.md is missing")
        return

    text = read(DOI_DASHBOARD)
    if BOARD_HEADER not in text and LEGACY_BOARD_HEADER not in text and LEGACY_DETAIL_BOARD_HEADER not in text and LEGACY_COMPACT_BOARD_HEADER not in text and OLD_BOARD_HEADER not in text:
        errors.append("raw/doi_dashboard.md is missing the DOI Status Board header")

    seen: set[str] = set()
    in_board = ""
    for line in text.splitlines():
        if line.strip() == BOARD_HEADER:
            in_board = "new"
            continue
        if line.strip() in {LEGACY_BOARD_HEADER, LEGACY_DETAIL_BOARD_HEADER, LEGACY_COMPACT_BOARD_HEADER}:
            in_board = "legacy"
            continue
        if line.strip() == OLD_BOARD_HEADER:
            in_board = "old"
            continue
        if not in_board or not line.startswith("|"):
            continue
        if line.strip().startswith("|---"):
            continue
        parts = split_row(line)
        if in_board == "new" and len(parts) == 6:
            doi = normalize_doi(parts[2])
            status = parts[3]
        elif in_board == "legacy" and len(parts) in {7, 10}:
            doi = normalize_doi(parts[2])
            status = parts[3]
        elif in_board == "old" and len(parts) == 8:
            doi = normalize_doi(parts[0])
            status = parts[1]
        else:
            continue
        if not DOI_RE.fullmatch(doi):
            errors.append(f"raw/doi_dashboard.md: invalid DOI in board: {doi}")
        if doi in seen:
            errors.append(f"raw/doi_dashboard.md: duplicate DOI: {doi}")
        seen.add(doi)
        if status not in STATUSES:
            errors.append(f"raw/doi_dashboard.md: invalid status for {doi}: {status}")


def lint_full_text_index(errors: list[str]) -> None:
    if not FULL_TEXT_INDEX_MD.exists():
        errors.append("raw/full_text_index.md is missing")
    if not FULL_TEXT_INDEX_JSON.exists():
        errors.append("raw/full_text_index.json is missing")


def lint_full_text_qc(errors: list[str]) -> None:
    if not FULL_TEXT_DIR.exists():
        return
    pending_markers = {
        "machine_extracted_needs_codex_qc",
        "needs_codex_qc",
        "pending_codex_qc",
        "needs-human-review",
    }
    for path in sorted(FULL_TEXT_DIR.glob("*.md")):
        text = read(path)
        frontmatter = parse_frontmatter(text) or {}
        status_blob = " ".join(frontmatter.get(key, "") for key in ["extraction_status", "readability_status", "qc_status"]).lower()
        if any(marker in status_blob for marker in pending_markers):
            errors.append(
                f"{path.relative_to(ROOT)}: raw/full_text may only contain QCed readable full text; use raw/staging/extracted_text and Paper intake for Codex conversion"
            )
        if frontmatter.get("extraction_status") in {"codex_qc_done", "abstract_only"} and not frontmatter.get("table_quality"):
            errors.append(f"{path.relative_to(ROOT)}: full_text frontmatter missing table_quality")


def lint_wiki_pages(errors: list[str]) -> None:
    required = {"type", "status", "source_status", "topics", "subtopics", "created", "updated", "sources"}
    folders = [
        (WIKI_LIT, {"paper", "maintenance"}, {"literature.md", "topic_registry.md"}),
        (WIKI_SYNTHESIS, {"synthesis"}, {"synthesis.md"}),
        (WIKI_MEETINGS, {"meeting"}, {"meetings.md"}),
        (WIKI_PROJECT_SYNTHESIS, {"project-synthesis"}, {"project_synthesis.md"}),
        (WIKI_SEMINARS, {"seminar"}, {"seminars.md"}),
    ]
    for folder, allowed_types, support_pages in folders:
        if not folder.exists():
            errors.append(f"{folder.relative_to(ROOT)} is missing")
            continue
        for path in sorted(folder.glob("*.md")):
            text = read(path)
            meta = parse_frontmatter(text)
            rel = path.relative_to(ROOT)
            if meta is None:
                errors.append(f"{rel}: missing YAML frontmatter")
                continue
            if path.name in support_pages:
                if "## Graph Links" not in text:
                    errors.append(f"{rel}: support page missing Graph Links section")
                continue
            missing = required - set(meta)
            if missing:
                errors.append(f"{rel}: missing frontmatter keys: {', '.join(sorted(missing))}")
            page_type = meta.get("type", "")
            if page_type not in allowed_types:
                errors.append(f"{rel}: type must be one of {sorted(allowed_types)}, got {page_type!r}")
            if page_type == "paper" and "- DOI:" not in text:
                errors.append(f"{rel}: paper page missing '- DOI:' metadata line")
            if "## Graph Links" not in text:
                errors.append(f"{rel}: missing Graph Links section")


def main() -> int:
    errors: list[str] = []
    lint_doi_board(errors)
    lint_full_text_index(errors)
    lint_full_text_qc(errors)
    lint_wiki_pages(errors)

    if errors:
        print("wiki_lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("wiki_lint passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
