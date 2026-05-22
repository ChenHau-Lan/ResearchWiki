#!/usr/bin/env python3
"""Build the project-wide full_text index.

The index is intentionally derived from files already in the wiki/raw tree. It
does not acquire text, rewrite paper content, or delete anything.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
WIKI_LIT = ROOT / "wiki" / "literature"

OUT_JSON = RAW / "full_text_index.json"
OUT_MD = RAW / "full_text_index.md"

READABLE_DIR_NAMES = {"full_text", "readable_md", "literature_texts_md"}
SOURCE_DIR_NAMES = {"original_text_md", "clean_original_text_md", "clean_original_text_en_md"}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def normalize_source_ref(value: str) -> str:
    """Return source references without reviving retired raw layouts."""
    value = value.strip()
    if not value:
        return ""

    as_path = Path(value)
    if as_path.is_absolute():
        if as_path.exists() and ROOT in as_path.parents:
            return rel(as_path)
        return value

    candidate = ROOT / value
    if candidate.exists():
        return rel(candidate)

    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end]
    data: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                data[key] = [part.strip().strip('"').strip("'") for part in inner.split(",")]
            else:
                data[key] = []
        else:
            data[key] = value.strip('"').strip("'")
    return data


def extract_line(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def scan_wiki_pages() -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    pages: list[dict[str, str]] = []
    by_doi: dict[str, dict[str, str]] = {}
    for path in sorted(WIKI_LIT.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        if fm.get("type") != "paper":
            continue
        doi = extract_line(r"^- DOI:\s*(.+)$", text)
        citation_key = extract_line(r"^- Citation Key:\s*(.+)$", text)
        title = extract_line(r"^- Title:\s*(.+)$", text)
        page = {
            "wiki_page": rel(path),
            "doi": doi,
            "citation_key": citation_key,
            "title": title,
            "text": text,
        }
        pages.append(page)
        if doi:
            by_doi[doi.lower()] = page
    return by_doi, pages


def cache_layer(path: Path) -> str:
    parts = set(path.parts)
    if parts & READABLE_DIR_NAMES:
        return "readable_md"
    if parts & SOURCE_DIR_NAMES:
        return "source_or_clean_text_md"
    return "other_md"


def slug_from_md(path: Path) -> str:
    name = path.name
    if name.endswith(".en.md"):
        return name[:-6]
    return path.stem


def iter_text_sources() -> list[Path]:
    """Return project-recognized full-text Markdown sources.

    The canonical folder is raw/full_text/. Legacy package folders are kept for
    index compatibility, but generated index files and optional translations are
    not treated as full-text sources.
    """
    allowed_dirs = READABLE_DIR_NAMES | SOURCE_DIR_NAMES
    paths: list[Path] = []
    for path in sorted(RAW.rglob("*.md")):
        if path == OUT_MD or path.name.endswith(".zh.md"):
            continue
        relative_parts = set(path.relative_to(RAW).parts[:-1])
        if relative_parts & allowed_dirs:
            paths.append(path)
    return paths


def normalized_status(fm: dict[str, Any]) -> str:
    status = str(fm.get("status") or fm.get("extraction_status") or fm.get("qc_status") or "").strip()
    if status:
        return status
    return "unknown"


def find_translation(package_dir: Path, slug: str, folder: str) -> str:
    candidate = package_dir / folder / f"{slug}.zh.md"
    return rel(candidate) if candidate.exists() else ""


def find_wiki_for_entry(
    entry_path: Path,
    doi: str,
    by_doi: dict[str, dict[str, str]],
    wiki_pages: list[dict[str, str]],
) -> dict[str, str]:
    rel_path = rel(entry_path)
    basename = entry_path.name
    for page in wiki_pages:
        if rel_path in page["text"] or basename in page["text"]:
            return page
    if doi and doi.lower() in by_doi:
        return by_doi[doi.lower()]
    return {}


def dispatch_status(fulltext_status: str, readability_status: str, wiki_page: str, layer: str) -> str:
    status_lower = fulltext_status.lower()
    readability_lower = readability_status.lower()
    if (
        "needs_codex_qc" in status_lower
        or "needs_codex_qc" in readability_lower
        or "needs-human-review" in readability_lower
    ):
        return "fulltext_qc_needed"
    if "abstract" in status_lower or "metadata" in status_lower:
        return "fulltext_acquisition_needed"
    if not wiki_page:
        return "wiki_ingest_needed"
    if layer != "readable_md":
        return "readable_markdown_upgrade_needed"
    return "ready_for_downstream_tasks"


def primary_score(entry: dict[str, Any]) -> int:
    score = 0
    if entry["package"] == "full_text":
        score += 140
    if entry["package"].endswith("_keep_only"):
        score += 100
    if entry["cache_layer"] == "readable_md":
        score += 80
    if entry["dispatch_status"] == "ready_for_downstream_tasks":
        score += 50
    if entry["dispatch_status"] == "fulltext_acquisition_needed":
        score -= 40
    if entry["zh_full_md"]:
        score += 20
    if ".clean.en.md" in entry["readable_md"]:
        score -= 10
    return score


def choose_primary_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = (entry["doi"] or entry["citation_key"] or entry["slug"]).lower()
        grouped.setdefault(key, []).append(entry)

    primary: list[dict[str, Any]] = []
    for candidates in grouped.values():
        candidates.sort(key=lambda e: (primary_score(e), e["readable_md"]), reverse=True)
        chosen = dict(candidates[0])
        chosen["alternate_text_source_count"] = len(candidates) - 1
        primary.append(chosen)
    primary.sort(key=lambda e: (e["citation_key"], e["doi"], e["readable_md"]))
    return primary


def build_index() -> dict[str, Any]:
    by_doi, wiki_pages = scan_wiki_pages()
    entries: list[dict[str, Any]] = []

    for path in iter_text_sources():
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        slug = slug_from_md(path)
        package_dir = RAW / path.relative_to(RAW).parts[0]
        doi = str(fm.get("doi") or "").strip()
        wiki = find_wiki_for_entry(path, doi, by_doi, wiki_pages)
        layer = cache_layer(path)
        fulltext_status = normalized_status(fm)
        readability_status = str(fm.get("readability_status") or fm.get("qc_status") or "").strip()
        zh_full = find_translation(package_dir, slug, "literature_texts_zh_full_md")
        zh_notes = find_translation(package_dir, slug, "literature_texts_zh_md")

        entries.append(
            {
                "slug": slug,
                "doi": doi,
                "title": str(fm.get("title") or wiki.get("title") or "").strip(),
                "citation_key": wiki.get("citation_key") or slug,
                "package": package_dir.name,
                "cache_layer": layer,
                "readable_md": rel(path),
                "wiki_page": wiki.get("wiki_page", ""),
                "zh_full_md": zh_full,
                "zh_reading_note_md": zh_notes,
                "source_type": str(fm.get("source_type") or "").strip(),
                "source_path": normalize_source_ref(str(fm.get("source_path") or fm.get("raw_capture_path") or "")),
                "source_pdf": normalize_source_ref(str(fm.get("source_pdf") or "")),
                "fulltext_status": fulltext_status,
                "readability_status": readability_status,
                "equation_quality": str(fm.get("equation_quality") or "").strip(),
                "updated": str(fm.get("updated") or "").strip(),
                "dispatch_status": dispatch_status(fulltext_status, readability_status, wiki.get("wiki_page", ""), layer),
                "translation_status": "zh_full_available" if zh_full else "zh_full_pending",
            }
        )

    primary_entries = choose_primary_entries(entries)

    summary = {
        "generated": date.today().isoformat(),
        "primary_entries": len(primary_entries),
        "all_text_sources": len(entries),
        "primary_readable_md": sum(1 for e in primary_entries if e["cache_layer"] == "readable_md"),
        "primary_source_or_clean_text_md": sum(
            1 for e in primary_entries if e["cache_layer"] == "source_or_clean_text_md"
        ),
        "primary_with_wiki_page": sum(1 for e in primary_entries if e["wiki_page"]),
        "primary_with_zh_full_md": sum(1 for e in primary_entries if e["zh_full_md"]),
        "fulltext_acquisition_needed": sum(
            1 for e in primary_entries if e["dispatch_status"] == "fulltext_acquisition_needed"
        ),
        "fulltext_qc_needed": sum(1 for e in primary_entries if e["dispatch_status"] == "fulltext_qc_needed"),
        "wiki_ingest_needed": sum(1 for e in primary_entries if e["dispatch_status"] == "wiki_ingest_needed"),
        "readable_markdown_upgrade_needed": sum(
            1 for e in primary_entries if e["dispatch_status"] == "readable_markdown_upgrade_needed"
        ),
        "ready_for_downstream_tasks": sum(
            1 for e in primary_entries if e["dispatch_status"] == "ready_for_downstream_tasks"
        ),
    }
    return {
        "schema": "full-text-index-v2",
        "summary": summary,
        "dispatch_rule": (
            "Resolve DOI/citation key/slug here first; use wiki_page for knowledge tasks, "
            "readable_md for full-text verification or optional translation, and source_pdf/source_path "
            "only when equation/table/layout checks are required."
        ),
        "entries": primary_entries,
        "all_text_sources": entries,
    }


def write_markdown(index: dict[str, Any]) -> None:
    summary = index["summary"]
    rows = []
    for entry in index["entries"]:
        rows.append(
            "| {citation_key} | {doi} | {status} | {wiki} | {en} | {zh} |".format(
                citation_key=entry["citation_key"],
                doi=entry["doi"] or "",
                status=entry["dispatch_status"],
                wiki=entry["wiki_page"],
                en=entry["readable_md"],
                zh=entry["zh_full_md"] or "",
            )
        )

    body = [
        "# full_text Index",
        "",
        f"Generated: {summary['generated']}",
        "",
        "This file is generated by `tools/build_full_text_index.py`.",
        "Use it as the dispatch table between DOI/citation keys, paper wiki pages, verified full text, and optional downstream artifacts.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        body.append(f"- `{key}`: {value}")
    body.extend(
        [
            "",
            "## Dispatch Rule",
            "",
            index["dispatch_rule"],
            "",
            "## Entries",
            "",
            "| Citation Key | DOI | Dispatch Status | Wiki Page | Full Text MD | Optional Translation MD |",
            "|---|---|---|---|---|---|",
        ]
    )
    body.extend(rows)
    body.append("")
    OUT_MD.write_text("\n".join(body), encoding="utf-8")


def format_summary(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Generated: {generated}".format(**summary),
            "",
            "Entries",
            f"- Primary entries: {summary['primary_entries']}",
            f"- All text sources: {summary['all_text_sources']}",
            f"- Readable Markdown entries: {summary['primary_readable_md']}",
            f"- Source/clean-text fallback entries: {summary['primary_source_or_clean_text_md']}",
            "",
            "Coverage",
            f"- Entries with wiki page: {summary['primary_with_wiki_page']}",
            f"- Entries with optional zh full text: {summary['primary_with_zh_full_md']}",
            f"- Ready for downstream tasks: {summary['ready_for_downstream_tasks']}",
            "",
            "Needs Attention",
            f"- Full text acquisition needed: {summary['fulltext_acquisition_needed']}",
            f"- Full text Codex QC needed: {summary['fulltext_qc_needed']}",
            f"- Wiki ingest needed: {summary['wiki_ingest_needed']}",
            f"- Readable Markdown upgrade needed: {summary['readable_markdown_upgrade_needed']}",
            "",
            "Outputs",
            "- raw/full_text_index.json",
            "- raw/full_text_index.md",
        ]
    )


def main() -> None:
    index = build_index()
    OUT_JSON.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(index)
    print(format_summary(index["summary"]))


if __name__ == "__main__":
    main()
